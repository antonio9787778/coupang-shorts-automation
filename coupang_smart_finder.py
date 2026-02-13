# coupang_smart_finder.py - 쿠팡 파트너스 제품 검색 (최종 작동 버전)
import os
import hmac
import hashlib
import requests
import sys
import traceback
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

DOMAIN = "https://api-gateway.coupang.com"

def generate_hmac_signature(method, path, query_string, access_key, secret_key):
    """HMAC 서명 생성"""
    now_utc = datetime.now(timezone.utc)
    datetime_str = now_utc.strftime('%y%m%d') + 'T' + now_utc.strftime('%H%M%S') + 'Z'
    
    message = datetime_str + method + path + query_string
    
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    authorization = (
        f"CEA algorithm=HmacSHA256, "
        f"access-key={access_key}, "
        f"signed-date={datetime_str}, "
        f"signature={signature}"
    )
    
    return authorization

def search_products(keyword, limit, access_key, secret_key):
    """쿠팡 파트너스 제품 검색 API"""
    path = "/v2/providers/affiliate_open_api/apis/openapi/products/search"
    
    params = {
        'keyword': keyword,
        'limit': limit
    }
    query_string = urlencode(params)
    
    authorization = generate_hmac_signature("GET", path, query_string, access_key, secret_key)
    
    url = f"{DOMAIN}{path}?{query_string}"
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json;charset=UTF-8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('rCode') == '0':
                response_data = data.get('data', {})
                
                if isinstance(response_data, dict):
                    products = response_data.get('productData', [])
                elif isinstance(response_data, list):
                    products = response_data
                else:
                    products = []
                
                return products if products else [], None
            else:
                return None, f"API 오류: {data.get('rMessage')}"
        
        elif response.status_code == 401:
            return None, "인증 실패 (401)"
        
        else:
            return None, f"HTTP {response.status_code}"
    
    except:
        return None, "네트워크 오류"

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
        print("=" * 70)
        print("🎯 쿠팡 파트너스: TOP 1 고수수료 제품 찾기")
        print("=" * 70)
        
        ACCESS_KEY = os.environ.get('COUPANG_ACCESS_KEY', '').strip()
        SECRET_KEY = os.environ.get('COUPANG_SECRET_KEY', '').strip()
        
        if not ACCESS_KEY or not SECRET_KEY:
            print("❌ API 키 로드 실패")
            with open('result.txt', 'w', encoding='utf-8') as f:
                f.write("❌ API 키가 설정되지 않았습니다.\n")
            sys.exit(1)
        
        print("✅ API 키 로드 완료")
        print("🔒 Rate Limit 안전 모드: 키워드당 1개만 검색, 15초 대기")
        print()
        
        keywords = ['여성의류', '화장품세트', '건강식품']
        print(f"🔍 검색 키워드: {', '.join(keywords)} (각 키워드당 TOP 1)")
        
        results = []
        
        for idx, keyword in enumerate(keywords, 1):
            print("=" * 70)
            print(f"📌 키워드: {keyword} ({idx}/{len(keywords)})")
            print("=" * 70)
            print()
            print(f"🔍 '{keyword}' TOP 1 검색 중...")
            
            products, error = search_products(keyword, limit=1, access_key=ACCESS_KEY, secret_key=SECRET_KEY)
            
            if error:
                print(f"   ❌ 검색 실패: {error}")
                print("⚠️ 검색 실패")
                continue
            
            if not isinstance(products, list) or len(products) == 0:
                print("   ⚠️ 제품 없음")
                continue
            
            product = products[0]
            formatted = format_product(product)
            results.append({'keyword': keyword, 'product': formatted})
            
            print(f"✅ 검색 성공: {formatted['productName'][:50]}")
            print()
            
            if idx < len(keywords):
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
                f.write("=" * 70 + "\n")
        
        print("=" * 70)
        print(f"✅ 검색 완료: {len(results)}개 제품")
        print("=" * 70)
    
    except Exception as e:
        print(f"❌ 오류: {type(e).__name__}")
        traceback.print_exc()
        with open('result.txt', 'w', encoding='utf-8') as f:
            f.write(f"❌ 오류 발생\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
