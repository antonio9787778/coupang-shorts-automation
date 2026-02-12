# coupang_smart_finder.py - 쿠팡 공식 Python 예제 기반

import hmac
import hashlib
import requests
import os
from datetime import datetime
from urllib.parse import quote

# ==================== 설정 ====================
ACCESS_KEY = os.environ.get('COUPANG_ACCESS_KEY')
SECRET_KEY = os.environ.get('COUPANG_SECRET_KEY')
DOMAIN = "https://api-gateway.coupang.com"

print("🔧 시작")
print(f"ACCESS_KEY: {ACCESS_KEY[:10] if ACCESS_KEY else 'None'}...")
print(f"SECRET_KEY: {SECRET_KEY[:10] if SECRET_KEY else 'None'}...")
print()

CATEGORY_COMMISSION = {
    '패션의류': 6.0,
    '패션잡화': 6.0,
    '화장품': 5.0,
    '건강식품': 5.0,
    '건강': 5.0,
    '식품': 4.5,
    '생활용품': 4.0,
    '가전디지털': 3.0,
    '도서': 7.5,
    '출산/육아': 4.5,
    '스포츠': 4.0
}

# ==================== HMAC 서명 생성 (쿠팡 공식) ====================
def generate_hmac_signature(method, url, secret_key, access_key):
    """쿠팡 공식 HMAC 서명 - URL 전체 사용"""
    
    # GMT 시간
    datetime_str = datetime.utcnow().strftime('%y%m%d') + 'T' + datetime.utcnow().strftime('%H%M%S') + 'Z'
    
    # URL에서 path만 추출 (도메인 제외)
    path = url.replace(DOMAIN, '')
    
    # 메시지: datetime + method + path
    message = datetime_str + method + path
    
    # HMAC-SHA256
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Authorization 헤더
    return f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={datetime_str}, signature={signature}"

# ==================== 쿠팡 제품 검색 ====================
def search_coupang_products(keyword, limit=10):
    """쿠팡 제품 검색 - 단순 버전"""
    
    # URL 생성
    url = f"{DOMAIN}/v2/providers/affiliate_open_api/apis/openapi/products/search?keyword={quote(keyword)}&limit={limit}"
    
    # 서명 생성
    authorization = generate_hmac_signature("GET", url, SECRET_KEY, ACCESS_KEY)
    
    # 헤더
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json"
    }
    
    # 요청
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ [{keyword}] {response.status_code}: {response.text[:100]}")
            return None
    except Exception as e:
        print(f"❌ [{keyword}] 오류: {e}")
        return None

# ==================== 수수료율 예측 ====================
def estimate_commission_rate(product):
    category_name = product.get('categoryName', '')
    price = product.get('productPrice', 0)
    is_rocket = product.get('isRocket', False)
    
    commission_rate = 3.5
    for key, rate in CATEGORY_COMMISSION.items():
        if key in category_name:
            commission_rate = rate
            break
    
    if price <= 20000:
        commission_rate += 0.5
    elif price >= 100000:
        commission_rate -= 0.5
    
    if is_rocket:
        commission_rate += 0.3
    
    return round(commission_rate, 1)

# ==================== 제품 분석 ====================
def analyze_products(products):
    analyzed = []
    
    for product in products:
        price = product.get('productPrice', 0)
        
        if price < 10000 or price > 100000:
            continue
        
        commission_rate = estimate_commission_rate(product)
        commission_amount = int(price * (commission_rate / 100))
        is_rocket = product.get('isRocket', False)
        
        analyzed.append({
            'product': product,
            'price': price,
            'commission_rate': commission_rate,
            'commission_amount': commission_amount,
            'is_rocket': is_rocket,
            'priority_score': (
                commission_rate * 10 +
                (20 if is_rocket else 0) +
                (10 if 10000 <= price <= 30000 else 0)
            )
        })
    
    analyzed.sort(key=lambda x: x['priority_score'], reverse=True)
    return analyzed

# ==================== 메인 ====================
def main():
    print("=" * 70)
    print("🎯 쿠팡 파트너스 제품 검색")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    if not ACCESS_KEY or not SECRET_KEY:
        print("❌ API 키 없음")
        return
    
    keywords = ['여성의류', '화장품세트', '건강식품']
    all_high_commission = []
    
    for keyword in keywords:
        print(f"\n{'=' * 70}")
        print(f"📌 키워드: {keyword}")
        print(f"{'=' * 70}\n")
        
        # API 호출
        data = search_coupang_products(keyword, limit=10)
        
        if not data or data.get('rCode') != '0':
            print(f"⚠️ 검색 실패\n")
            continue
        
        products = data.get('data', {}).get('productData', [])
        
        if not products:
            print(f"⚠️ 제품 없음\n")
            continue
        
        print(f"✅ {len(products)}개 제품 발견")
        
        # 분석
        analyzed = analyze_products(products)
        
        if not analyzed:
            print(f"⚠️ 가격 필터 후 제품 없음\n")
            continue
        
        print(f"✅ 필터 후 {len(analyzed)}개")
        
        # TOP 3 출력
        top_products = analyzed[:3]
        print(f"\n📋 TOP 3:\n")
        
        for idx, item in enumerate(top_products, 1):
            product = item['product']
            print(f"{idx}. {product.get('productName', 'N/A')}")
            if item['is_rocket']:
                print("   🚀 로켓배송")
            print(f"   💰 가격: {item['price']:,}원")
            print(f"   📂 카테고리: {product.get('categoryName', 'N/A')}")
            print(f"   📊 예상 수수료율: {item['commission_rate']}% (추정치)")
            print(f"   💵 예상 수수료: {item['commission_amount']:,}원")
            print(f"   ⭐ 우선순위 점수: {item['priority_score']:.1f}")
            print(f"   🔗 {product.get('productUrl', 'N/A')}\n")
        
        high_commission = [item for item in analyzed if item['commission_rate'] >= 5.0]
        all_high_commission.extend(high_commission)
    
    # 요약
    print("\n" + "=" * 70)
    print("📊 전체 요약")
    print("=" * 70)
    
    if all_high_commission:
        all_high_commission.sort(key=lambda x: x['priority_score'], reverse=True)
        best = all_high_commission[0]
        
        print(f"✅ 총 {len(all_high_commission)}개 예상 고수수료 제품 발견 (5% 이상)")
        print(f"🥇 최고 우선순위 제품:")
        print(f"   - 제품: {best['product'].get('productName', 'N/A')[:50]}...")
        print(f"   - 예상 수수료율: {best['commission_rate']}%")
        print(f"   - 예상 수수료: {best['commission_amount']:,}원")
        print(f"   - 로켓배송: {'O' if best['is_rocket'] else 'X'}")
        print(f"   - 우선순위 점수: {best['priority_score']:.1f}")
        
        rocket_count = sum(1 for item in all_high_commission if item['is_rocket'])
        rocket_ratio = (rocket_count / len(all_high_commission)) * 100
        print(f"\n🚀 로켓배송 비율: {rocket_ratio:.1f}% ({rocket_count}/{len(all_high_commission)})")
    else:
        print("⚠️ 고수수료 제품 없음")
    
    print("\n" + "=" * 70)
    print("✅ 완료")
    print("=" * 70)

if __name__ == "__main__":
    main()
