# coupang_smart_finder.py - 쿠팡 공식 서명 방식

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

print("🔧 디버깅 모드 시작")
print(f"ACCESS_KEY 존재: {'✅' if ACCESS_KEY else '❌'}")
print(f"SECRET_KEY 존재: {'✅' if SECRET_KEY else '❌'}")
if ACCESS_KEY:
    print(f"ACCESS_KEY 앞 10자: {ACCESS_KEY[:10]}...")
if SECRET_KEY:
    print(f"SECRET_KEY 앞 10자: {SECRET_KEY[:10]}...")
print()

# 카테고리별 평균 수수료율
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
def generate_hmac(method, path, secret_key, access_key):
    """쿠팡 공식 HMAC 서명 생성"""
    # GMT 시간 형식: yyMMddTHHmmssZ
    datetime_utc = datetime.utcnow()
    datetime_str = datetime_utc.strftime('%y%m%d') + 'T' + datetime_utc.strftime('%H%M%S') + 'Z'
    
    # 메시지 생성: datetime + method + path
    message = datetime_str + method + path
    
    print(f"🔐 서명 생성 상세:")
    print(f"   UTC 시간: {datetime_utc}")
    print(f"   DateTime 문자열: {datetime_str}")
    print(f"   Method: {method}")
    print(f"   Path: {path}")
    print(f"   Message: {message}")
    
    # HMAC-SHA256 서명
    signature = hmac.new(
        bytes(secret_key, 'utf-8'),
        bytes(message, 'utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    print(f"   Signature: {signature}")
    
    # Authorization 헤더
    authorization = f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={datetime_str}, signature={signature}"
    
    print(f"   Authorization 헤더 생성 완료")
    print()
    
    return authorization

# ==================== 쿠팡 제품 검색 ====================
def search_products(keyword, limit=10):
    """쿠팡 제품 검색"""
    print(f"🔍 검색 시작: {keyword}")
    
    if limit > 10:
        limit = 10
    
    # Path 정확히 생성
    path = f"/v2/providers/affiliate_open_api/apis/openapi/products/search?keyword={quote(keyword)}&limit={limit}"
    url = DOMAIN + path
    
    print(f"   전체 URL: {url}")
    print()
    
    authorization = generate_hmac("GET", path, SECRET_KEY, ACCESS_KEY)
    
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        print(f"   📡 응답 받음: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 성공!")
            print(f"   rCode: {data.get('rCode')}")
            print(f"   rMessage: {data.get('rMessage')}")
            
            if data.get('data'):
                products = data.get('data', {}).get('productData', [])
                print(f"   제품 개수: {len(products)}")
                if products:
                    print(f"   첫 제품: {products[0].get('productName', '')[:40]}...")
            print()
            return data
        else:
            print(f"   ❌ API 오류 코드: {response.status_code}")
            print(f"   응답 내용: {response.text}")
            print()
            return None
            
    except Exception as e:
        print(f"   ❌ 예외 발생: {type(e).__name__}: {str(e)}")
        print()
        return None

# ==================== 수수료율 예측 ====================
def estimate_commission_rate(product):
    """카테고리, 가격, 배송 타입 기반 수수료율 예측"""
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
    """제품 분석 후 수익성 기준으로 정렬"""
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

# ==================== 메인 실행 ====================
def main():
    print("=" * 70)
    print("🎯 쿠팡 파트너스 수익 최적화 제품 검색 시작")
    print(f"📅 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    if not ACCESS_KEY or not SECRET_KEY:
        print("❌ 치명적 오류: API 키가 설정되지 않았습니다!")
        return
    
    keywords = ['여성의류', '화장품세트', '건강식품']
    print(f"🔍 검색 키워드: {', '.join(keywords)}\n")
    
    all_high_commission = []
    
    for keyword in keywords:
        print(f"\n{'=' * 70}")
        print(f"📌 키워드: {keyword}")
        print(f"{'=' * 70}\n")
        
        data = search_products(keyword, limit=10)
        
        if not data:
            print(f"⚠️ API 호출 실패\n")
            continue
        
        if data.get('rCode') != '0':
            print(f"⚠️ API 응답 오류: {data.get('rMessage')}\n")
            continue
        
        products = data.get('data', {}).get('productData', [])
        
        if not products:
            print(f"⚠️ 검색 결과 없음\n")
            continue
        
        analyzed = analyze_products(products)
        
        if not analyzed:
            print(f"⚠️ 가격 필터링 후 제품 없음\n")
            continue
        
        top_products = analyzed[:3]
        
        print(f"📋 TOP 3 제품:\n")
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
    
    print("\n" + "=" * 70)
    print("📊 전체 검색 요약")
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
        print("⚠️ 예상 고수수료 제품을 찾지 못했습니다.")
    
    print("\n" + "=" * 70)
    print("✅ 검색 완료!")
    print("=" * 70)

if __name__ == "__main__":
    main()
