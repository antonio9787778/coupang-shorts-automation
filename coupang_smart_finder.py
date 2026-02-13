import hmac
import hashlib
import requests
import os
import time
from datetime import datetime
from urllib.parse import quote

# ==================== 설정 ====================
ACCESS_KEY = os.environ.get('COUPANG_ACCESS_KEY')
SECRET_KEY = os.environ.get('COUPANG_SECRET_KEY')
DOMAIN = "https://api-gateway.coupang.com"

# 카테고리별 수수료율
CATEGORY_RATES = {
    '패션의류': 6.0, '패션잡화': 6.0, '남성패션': 6.0, '여성패션': 6.0,
    '뷰티': 5.0, '화장품': 5.0, '향수': 5.0,
    '식품': 5.0, '건강': 5.0, '건강식품': 5.0,
    '생활': 4.0, '주방': 4.0,
    '가전': 3.0, '디지털': 3.0
}

# ==================== 초기 검증 ====================
print("=" * 70)
print("🎯 쿠팡 파트너스: TOP 1 고수수료 제품 찾기")
print("=" * 70)
print()

if not ACCESS_KEY:
    print("❌ 오류: COUPANG_ACCESS_KEY 환경 변수가 없습니다!")
    exit(1)

if not SECRET_KEY:
    print("❌ 오류: COUPANG_SECRET_KEY 환경 변수가 없습니다!")
    exit(1)

print("✅ API 키 로드 완료")
print("🔒 Rate Limit 안전 모드: 키워드당 1개만 검색, 15초 대기")
print()

