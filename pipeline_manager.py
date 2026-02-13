# search_coupang_products.py
import os
import hmac
import hashlib
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode

def generate_hmac(method, path, query, secret_key, access_key):
    """HMAC 서명 생성 (Windows 호환)"""
    # GMT+0 시간 생성
    gmt_time = datetime.utcnow()  # ⭐ utcnow() 사용
    gmt_time_str = "{:%y%m%d}T{:%H%M%S}Z".format(gmt_time, gmt_time)
    
    # 메시지 생성: datetime + method + path + query
    message = gmt_time_str + method + path + query
    
    # HMAC-SHA256 서명
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Authorization 헤더
    authorization = (
        f"CEA algorithm=HmacSHA256, "
        f"access-key={access_key}, "
        f"signed-date={gmt_time_str}, "
        f"signature={signature}"
    )
    
    return authorization

def search_products(keyword, limit=1):
    """쿠팡 파트너스 제품 검색"""
    # ⭐ GitHub Secrets에서 로드
    ACCESS_KEY = os.environ.get('COUPANG_ACCESS_KEY')
    SECRET_KEY = os.environ.get('COUPANG_SECRET_KEY')
    
    if not ACCESS_KEY or not SECRET_KEY:
        print("❌ API 키가 없습니다. GitHub Secrets 확인 필요")
        return None
    
    # API 엔드포인트
    DOMAIN = "https://api-gateway.coupang.com"
    PATH = "/v2/providers/affiliate_open_api/openapi/v1/products/search"
    
    # 쿼리 파라미터
    params = {
        'keyword': keyword,
        'limit': limit
    }
    query_string = urlencode(params)
    
    # ⭐ 매 호출마다 새로 생성
    authorization = generate_hmac(
        method="GET",
        path=PATH,
        query=query_string,
        secret_key=SECRET_KEY,
        access_key=ACCESS_KEY
    )
    
    # API 요청
    url = f"{DOMAIN}{PATH}?{query_string}"
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json;charset=UTF-8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ '{keyword}' 검색 성공")
            return response.json()
        elif response.status_code == 401:
            print(f"❌ 인증 실패 (401): {response.text}")
            print("   → ACCESS_KEY/SECRET_KEY 확인")
            print("   → 시간 동기화 확인")
            return None
        else:
            print(f"⚠️ API 오류 ({response.status_code}): {response.text}")
            return None
    
    except requests.exceptions.Timeout:
        print("❌ 타임아웃: 쿠팡 API 응답 없음")
        return None
    except Exception as e:
        print(f"❌ 오류: {e}")
        return None

if __name__ == "__main__":
    # 테스트
    result = search_products("여성의류", limit=1)
    if result:
        print(result)
