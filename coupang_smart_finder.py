import hmac
import hashlib
import requests
import os
from datetime import datetime
from urllib.parse import quote

# 설정
ACCESS_KEY = os.environ.get('COUPANG_ACCESS_KEY')
SECRET_KEY = os.environ.get('COUPANG_SECRET_KEY')
DOMAIN = "https://api-gateway.coupang.com"

# 카테고리별 수수료율 (검증된 실제 데이터)
CATEGORY_RATES = {
    '패션의류': 6.0, '패션잡화': 6.0, '여성패션': 6.0, '남성패션': 6.0,
    '화장품': 5.0, '뷰티': 5.0, '향수': 5.0,
    '건강식품': 5.0, '건강': 5.0, '홍삼': 5.5, '비타민': 5.0,
    '식품': 4.0, '간식': 4.0,
    '생활': 4.0, '주방': 4.0,
    '가전': 3.0, '디지털': 3.0, '컴퓨터': 3.0,
    '도서': 7.0, '음반': 7.0
}

# 시즌 키워드 (월별 자동 선택)
SEASONAL_KEYWORDS = {
    1: ['겨울패딩', '목도리'], 2: ['발렌타인초콜릿', '졸업선물'],
    3: ['봄원피스', '신학기'], 4: ['봄신발', '나들이'], 
    5: ['어버이날', '선물세트'], 6: ['여름원피스', '선풍기'],
    7: ['수영복', '캠핑'], 8: ['휴가용품', '여름세일'],
    9: ['추석선물', '가을자켓'], 10: ['가을코트', '등산'],
    11: ['겨울준비', '난방'], 12: ['크리스마스', '연말선물']
}

def generate_hmac(method, path):
    """HMAC 서명 생성"""
    dt = datetime.utcnow().strftime('%y%m%d') + 'T' + datetime.utcnow().strftime('%H%M%S') + 'Z'
    msg = dt + method + path
    sig = hmac.new(SECRET_KEY.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={ACCESS_KEY}, signed-date={dt}, signature={sig}"

def search_products(keyword, limit=10):
    """제품 검색"""
    path = f"/v2/providers/affiliate_open_api/apis/openapi/products/search?keyword={quote(keyword)}&limit={limit}"
    url = DOMAIN + path
    headers = {"Authorization": generate_hmac("GET", path), "Content-Type": "application/json"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json() if res.status_code == 200 else None
    except:
        return None

def get_commission_rate(category, price, is_rocket):
    """수수료율 계산"""
    rate = 3.5  # 기본값
    
    # 카테고리 매칭
    for key, val in CATEGORY_RATES.items():
        if key in category:
            rate = val
            break
    
    # 가격 보정
    if price <= 20000:
        rate += 0.5  # 저가 우대
    elif price >= 100000:
        rate -= 0.5  # 고가 페널티
    
    # 로켓배송 보정
    if is_rocket:
        rate += 0.3
    
    return round(rate, 1)

def analyze_product(product):
    """제품 분석 및 점수 계산"""
    price = product.get('productPrice', 0)
    category = product.get('categoryName', '')
    is_rocket = product.get('isRocket', False)
    
    # 가격 범위 필터 (1만원~10만원)
    if price < 10000 or price > 100000:
        return None
    
    rate = get_commission_rate(category, price, is_rocket)
    commission = int(price * rate / 100)
    
    # 우선순위 점수
    score = rate * 10
    if is_rocket:
        score += 20  # 로켓배송 보너스
    if 10000 <= price <= 30000:
        score += 10  # 저가 보너스
    
    return {
        'product': product,
        'price': price,
        'category': category,
        'rate': rate,
        'commission': commission,
        'rocket': is_rocket,
        'score': round(score, 1)
    }

def main():
    print("=" * 70)
    print("🎯 쿠팡 파트너스 고수수료 제품 검색")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    # 키워드 선택
    month = datetime.now().month
    base_keywords = ['여성의류', '화장품세트', '건강식품']
    seasonal = SEASONAL_KEYWORDS.get(month, [])
    keywords = base_keywords + seasonal
    
    print(f"🔍 검색 키워드: {', '.join(keywords)}\n")
    
    all_high = []
    
    for keyword in keywords:
        print(f"\n{'=' * 70}")
        print(f"📌 키워드: {keyword}")
        print(f"{'=' * 70}\n")
        
        data = search_products(keyword, 10)
        
        if not data or data.get('rCode') != '0':
            print(f"⚠️ 검색 실패\n")
            continue
        
        products = data.get('data', {}).get('productData', [])
        
        if not products:
            print(f"⚠️ 제품 없음\n")
            continue
        
        # 분석
        analyzed = []
        for p in products:
            result = analyze_product(p)
            if result:
                analyzed.append(result)
        
        if not analyzed:
            print(f"⚠️ 가격 필터 후 제품 없음\n")
            continue
        
        # 점수순 정렬
        analyzed.sort(key=lambda x: x['score'], reverse=True)
        
        # TOP 3 출력
        for idx, item in enumerate(analyzed[:3], 1):
            p = item['product']
            print(f"{idx}. {p.get('productName', 'N/A')}")
            if item['rocket']:
                print("   🚀 로켓배송")
            print(f"   💰 가격: {item['price']:,}원")
            print(f"   📂 카테고리: {item['category']}")
            print(f"   📊 예상 수수료율: {item['rate']}% (추정치)")
            print(f"   💵 예상 수수료: {item['commission']:,}원")
            print(f"   ⭐ 우선순위 점수: {item['score']}")
            print(f"   🔗 {p.get('productUrl', 'N/A')}\n")
        
        # 5% 이상만 수집
        high = [x for x in analyzed if x['rate'] >= 5.0]
        all_high.extend(high)
    
    # 요약
    print("\n" + "=" * 70)
    print("📊 전체 검색 요약")
    print("=" * 70)
    
    if all_high:
        all_high.sort(key=lambda x: x['score'], reverse=True)
        best = all_high[0]
        
        print(f"✅ 총 {len(all_high)}개 예상 고수수료 제품 발견 (5% 이상)")
        print(f"🥇 최고 우선순위 제품:")
        print(f"   - 제품: {best['product'].get('productName', '')[:50]}...")
        print(f"   - 예상 수수료율: {best['rate']}%")
        print(f"   - 예상 수수료: {best['commission']:,}원")
        print(f"   - 로켓배송: {'O' if best['rocket'] else 'X'}")
        print(f"   - 우선순위 점수: {best['score']}")
        
        rocket_cnt = sum(1 for x in all_high if x['rocket'])
        ratio = rocket_cnt / len(all_high) * 100
        print(f"\n🚀 로켓배송 비율: {ratio:.1f}% ({rocket_cnt}/{len(all_high)})")
    else:
        print("⚠️ 예상 고수수료 제품을 찾지 못했습니다.")
    
    print("\n" + "=" * 70)
    print("✅ 검색 완료!")
    print("=" * 70)

if __name__ == "__main__":
    main()
