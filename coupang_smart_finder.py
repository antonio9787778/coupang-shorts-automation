# coupang_smart_finder.py - 수익 최적화 완전 반영 버전

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

# 카테고리별 평균 수수료율 (%)
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

# 💡 수익 최적화 1: 시즌별 키워드 자동 변경
def get_seasonal_keywords():
    """현재 월에 맞는 시즌 키워드 반환"""
    month = datetime.now().month
    
    seasonal_map = {
        1: ['겨울패딩', '목도리', '핫팩'],  # 1월
        2: ['발렌타인초콜릿', '화이트데이선물', '졸업선물'],  # 2월
        3: ['봄자켓', '신학기가방', '화이트데이'],  # 3월
        4: ['봄원피스', '봄신발', '야외용품'],  # 4월
        5: ['어버이날선물', '카네이션', '가정의달선물'],  # 5월
        6: ['여름원피스', '선풍기', '썬크림'],  # 6월
        7: ['여름휴가용품', '수영복', '캠핑용품'],  # 7월
        8: ['여름세일', '휴가용품', '선글라스'],  # 8월
        9: ['가을자켓', '추석선물', '등산용품'],  # 9월
        10: ['가을코트', '핼러윈', '단풍여행용품'],  # 10월
        11: ['겨울준비', '블랙프라이데이', '난방용품'],  # 11월
        12: ['크리스마스선물', '연말선물', '겨울패딩']  # 12월
    }
    
    base_keywords = ['여성의류', '화장품세트', '건강식품']  # 기본 고수수료 카테고리
    seasonal = seasonal_map.get(month, [])
    
    return base_keywords + seasonal

# 💡 수익 최적화 2: 가격대별 검색 (1-3만원대 집중)
PRICE_RANGES = [
    {'min': 10000, 'max': 20000, 'name': '1만원대'},
    {'min': 20000, 'max': 30000, 'name': '2만원대'},
    {'min': 30000, 'max': 50000, 'name': '3-5만원대'}
]

# ==================== HMAC 서명 생성 ====================
def generate_hmac(method, path, secret_key):
    """쿠팡 API HMAC 서명 생성"""
    datetime_str = datetime.utcnow().strftime('%y%m%d') + 'T' + datetime.utcnow().strftime('%H%M%S') + 'Z'
    message = datetime_str + method + path
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={ACCESS_KEY}, signed-date={datetime_str}, signature={signature}"

# ==================== 쿠팡 제품 검색 ====================
def search_products(keyword, price_min=None, price_max=None, limit=10):
    """쿠팡 제품 검색 - 가격 범위 지정 가능"""
    path = f"/v2/providers/affiliate_open_api/apis/openapi/products/search?keyword={quote(keyword)}&limit={limit}"
    
    # 가격 범위 추가
    if price_min:
        path += f"&minPrice={price_min}"
    if price_max:
        path += f"&maxPrice={price_max}"
    
    url = DOMAIN + path
    authorization = generate_hmac("GET", path, SECRET_KEY)
    
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API 오류 [{keyword}]: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 요청 실패 [{keyword}]: {str(e)}")
        return None

# ==================== 수수료율 예측 ====================
def estimate_commission_rate(product):
    """카테고리, 가격, 배송 타입 기반 수수료율 예측"""
    category_name = product.get('categoryName', '')
    price = product.get('productPrice', 0)
    is_rocket = product.get('isRocket', False)
    
    # 기본 카테고리 수수료율
    commission_rate = 3.5  # 기본값
    for key, rate in CATEGORY_COMMISSION.items():
        if key in category_name:
            commission_rate = rate
            break
    
    # 💡 가격대 보정: 저가 제품 우대
    if price <= 20000:
        commission_rate += 0.5
    elif price >= 100000:
        commission_rate -= 0.5
    
    # 💡 로켓배송 보정: 구매전환율 높음
    if is_rocket:
        commission_rate += 0.3
    
    return round(commission_rate, 1)

# ==================== 제품 분석 및 정렬 ====================
def analyze_products(products):
    """제품 분석 후 수익성 기준으로 정렬"""
    analyzed = []
    
    for product in products:
        price = product.get('productPrice', 0)
        commission_rate = estimate_commission_rate(product)
        commission_amount = int(price * (commission_rate / 100))
        is_rocket = product.get('isRocket', False)
        
        analyzed.append({
            'product': product,
            'price': price,
            'commission_rate': commission_rate,
            'commission_amount': commission_amount,
            'is_rocket': is_rocket,
            # 💡 우선순위 점수: 로켓배송 + 수수료율 + 저가 보너스
            'priority_score': (
                commission_rate * 10 +  # 수수료율 가중치
                (20 if is_rocket else 0) +  # 로켓배송 보너스
                (10 if 10000 <= price <= 30000 else 0)  # 저가 보너스
            )
        })
    
    # 💡 수익 최적화 3: 우선순위 점수로 정렬
    analyzed.sort(key=lambda x: x['priority_score'], reverse=True)
    return analyzed

# ==================== 메인 실행 ====================
def main():
    print("=" * 70)
    print("🎯 쿠팡 파트너스 수익 최적화 제품 검색 시작")
    print(f"📅 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    if not ACCESS_KEY or not SECRET_KEY:
        print("❌ API 키가 설정되지 않았습니다.")
        return
    
    # 💡 시즌별 키워드 자동 선택
    keywords = get_seasonal_keywords()
    print(f"\n🔍 이번 달 검색 키워드: {', '.join(keywords)}\n")
    
    all_high_commission = []
    results_by_keyword = {}
    
    for keyword in keywords:
        print(f"\n{'=' * 70}")
        print(f"📌 키워드: {keyword}")
        print(f"{'=' * 70}\n")
        
        keyword_products = []
        
        # 💡 가격대별 검색 (1-3만원대 집중)
        for price_range in PRICE_RANGES:
            print(f"💰 {price_range['name']} 검색 중...")
            
            data = search_products(
                keyword,
                price_min=price_range['min'],
                price_max=price_range['max'],
                limit=10
            )
            
            if not data or data.get('rCode') != '0':
                continue
            
            products = data.get('data', {}).get('productData', [])
            if products:
                analyzed = analyze_products(products)
                keyword_products.extend(analyzed)
        
        if not keyword_products:
            print(f"⚠️ 제품을 찾지 못했습니다.\n")
            continue
        
        # 중복 제거 (productId 기준)
        seen_ids = set()
        unique_products = []
        for item in keyword_products:
            prod_id = item['product'].get('productId')
            if prod_id not in seen_ids:
                seen_ids.add(prod_id)
                unique_products.append(item)
        
        # 우선순위 점수 기준 재정렬
        unique_products.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # TOP 3 출력
        top_products = unique_products[:3]
        results_by_keyword[keyword] = top_products
        
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
        
        # 고수수료 제품 수집 (5% 이상)
        high_commission = [item for item in unique_products if item['commission_rate'] >= 5.0]
        all_high_commission.extend(high_commission)
    
    # ==================== 전체 요약 ====================
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
        
        # 💡 카테고리별 통계
        print(f"\n📂 카테고리별 분포:")
        category_count = {}
        for item in all_high_commission:
            cat = item['product'].get('categoryName', '기타')
            category_count[cat] = category_count.get(cat, 0) + 1
        
        for cat, count in sorted(category_count.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   - {cat}: {count}개")
        
        # 💡 로켓배송 비율
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