# ==================== HMAC 서명 생성 ====================
def generate_hmac_signature(method, url, secret_key, access_key):
    """쿠팡 공식 HMAC 서명 생성"""
    path = url.replace(DOMAIN, "")
    
    datetime_utc = datetime.utcnow()
    datetime_str = datetime_utc.strftime('%y%m%d') + 'T' + datetime_utc.strftime('%H%M%S') + 'Z'
    
    message = datetime_str + method + path
    
    signature = hmac.new(
        bytes(secret_key, 'utf-8'),
        bytes(message, 'utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    authorization = "CEA algorithm=HmacSHA256, access-key={}, signed-date={}, signature={}".format(
        access_key, datetime_str, signature
    )
    
    return authorization

# ==================== 제품 검색 (재시도 로직 포함) ====================
def search_products(keyword, limit=1, max_retries=3):
    """
    쿠팡 제품 검색 API 호출
    limit=1: TOP 1만 검색 (Rate Limit 안전)
    """
    encoded_keyword = quote(keyword)
    request_url = "{}/v2/providers/affiliate_open_api/apis/openapi/products/search?keyword={}&limit={}".format(
        DOMAIN, encoded_keyword, limit
    )
    
    for attempt in range(max_retries):
        try:
            authorization = generate_hmac_signature("GET", request_url, SECRET_KEY, ACCESS_KEY)
            
            headers = {
                "Authorization": authorization,
                "Content-Type": "application/json"
            }
            
            response = requests.get(request_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            
            elif response.status_code == 429:
                wait_time = 30  # Rate limit 시 30초 대기
                print("   ⚠️ Rate limit 발생! {}초 대기 후 재시도...".format(wait_time))
                time.sleep(wait_time)
                continue
            
            elif response.status_code == 401:
                print("   ❌ 인증 실패 (401): API 키를 확인하세요")
                return None
            
            else:
                print("   ❌ API 오류 (상태 코드: {})".format(response.status_code))
                return None
        
        except requests.exceptions.Timeout:
            print("   ⚠️ 타임아웃 (시도 {}/{})".format(attempt + 1, max_retries))
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            return None
        
        except requests.exceptions.ConnectionError:
            print("   ⚠️ 연결 오류 (시도 {}/{})".format(attempt + 1, max_retries))
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            return None
        
        except Exception as e:
            print("   ❌ 예외 발생: {}".format(type(e).__name__))
            return None
    
    print("   ❌ {}회 재시도 후 실패".format(max_retries))
    return None

# ==================== 수수료율 계산 ====================
def get_commission_rate(category, price, is_rocket):
    """카테고리, 가격, 배송 타입 기반 수수료율 예측"""
    rate = 4.0
    
    for key, val in CATEGORY_RATES.items():
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

# ==================== 메인 실행 ====================
def main():
    # 검색 키워드 (필요시 더 추가 가능)
    keywords = ['여성의류', '화장품세트', '건강식품']
    
    print("🔍 검색 키워드: {} (각 키워드당 TOP 1)\n".format(', '.join(keywords)))
    
    all_results = []
    
    for idx, keyword in enumerate(keywords):
        print("=" * 70)
        print("📌 키워드: {} ({}/{})".format(keyword, idx + 1, len(keywords)))
        print("=" * 70)
        print("🔍 '{}' TOP 1 검색 중...".format(keyword))
        
        # API 호출 (limit=1)
        data = search_products(keyword, limit=1)
        
        if not data:
            print("⚠️ 검색 실패\n")
            
            if idx < len(keywords) - 1:
                wait_time = 15
                print("⏳ Rate Limit 안전을 위해 {}초 대기...\n".format(wait_time))
                time.sleep(wait_time)
            continue
        
        if data.get('rCode') != '0':
            print("⚠️ API 응답 오류: {}".format(data.get('rMessage', 'Unknown')))
            print()
            
            if idx < len(keywords) - 1:
                time.sleep(15)
            continue
        
        products = data.get('data', {}).get('productData', [])
        
        if not products:
            print("⚠️ 제품 없음\n")
            
            if idx < len(keywords) - 1:
                time.sleep(15)
            continue
        
        print("✅ API 호출 성공 (상태: 200)")
        print("📊 TOP 1 제품 발견\n")
        
        # TOP 1 제품 분석
        product = products[0]
        price = product.get('productPrice', 0)
        category = product.get('categoryName', '')
        is_rocket = product.get('isRocket', False)
        
        rate = get_commission_rate(category, price, is_rocket)
        commission = int(price * rate / 100)
        
        print("🏆 예상 고수수료 제품 TOP 1:\n")
        
        rocket_icon = "🚀" if is_rocket else ""
        name = product.get('productName', 'N/A')
        
        print("1. {}{}".format(name, rocket_icon))
        print("   💰 가격: {:,}원".format(price))
        print("   📂 카테고리: {}".format(category))
        print("   📊 예상 수수료율: {}% (추정치)".format(rate))
        print("   💵 예상 수수료: {:,}원".format(commission))
        print("   🔗 [쿠팡 링크]\n")
        
        all_results.append({
            'keyword': keyword,
            'name': name,
            'price': price,
            'category': category,
            'rate': rate,
            'commission': commission,
            'rocket': is_rocket
        })
        
        # 다음 키워드 전 대기 (Rate Limit 안전)
        if idx < len(keywords) - 1:
            wait_time = 15
            print("⏳ Rate Limit 안전을 위해 {}초 대기...\n".format(wait_time))
            
            # 카운트다운
            for remaining in range(wait_time, 0, -5):
                print("   {}초 남음...".format(remaining))
                time.sleep(5)
            print()
    
    # ==================== 전체 요약 ====================
    print("=" * 70)
    
    if all_results:
        all_results.sort(key=lambda x: x['commission'], reverse=True)
        best = all_results[0]
        
        print("✅ 완료! 총 {}개 예상 고수수료 제품 발견 (각 카테고리 TOP 1)".format(len(all_results)))
        print("=" * 70)
        print()
        
        print("📋 카테고리별 결과:\n")
        for item in all_results:
            rocket_icon = "🚀" if item['rocket'] else ""
            print("▪️ {}: {}{}".format(item['keyword'], item['name'][:40], rocket_icon))
            print("   💰 {:,}원 | 📊 {}% | 💵 {:,}원\n".format(
                item['price'], item['rate'], item['commission']
            ))
        
        print("=" * 70)
        print("🥇 최고 예상 수수료율 제품:")
        print("   카테고리: {}".format(best['keyword']))
        print("   제품: {}".format(best['name']))
        print("   예상 수수료율: {}%".format(best['rate']))
        print("   예상 수수료: {:,}원".format(best['commission']))
        print()
        print("⚠️ 주의: 수수료율은 추정치입니다. 실제 수수료는 쿠팡 파트너스에서 확인하세요.")
    else:
        print("⚠️ 예상 고수수료 제품을 찾지 못했습니다.")
        print("=" * 70)
        print()
        print("가능한 원인:")
        print("- API 키 인증 문제")
        print("- 검색 키워드 문제")
        print("- 일시적 API 오류")
        print()
        print("해결 방법:")
        print("1. GitHub Secrets에서 API 키 재확인")
        print("2. 쿠팡 파트너스에서 키 재발급")
        print("3. 잠시 후 다시 시도")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
