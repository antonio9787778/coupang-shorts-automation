# pipeline_manager.py - 쿠팡 검색 → 쇼츠 생성 → 업로드 통합

import os
import re
import json
from datetime import datetime
from create_coupang_shorts import create_shorts

def parse_result_txt(result_file='result.txt'):
    """
    result.txt 파싱하여 제품 데이터 추출
    """
    print("=" * 70)
    print("📄 result.txt 파싱 시작")
    print("=" * 70)
    print()
    
    if not os.path.exists(result_file):
        print(f"❌ {result_file} 파일이 없습니다.")
        return []
    
    with open(result_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    products = []
    
    # 키워드 섹션 분리
    keyword_sections = re.split(r'={70}\n📌 키워드: ', content)
    
    for section in keyword_sections[1:]:  # 첫 번째는 헤더이므로 제외
        try:
            # 키워드 추출
            keyword_match = re.match(r'(.+?)\s+\((\d+)/(\d+)\)', section)
            if not keyword_match:
                continue
            
            keyword = keyword_match.group(1).strip()
            
            # 검색 실패 확인
            if '⚠️ 검색 실패' in section or '⚠️ 제품 없음' in section:
                print(f"⚠️ {keyword}: 검색 실패 또는 제품 없음")
                continue
            
            # TOP 1 제품 정보 추출
            # 제품명: "1. 제품명🚀" 형식
            name_match = re.search(r'1\.\s+(.+?)(?:🚀)?\s*\n', section)
            if not name_match:
                print(f"⚠️ {keyword}: 제품명을 찾을 수 없음")
                continue
            
            name = name_match.group(1).strip()
            
            # 가격: "💰 가격: 19,900원"
            price_match = re.search(r'💰 가격:\s+([\d,]+)원', section)
            price = int(price_match.group(1).replace(',', '')) if price_match else 0
            
            # 카테고리: "📂 카테고리: 패션의류"
            category_match = re.search(r'📂 카테고리:\s+(.+)', section)
            category = category_match.group(1).strip() if category_match else ''
            
            # 수수료율: "📊 예상 수수료율: 6.8% (추정치)"
            rate_match = re.search(r'📊 예상 수수료율:\s+([\d.]+)%', section)
            rate = float(rate_match.group(1)) if rate_match else 5.0
            
            # 수수료: "💵 예상 수수료: 1,353원"
            commission_match = re.search(r'💵 예상 수수료:\s+([\d,]+)원', section)
            commission = int(commission_match.group(1).replace(',', '')) if commission_match else 0
            
            # 로켓배송 확인
            rocket = '🚀' in section
            
            # 제품 데이터 구성
            product = {
                'keyword': keyword,
                'name': name,
                'price': price,
                'category': category,
                'rate': rate,
                'commission': commission,
                'rocket': rocket,
                'url': '',  # 보안상 result.txt에 없음
                'image_url': '',  # 나중에 쿠팡 API에서 가져올 예정
                'review_count': 0,  # 더미 데이터
                'rating': 4.5  # 더미 데이터
            }
            
            products.append(product)
            print(f"✅ {keyword}: {name[:40]}... (₩{price:,})")
        
        except Exception as e:
            print(f"⚠️ 섹션 파싱 중 오류: {e}")
            continue
    
    print()
    print(f"📊 총 {len(products)}개 제품 파싱 완료")
    print("=" * 70)
    print()
    
    return products


def save_products_json(products, output_file='products.json'):
    """제품 데이터를 JSON으로 저장"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"💾 제품 데이터 저장: {output_file}")


def create_all_shorts(products):
    """모든 제품에 대해 쇼츠 생성"""
    print("=" * 70)
    print("🎬 쇼츠 생성 시작")
    print("=" * 70)
    print()
    
    created_videos = []
    
    for idx, product in enumerate(products, 1):
        print(f"▶ [{idx}/{len(products)}] {product['keyword']} 쇼츠 생성 중...")
        print()
        
        try:
            video_file = create_shorts(product)
            
            if video_file and os.path.exists(video_file):
                created_videos.append({
                    'keyword': product['keyword'],
                    'video_file': video_file,
                    'product': product
                })
                print(f"✅ 생성 완료: {video_file}")
            else:
                print(f"❌ 생성 실패: {product['keyword']}")
        
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
        
        print()
    
    print("=" * 70)
    print(f"✅ 쇼츠 생성 완료: {len(created_videos)}/{len(products)}개")
    print("=" * 70)
    print()
    
    return created_videos


def generate_summary(products, videos):
    """요약 리포트 생성"""
    print("=" * 70)
    print("📊 최종 요약")
    print("=" * 70)
    print()
    
    print(f"🔍 검색된 제품: {len(products)}개")
    print(f"🎬 생성된 쇼츠: {len(videos)}개")
    print()
    
    if videos:
        print("📹 생성된 쇼츠 목록:")
        for video in videos:
            print(f"  ✅ {video['video_file']}")
            print(f"     제품: {video['product']['name'][:40]}...")
            print(f"     가격: ₩{video['product']['price']:,}")
            print()
    
    # summary.txt 저장
    with open('summary.txt', 'w', encoding='utf-8') as f:
        f.write(f"쿠팡 쇼츠 자동 생성 요약\n")
        f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"\n")
        f.write(f"검색된 제품: {len(products)}개\n")
        f.write(f"생성된 쇼츠: {len(videos)}개\n")
        f.write(f"\n")
        f.write(f"생성된 파일:\n")
        for video in videos:
            f.write(f"  - {video['video_file']}\n")
    
    print("💾 요약 저장: summary.txt")
    print("=" * 70)


def main():
    """전체 파이프라인 실행"""
    print()
    print("=" * 70)
    print("🚀 쿠팡 쇼츠 자동 생성 파이프라인")
    print("=" * 70)
    print()
    
    # Step 1: result.txt 파싱
    products = parse_result_txt('result.txt')
    
    if not products:
        print("❌ 파싱된 제품이 없습니다.")
        print()
        print("해결 방법:")
        print("1. 쿠팡 검색 워크플로우를 먼저 실행하세요")
        print("2. result.txt 파일이 생성되었는지 확인하세요")
        return
    
    # Step 2: JSON 저장 (선택)
    save_products_json(products)
    print()
    
    # Step 3: 쇼츠 생성
    videos = create_all_shorts(products)
    
    # Step 4: 요약 생성
    generate_summary(products, videos)
    
    print()
    print("🎉 모든 작업 완료!")
    print()


if __name__ == "__main__":
    main()
