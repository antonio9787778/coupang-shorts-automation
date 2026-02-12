import os
import hmac
import hashlib
import requests
from time import gmtime, strftime
from urllib.parse import urlencode

DOMAIN = "https://api-gateway.coupang.com"
PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/products/search"

ACCESS_KEY = os.getenv("COUPANG_ACCESS_KEY")
SECRET_KEY = os.getenv("COUPANG_SECRET_KEY")

if not ACCESS_KEY or not SECRET_KEY:
    raise SystemExit(
        "❌ COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY 가 없습니다.\n"
        "GitHub Secrets에 등록 후 다시 실행하세요."
    )

print("✅ API 키 로드 완료")

def signed_date_gmt():
    """Coupang HMAC 서명용 GMT 시간"""
    return strftime("%y%m%dT%H%M%SZ", gmtime())

def make_authorization(method: str, path: str, query: str):
    """쿠팡 API 인증 헤더 생성"""
    dt = signed_date_gmt()
    message = dt + method + path + query
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={ACCESS_KEY}, signed-date={dt}, signature={signature}"

def search_products(keyword: str, limit: int = 10): # 50 -> 10 으로 변경
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
        
        response_json = r.json()
        
        # === 디버깅 시작 ===
        print(f"\n{'='*70}")
        print("🔍 API 응답 디버깅")
        print('='*70)
        print(f"📋 응답 최상위 키: {list(response_json.keys())}")
        
        if 'data' in response_json:
            data = response_json['data']
            print(f"📋 data 타입: {type(data)}")
            print(f"📋 data 길이: {len(data) if isinstance(data, list) else 'N/A'}")
            if isinstance(data, list) and len(data) > 0:
                print(f"📋 첫 번째 항목 키: {list(data[0].keys())}")
                print(f"📋 첫 번째 항목 내용:")
                import json
                print(json.dumps(data[0], indent=2, ensure_ascii=False))
            else:
                print(f"⚠️ data가 비어있거나 리스트가 아님: {data}")
        else:
            print(f"⚠️ 'data' 키가 없음")
            print(f"📋 전체 응답:")
            import json
            print(json.dumps(response_json, indent=2, ensure_ascii=False))
        
        print('='*70)
        # === 디버깅 끝 ===
        
        return response_json

    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP 에러: {e}")
        print(f"응답: {r.text}")
        return None
    except Exception as e:
        print(f"❌ 요청 실패: {e}")
        return None

def pick_high_commission_rate(products_json, top_n: int = 5, min_rate: float = 5.0):
    """
    수수료율이 높은 제품 선별
    정렬 우선순위: 수수료율 > 예상수수료 > 가격
    """
    data = products_json.get("data") or []
    
    if not data:
        print("⚠️ 검색 결과 없음")
        return [], False
    
    rows = []
    for p in data:
        name = p.get("productName", "제품명 없음")
        price = p.get("productPrice", 0)
        url = p.get("productUrl", "")
        rate = p.get("commissionRate")
        
        if rate is None:
            rate = 0.0
        
        est_commission = int(price * (float(rate) / 100.0)) if rate and price else 0
        
        rows.append({
            "name": name,
            "price": int(price) if price else 0,
            "commissionRate": float(rate),
            "estCommission": est_commission,
            "url": url,
        })
    
    # 수수료율 최소 조건 필터링
    filtered = [x for x in rows if x["commissionRate"] >= min_rate]
    
    if not filtered:
        print(f"⚠️ 수수료율 {min_rate}% 이상 제품이 없습니다.")
        # 임시로 전체 중 수수료율 높은 순 표시
        rows.sort(key=lambda x: x["commissionRate"], reverse=True)
        return rows[:top_n], False
    
    # 수수료율 높은 순 → 예상수수료 → 가격 순 정렬
    filtered.sort(
        key=lambda x: (x["commissionRate"], x["estCommission"], x["price"]), 
        reverse=True
    )
    
    print(f"📊 전체 {len(data)}개 중 {len(filtered)}개 선택됨 (수수료 {min_rate}% 이상)")
    
    return filtered[:top_n], True

def main():
    print("=" * 70)
    print("🔍 쿠팡 파트너스: 수수료율 높은 제품 찾기")
    print("=" * 70)
    
    # 검색할 키워드 (수정 가능)
    keywords = ["무선이어폰", "블루투스스피커", "보조배터리"]
    
    all_top_products = []
    
    for kw in keywords:
        print(f"\n{'='*70}")
        print(f"📌 키워드: {kw}")
        print('='*70)
        
        # API 호출
        result = search_products(kw, limit=10)  # 50 → 10으로 변경
        
        if not result:
            print("❌ API 호출 실패 또는 결과 없음")
            continue
        
        # 수수료율 5% 이상 제품 선별
        top_products, has_sufficient = pick_high_commission_rate(
            result, 
            top_n=5, 
            min_rate=5.0
        )
        
        if not top_products:
            print("⚠️ 조건에 맞는 제품 없음")
            continue
        
        if not has_sufficient:
            print("⚠️ 수수료율 5% 이상 제품이 없어서 전체 중 상위 5개를 표시합니다.")
        
        print(f"\n🏆 수수료율 높은 제품 TOP {len(top_products)}:\n")
        
        for i, item in enumerate(top_products, 1):
            print(f"{i}. {item['name'][:50]}")
            print(f"   💰 가격: {item['price']:,}원")
            print(f"   📊 수수료율: {item['commissionRate']}%")
            print(f"   💵 예상 수수료: {item['estCommission']:,}원")
            print(f"   🔗 {item['url'][:60]}...")
            print()
            
            all_top_products.append(item)
        
        # API 호출 제한 방지
        import time
        time.sleep(1)
    
    print("=" * 70)
    print(f"✅ 완료! 총 {len(all_top_products)}개 고수수료율 제품 발견")
    print("=" * 70)
    
    # 전체 중 최고 수수료율 제품
    if all_top_products:
        best = max(all_top_products, key=lambda x: x["commissionRate"])
        print(f"\n🥇 최고 수수료율 제품:")
        print(f"   {best['name'][:50]}")
        print(f"   수수료율: {best['commissionRate']}%")
        print(f"   예상 수수료: {best['estCommission']:,}원")

if __name__ == "__main__":
    main()
