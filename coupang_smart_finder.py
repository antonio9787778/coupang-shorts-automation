import os
import hmac
import hashlib
import requests
from time import gmtime, strftime
from urllib.parse import urlencode
import json

DOMAIN = "https://api-gateway.coupang.com"
PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/products/search"

ACCESS_KEY = os.getenv("COUPANG_ACCESS_KEY")
SECRET_KEY = os.getenv("COUPANG_SECRET_KEY")

if not ACCESS_KEY or not SECRET_KEY:
    raise SystemExit("❌ API 키가 없습니다.")

print("✅ API 키 로드 완료")

# ===== 카테고리별 예상 수수료율 데이터베이스 =====
CATEGORY_COMMISSION_RATES = {
    '패션': {'min': 5.0, 'max': 7.0, 'avg': 6.0},
    '의류': {'min': 5.0, 'max': 7.0, 'avg': 6.0},
    '잡화': {'min': 5.0, 'max': 7.0, 'avg': 6.0},
    '뷰티': {'min': 4.0, 'max': 6.0, 'avg': 5.0},
    '화장품': {'min': 4.0, 'max': 6.0, 'avg': 5.0},
    '식품': {'min': 4.0, 'max': 6.0, 'avg': 5.0},
    '건강': {'min': 4.0, 'max': 6.0, 'avg': 5.0},
    '건강식품': {'min': 4.0, 'max': 6.0, 'avg': 5.0},
    '도서': {'min': 5.0, 'max': 10.0, 'avg': 7.5},
    '음반': {'min': 5.0, 'max': 10.0, 'avg': 7.5},
    '생활': {'min': 3.0, 'max': 5.0, 'avg': 4.0},
    '생활용품': {'min': 3.0, 'max': 5.0, 'avg': 4.0},
    '가전': {'min': 2.0, 'max': 4.0, 'avg': 3.0},
    '가전디지털': {'min': 2.0, 'max': 4.0, 'avg': 3.0},
    '디지털': {'min': 2.0, 'max': 4.0, 'avg': 3.0},
    '스포츠': {'min': 3.0, 'max': 5.0, 'avg': 4.0},
    '레저': {'min': 3.0, 'max': 5.0, 'avg': 4.0},
    '완구': {'min': 4.0, 'max': 6.0, 'avg': 5.0},
    '취미': {'min': 4.0, 'max': 6.0, 'avg': 5.0},
}

def estimate_commission_rate(product):
    """제품 정보로 수수료율 예측"""
    
    category = product.get('categoryName', '')
    price = product.get('productPrice', 0)
    is_rocket = product.get('isRocket', False)
    
    # 카테고리 기반 기본 수수료율
    base_rate = 3.0  # 기본값
    
    for keyword, rates in CATEGORY_COMMISSION_RATES.items():
        if keyword in category:
            base_rate = rates['avg']
            break
    
    # 가격대 보정
    if price >= 100000:  # 10만원 이상 고가품
        base_rate -= 0.5
    elif price <= 20000:  # 2만원 이하 저가품
        base_rate += 0.5
    
    # 로켓배송 보정
    if is_rocket:
        base_rate += 0.3
    
    # 최소/최대 제한
    base_rate = max(1.0, min(10.0, base_rate))
    
    return round(base_rate, 1)

def signed_date_gmt():
    return strftime("%y%m%dT%H%M%SZ", gmtime())

def make_authorization(method, path, query):
    dt = signed_date_gmt()
    message = dt + method + path + query
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={ACCESS_KEY}, signed-date={dt}, signature={signature}"

def search_products(keyword, limit=10):
    """키워드로 쿠팡 제품 검색"""
    print(f"🔍 '{keyword}' 검색 중...")
    
    params = {"keyword": keyword, "limit": limit}
    query = urlencode(params)
    auth = make_authorization("GET", PATH, query)

    url = f"{DOMAIN}{PATH}"
    headers = {"Authorization": auth, "Content-Type": "application/json"}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
        r.raise_for_status()
        print(f"✅ API 호출 성공 (상태: {r.status_code})")
        return r.json()
    except Exception as e:
        print(f"❌ 요청 실패: {e}")
        return None

