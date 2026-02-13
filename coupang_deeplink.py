# coupang_deeplink.py - 일반 URL → 파트너스 링크 변환

import hmac
import hashlib
import requests
import json
import os
from datetime import datetime

ACCESS_KEY = os.environ.get('COUPANG_ACCESS_KEY')
SECRET_KEY = os.environ.get('COUPANG_SECRET_KEY')
DOMAIN = "https://api-gateway.coupang.com"
DEEPLINK_URL = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"

def generate_hmac_signature(method, url, secret_key, access_key):
    """HMAC 서명 생성 (POST 방식)"""
    path = url.split('?')[0].replace(DOMAIN, '')
    
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

def convert_to_deeplink(product_urls):
    """
    일반 쿠팡 URL을 파트너스 링크로 변환
    
    Args:
        product_urls: 문자열 또는 리스트 (쿠팡 제품 URL)
    
    Returns:
        변환된 파트너스 링크 (문자열 또는 리스트)
    """
    
    if not ACCESS_KEY or not SECRET_KEY:
        print("  ⚠️ API 키가 설정되지 않았습니다.")
        return product_urls
    
    # 단일 URL을 리스트로 변환
    single_url = isinstance(product_urls, str)
    if single_url:
        product_urls = [product_urls]
    
    # 빈 URL 필터링
    product_urls = [url for url in product_urls if url and url.strip()]
    
    if not product_urls:
        return "" if single_url else []
    
    # API 요청
    request_url = DOMAIN + DEEPLINK_URL
    
    request_body = {
        "coupangUrls": product_urls
    }
    
    try:
        authorization = generate_hmac_signature("POST", request_url, SECRET_KEY, ACCESS_KEY)
        
        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            request_url,
            headers=headers,
            data=json.dumps(request_body),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('rCode') == '0':
                deeplinks = data.get('data', [])
                
                # URL 매칭
                result = []
                for original_url in product_urls:
                    found = False
                    for deeplink_item in deeplinks:
                        if deeplink_item.get('originalUrl') == original_url:
                            result.append(deeplink_item.get('shortenUrl', original_url))
                            found = True
                            break
                    
                    if not found:
                        result.append(original_url)
                
                print(f"  ✅ Deeplink 변환 완료: {len(result)}개")
                return result[0] if single_url else result
            else:
                print(f"  ⚠️ Deeplink API 오류: {data.get('rMessage')}")
                return product_urls[0] if single_url else product_urls
        
        else:
            print(f"  ⚠️ Deeplink API 실패 (상태: {response.status_code})")
            return product_urls[0] if single_url else product_urls
    
    except Exception as e:
        print(f"  ⚠️ Deeplink 변환 오류: {e}")
        return product_urls[0] if single_url else product_urls


if __name__ == "__main__":
    print("🔗 Deeplink API 모듈")
    print("일반 쿠팡 URL → 파트너스 링크 변환")
