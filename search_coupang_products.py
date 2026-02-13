# search_coupang_products.py - 쿠팡 파트너스 제품 검색 (401 오류 해결 버전)
import os
import hmac
import hashlib
import requests
import json
import sys
import traceback
from datetime import datetime, timezone
from urllib.parse import urlencode

DOMAIN = "https://api-gateway.coupang.com"

def generate_hmac_signature(method, path, query_string, access_key, secret_key):
    """
    HMAC 서명 생성 (Windows/Linux 모두 작동)
    
    ⭐ 핵심: datetime.now(timezone.utc) 사용으로 GMT+0 시간 정확히 생성
    """
    # GMT+0 (UTC) 시간 생성
    now_utc = datetime.now(timezone.utc)
    datetime_str = now_utc.strftime('%y%m%d') + 'T' + now_utc.strftime('%H%M%S') + 'Z'
    
    # 서명 메시지: datetime + method + path + query
    message = datetime_str + method + path + query_string
    
    # HMAC-SHA256 생성
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Authorization 헤더
    authorization = (
        f"CEA algorithm=HmacSHA256, "
        f"access-key={access_key}, "
        f"signed-date={datetime_str}, "
        f"signature={signature}"
    )
    
    return authorization

def search_products(keyword, limit, access_key, secret_key):
    """쿠팡 파트너스 제품 검색 API"""
    if not access_key or not secret_key:
        return None, "API 키가 없습니다"
    
    # 파트너스 API 엔드포인트
    path = "/v2/providers/affiliate_open_api/apis/openapi/products/search"
    
    # 쿼리 파라미터
    params = {
        'keyword': keyword,
        'limit': limit
    }
    query_string = urlencode(params)
    
    # ⭐ 매 요청마다 새로 생성
    authorization = generate_hmac_signature("GET", path, query_string, access_key, secret_key)
    
    # API 요청
    url = f"{DOMAIN}{path}?{query_string}"
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json;charset=UTF-8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            # 성공 시 data 구조: {"rCode": "0", "rMessage": "OK", "data": [...]}
            if data.get('rCode') == '0':
                return data.get('data', []), None
            else:
                return None, f"API 오류: {data.get('rMessage')}"
        
        elif response.status_code == 401:
            return None, f"인증 실패 (401): {response.text[:200]}"
        
        else:
            return None, f"HTTP {response.status_code}: {response.text[:200]}"
    
    except requests.exceptions.Timeout:
        return None, "타임아웃 (15초 초과)"
    except Exception as e:
        return None, str(e)

def format_product(product):
    """제품 데이터 포맷팅"""
    return {
        'productId': product.get('productId', ''),
        'productName': product.get('productName', ''),
        'productPrice': product.get('productPrice', 0),
        'productImage': product.get('productImage', ''),
        'productUrl': product.get('productUrl', ''),
        'isRocket': product.get('isRocket', False),
        'categoryName': product.get('categoryName', ''),
    }