def pick_high_estimated_commission(response_json, top_n=5, min_rate=4.0):
    """예상 수수료율이 높은 제품 선별"""
    
    if not response_json or 'data' not in response_json:
        print("⚠️ 검색 결과 없음")
        return [], False
    
    data = response_json['data']
    
    # data가 딕셔너리인 경우 (실제 구조)
    if isinstance(data, dict):
        product_list = data.get('productData', [])
    else:
        product_list = data
    
    if not product_list:
        print("⚠️ 제품 데이터 없음")
        return [], False
    
    print(f"📊 총 {len(product_list)}개 제품 발견")
    
    # 각 제품의 예상 수수료율 계산
    products_with_estimate = []
    
    for p in product_list:
        estimated_rate = estimate_commission_rate(p)
        estimated_commission = int(p.get('productPrice', 0) * (estimated_rate / 100))
        
        products_with_estimate.append({
            'name': p.get('productName', '제품명 없음'),
            'price': p.get('productPrice', 0),
            'category': p.get('categoryName', '미분류'),
            'isRocket': p.get('isRocket', False),
            'estimatedRate': estimated_rate,
            'estimatedCommission': estimated_commission,
            'url': p.get('productUrl', ''),
            'rank': p.get('rank', 0)
        })
    
    # 예상 수수료율 필터링
    filtered = [x for x in products_with_estimate if x['estimatedRate'] >= min_rate]
    
    if not filtered:
        print(f"⚠️ 예상 수수료율 {min_rate}% 이상 제품이 없습니다.")
        # 전체 중 상위 표시
        products_with_estimate.sort(key=lambda x: x['estimatedRate'], reverse=True)
        return products_with_estimate[:top_n], False
    
    # 예상 수수료율 > 예상 수수료 > 가격 순 정렬
    filtered.sort(
        key=lambda x: (x['estimatedRate'], x['estimatedCommission'], x['price']),
        reverse=True
    )
    
    print(f"📊 예상 수수료율 {min_rate}% 이상: {len(filtered)}개")
    
    return filtered[:top_n], True

def main():
    print("=" * 70)
    print("🎯 쿠팡 파트너스: 예상 고수수료 제품 찾기")
    print("=" * 70)
    
    # 고수수료 카테고리 키워드
    keywords = ["여성의류", "화장품세트", "건강식품"]
    
    all_top_products = []
    
    for kw in keywords:
        print(f"\n{'='*70}")
        print(f"📌 키워드: {kw}")
        print('='*70)
        
        result = search_products(kw, limit=10)
        
        if not result:
            print("❌ 검색 실패")
            continue
        
        # 예상 수수료율 4% 이상 제품 선별
        top_products, has_sufficient = pick_high_estimated_commission(
            result,
            top_n=5,
            min_rate=4.0
        )
        
        if not top_products:
            print("⚠️ 조건에 맞는 제품 없음")
            continue
        
        if not has_sufficient:
            print("ℹ️ 기준 미달, 전체 중 상위 제품 표시")
        
        print(f"\n🏆 예상 고수수료 제품 TOP {len(top_products)}:\n")
        
        for i, item in enumerate(top_products, 1):
            rocket_badge = "🚀" if item['isRocket'] else ""
            
            print(f"{i}. {item['name'][:50]}{rocket_badge}")
            print(f"   💰 가격: {item['price']:,}원")
            print(f"   📂 카테고리: {item['category']}")
            print(f"   📊 예상 수수료율: {item['estimatedRate']}% (추정치)")
            print(f"   💵 예상 수수료: {item['estimatedCommission']:,}원")
            print(f"   🔗 {item['url'][:60]}...")
            print()
            
            all_top_products.append(item)
        
        import time
        time.sleep(1)
    
    print("=" * 70)
    print(f"✅ 완료! 총 {len(all_top_products)}개 예상 고수수료 제품 발견")
    print("=" * 70)
    
    if all_top_products:
        best = max(all_top_products, key=lambda x: x['estimatedRate'])
        print(f"\n🥇 최고 예상 수수료율 제품:")
        print(f"   {best['name'][:50]}")
        print(f"   예상 수수료율: {best['estimatedRate']}%")
        print(f"   예상 수수료: {best['estimatedCommission']:,}원")
        print(f"\n⚠️ 주의: 수수료율은 추정치입니다. 실제 수수료는 쿠팡 파트너스에서 확인하세요.")

if __name__ == "__main__":
    main()
