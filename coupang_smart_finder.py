# coupang_smart_finder.py - 쿠팡 공식 예제 완전 준수

import hmac
import hashlib
import requests
import os
from datetime import datetime

# ==================== 설정 ====================
ACCESS_KEY = os.environ.get('COUPANG_ACCESS_KEY')
SECRET_KEY = os.environ.get('COUPANG_SECRET_KEY')
DOMAIN = "https://api-gateway.coupang.com"

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
}

# ==================== HMAC 서명 (쿠팡 공식) ====================
def generateHmac(method, url, secretKey, accessKey):
    """쿠팡 공식 서명 함수 - 함수명도 공식 스타일"""
    path = url.replace(DOMAIN, "")
    
    datetime_str = datetime.utcnow().strftime('%y%m%d') + 'T' + datetime.utcnow().strftime('%H%M%S') + 'Z'
    message = datetime_str + method + path
    
    signature = hmac.new(
        bytes(secretKey, 'utf-8'),
        bytes(message, 'utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return "CEA algorithm=HmacSHA256, access-key={}, signed-date={}, signature={}".format(accessKey, datetime_str, signature)

# ==================== 제품 검색 ====================
def searchProducts(keyword, limit=10):
    """쿠팡 제품 검색"""
    import urllib.parse
    
    # URL 생성 - 쿠팡 방식
    encoded_keyword = urllib.parse.quote(keyword)
    request_url = "{}/v2/providers/affiliate_open_api/apis/openapi/products/search?keyword={}&limit={}".format(
        DOMAIN, encoded_keyword, limit
    )
    
    # 헤더 생성
    authorization = generateHmac("GET", request_url, SECRET_KEY, ACCESS_KEY)
    
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json"
    }
    
    # API 호출
    response = requests.get(request_url, headers=headers)
    
    return response

# ==================== 수수료율 예측 ====================
def estimateCommission(product):
    category = product.get('categoryName', '')
    price = product.get('productPrice', 0)
    is_rocket = product.get('isRocket', False)
    
    rate = 3.5
    for key, val in CATEGORY_COMMISSION.items():
        if key in category:
            rate = val
            break
    
    if price <= 20000:
        rate += 0.5
    elif price >= 100000:
        rate -= 0.5
    
    if is_rocket:
        rate += 0.3
    
    return round(rate, 1)

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
    all_results = []
    
    for keyword in keywords:
        print(f"\n{'=' * 70}")
        print(f"📌 키워드: {keyword}")
        print(f"{'=' * 70}\n")
        
        try:
            response = searchProducts(keyword, 10)
            
            print(f"응답 코드: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('rCode') == '0':
                    products = data.get('data', {}).get('productData', [])
                    print(f"✅ {len(products)}개 제품 발견\n")
                    
                    # 가격 필터링 & 분석
                    filtered = []
                    for p in products:
                        price = p.get('productPrice', 0)
                        if 10000 <= price <= 100000:
                            rate = estimateCommission(p)
                            commission = int(price * rate / 100)
                            is_rocket = p.get('isRocket', False)
                            
                            score = rate * 10
                            if is_rocket:
                                score += 20
                            if 10000 <= price <= 30000:
                                score += 10
                            
                            filtered.append({
                                'product': p,
                                'price': price,
                                'rate': rate,
                                'commission': commission,
                                'rocket': is_rocket,
                                'score': score
                            })
                    
                    filtered.sort(key=lambda x: x['score'], reverse=True)
                    
                    # TOP 3 출력
                    for idx, item in enumerate(filtered[:3], 1):
                        p = item['product']
                        print(f"{idx}. {p.get('productName', '')}")
                        if item['rocket']:
                            print("   🚀 로켓배송")
                        print(f"   💰 가격: {item['price']:,}원")
                        print(f"   📂 카테고리: {p.get('categoryName', '')}")
                        print(f"   📊 예상 수수료율: {item['rate']}% (추정치)")
                        print(f"   💵 예상 수수료: {item['commission']:,}원")
                        print(f"   ⭐ 우선순위 점수: {item['score']:.1f}")
                        print(f"   🔗 {p.get('productUrl', '')}\n")
                    
                    all_results.extend([x for x in filtered if x['rate'] >= 5.0])
                else:
                    print(f"❌ rCode: {data.get('rCode')}, {data.get('rMessage')}")
            else:
                print(f"❌ HTTP {response.status_code}")
                print(f"응답: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ 오류: {e}")
    
    # 요약
    print("\n" + "=" * 70)
    print("📊 전체 요약")
    print("=" * 70)
    
    if all_results:
        all_results.sort(key=lambda x: x['score'], reverse=True)
        best = all_results[0]
        
        print(f"✅ 총 {len(all_results)}개 예상 고수수료 제품 발견 (5% 이상)")
        print(f"🥇 최고:")
        print(f"   - {best['product'].get('productName', '')[:50]}...")
        print(f"   - 예상 수수료율: {best['rate']}%")
        print(f"   - 예상 수수료: {best['commission']:,}원")
        print(f"   - 로켓배송: {'O' if best['rocket'] else 'X'}")
        print(f"   - 우선순위 점수: {best['score']:.1f}")
        
        rocket_cnt = sum(1 for x in all_results if x['rocket'])
        ratio = rocket_cnt / len(all_results) * 100
        print(f"\n🚀 로켓배송 비율: {ratio:.1f}%")
    else:
        print("⚠️ 고수수료 제품 없음")
    
    print("\n" + "=" * 70)
    print("✅ 완료")
    print("=" * 70)

if __name__ == "__main__":
    main()