def main():
    """메인 실행"""
    try:
        print("🔍 쿠팡 제품 검색 + Deeplink 변환 시작...")
        print("=" * 70)
        print("🎯 쿠팡 파트너스: TOP 1 고수수료 제품 찾기")
        print("=" * 70)
        print()
        
        # ⭐ main() 함수 내부에서 환경변수 가져오기
        ACCESS_KEY = os.environ.get('COUPANG_ACCESS_KEY', '')
        SECRET_KEY = os.environ.get('COUPANG_SECRET_KEY', '')
        
        # API 키 확인
        if not ACCESS_KEY or not SECRET_KEY:
            print("❌ API 키 로드 실패")
            print("   GitHub Secrets 확인 필요:")
            print("   - COUPANG_ACCESS_KEY")
            print("   - COUPANG_SECRET_KEY")
            with open('result.txt', 'w', encoding='utf-8') as f:
                f.write("❌ API 키가 설정되지 않았습니다.\n")
            sys.exit(1)
        
        print("✅ API 키 로드 완료")
        print(f"   ACCESS_KEY: {ACCESS_KEY[:10]}...")
        print(f"   SECRET_KEY: {SECRET_KEY[:10]}...")
        print("🔒 Rate Limit 안전 모드: 키워드당 1개만 검색, 15초 대기")
        print()
        
        keywords = ['여성의류', '화장품세트', '건강식품']
        print(f"🔍 검색 키워드: {', '.join(keywords)} (각 키워드당 TOP 1)")
        print()
        
        results = []
        
        for idx, keyword in enumerate(keywords, 1):
            print("=" * 70)
            print(f"📌 키워드: {keyword} ({idx}/{len(keywords)})")
            print("=" * 70)
            print()
            print(f"🔍 '{keyword}' TOP 1 검색 중...")
            
            # ⭐ 함수 호출 시 키 전달
            products, error = search_products(keyword, limit=1, access_key=ACCESS_KEY, secret_key=SECRET_KEY)
            
            if error:
                print(f"   ❌ 검색 실패: {error}")
                print()
                continue
            
            if not products:
                print("   ⚠️ 제품 없음")
                print()
                continue
            
            # 첫 번째 제품만 사용
            product = products[0]
            formatted = format_product(product)
            results.append({'keyword': keyword, 'product': formatted})
            
            print(f"✅ 검색 성공:")
            print(f"   1. {formatted['productName'][:50]}")
            print(f"      💰 가격: {formatted['productPrice']:,}원")
            if formatted['isRocket']:
                print(f"      🚀 로켓배송")
            print(f"      📂 카테고리: {formatted['categoryName']}")
            print(f"      🔗 파트너스 링크: {formatted['productUrl'][:60]}...")
            print()
            
            # Rate limit 안전
            if idx < len(keywords):
                import time
                print("⏳ 15초 대기 중...")
                time.sleep(15)
        
        # result.txt 저장
        with open('result.txt', 'w', encoding='utf-8') as f:
            if results:
                for idx, item in enumerate(results, 1):
                    keyword = item['keyword']
                    product = item['product']
                    
                    f.write(f"=" * 70 + "\n")
                    f.write(f"📌 키워드: {keyword} ({idx}/{len(results)})\n")
                    f.write(f"=" * 70 + "\n\n")
                    
                    f.write(f"1. {product['productName']}\n")
                    f.write(f"   💰 가격: {product['productPrice']:,}원\n")
                    f.write(f"   📂 카테고리: {product['categoryName']}\n")
                    f.write(f"   📊 예상 수수료율: 5.0%\n")
                    f.write(f"   💵 예상 수수료: {int(product['productPrice'] * 0.05):,}원\n")
                    if product['isRocket']:
                        f.write(f"   🚀 로켓배송\n")
                    f.write(f"   🔗 파트너스 링크: {product['productUrl']}...\n")
                    f.write("\n")
            else:
                f.write("=" * 70 + "\n")
                f.write("⚠️ 예상 고수수료 제품을 찾지 못했습니다.\n")
                f.write("=" * 70 + "\n\n")
                f.write("가능한 원인:\n")
                f.write("- API 키 인증 문제\n")
                f.write("- 검색 키워드 문제\n")
                f.write("- 일시적 API 오류\n\n")
                f.write("해결 방법:\n")
                f.write("1. GitHub Secrets에서 API 키 재확인\n")
                f.write("2. 쿠팡 파트너스에서 키 재발급\n")
                f.write("3. 잠시 후 다시 시도\n")
                f.write("=" * 70 + "\n")
        
        print("=" * 70)
        if results:
            print(f"✅ 검색 완료: {len(results)}개 제품")
            print(f"💾 result.txt 저장 완료")
        else:
            print("⚠️ 예상 고수수료 제품을 찾지 못했습니다.")
        print("=" * 70)
    
    except Exception as e:
        # ⭐ 예외 발생 시 상세 정보 출력
        print()
        print("=" * 70)
        print("❌ 치명적 오류 발생!")
        print("=" * 70)
        print(f"오류 타입: {type(e).__name__}")
        print(f"오류 메시지: {e}")
        print()
        
        print("스택 트레이스:")
        traceback.print_exc()
        
        # 에러 내용도 result.txt에 저장
        with open('result.txt', 'w', encoding='utf-8') as f:
            f.write(f"❌ 오류 발생: {e}\n")
            f.write(f"\n{traceback.format_exc()}\n")
        
        sys.exit(1)

if __name__ == "__main__":
    main()
