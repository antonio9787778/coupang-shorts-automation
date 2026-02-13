def main():
    """메인 실행"""
    try:
        print("🔍 쿠팡 제품 검색 + Deeplink 변환 시작...")
        print("=" * 70)
        print("🎯 쿠팡 파트너스: TOP 1 고수수료 제품 찾기")
        print("=" * 70)
        print()
        
        # API 키 확인
        if not ACCESS_KEY or not SECRET_KEY:
            print("❌ API 키 로드 실패")
            print("   GitHub Secrets 확인 필요:")
            print("   - COUPANG_ACCESS_KEY")
            print("   - COUPANG_SECRET_KEY")
            with open('result.txt', 'w', encoding='utf-8') as f:
                f.write("❌ API 키가 설정되지 않았습니다.\n")
            import sys
            sys.exit(1)  # ⭐ 명시적 종료
        
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
            
            products, error = search_products(keyword, limit=1)
            
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
        
        import traceback
        print("스택 트레이스:")
        traceback.print_exc()
        
        # 에러 내용도 result.txt에 저장
        with open('result.txt', 'w', encoding='utf-8') as f:
            f.write(f"❌ 오류 발생: {e}\n")
            f.write(f"\n{traceback.format_exc()}\n")
        
        import sys
        sys.exit(1)

if __name__ == "__main__":
    main()
