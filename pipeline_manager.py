# pipeline_manager.py - 쿠팡 검색 → 쇼츠 생성 통합

import os
import re
import json
from datetime import datetime
from create_coupang_shorts import create_shorts

def parse_result_txt(result_file='result.txt'):
    """result.txt 파싱하여 제품 데이터 추출"""
    print("=" * 70)
    print("📄 result.txt 파싱 시작")
    print("=" * 70)
    print()
    
    if not os.path.exists(result_file):
        print(f"❌ {result_file} 파일이 없습니다.")
        return []
    
    with open(result_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 검색 실패 확인
    if '❌ 인증 실패' in content or '⚠️ 예상 고수수료 제품을 찾지 못했습니다' in content:
        print("⚠️ 쿠팡 API 검색 실패 감지")
        print("🔄 더미 데이터로 대체합니다...\n")
        return get_dummy_products()
    
    products = []
    keyword_sections = re.split(r'={70}\n📌 키워드: ', content)
    
    for section in keyword_sections[1:]:
        try:
            keyword_match = re.match(r'(.+?)\s+\((\d+)/(\d+)\)', section)
            if not keyword_match:
                continue
            
            keyword = keyword_match.group(1).strip()
            
            if '⚠️ 검색 실패' in section or '⚠️ 제품 없음' in section:
                print(f"⚠️ {keyword}: 검색 실패")
                continue
            
            name_match = re.search(r'1\.\s+(.+?)(?:🚀)?\s*\n', section)
            if not name_match:
                continue
            
            name = name_match.group(1).strip()
            
            price_match = re.search(r'💰 가격:\s+([\d,]+)원', section)
            price = int(price_match.group(1).replace(',', '')) if price_match else 0
            
            category_match = re.search(r'📂 카테고리:\s+(.+)', section)
            category = category_match.group(1).strip() if category_match else ''
            
            rate_match = re.search(r'📊 예상 수수료율:\s+([\d.]+)%', section)
            rate = float(rate_match.group(1)) if rate_match else 5.0
            
            commission_match = re.search(r'💵 예상 수수료:\s+([\d,]+)원', section)
            commission = int(commission_match.group(1).replace(',', '')) if commission_match else 0
            
            # ⭐ 파트너스 링크 추출
            url_match = re.search(r'🔗 파트너스 링크:\s+(.+?)\.\.\.', section)
            url = url_match.group(1).strip() if url_match else ''
            
            rocket = '🚀' in section
            
            product = {
                'keyword': keyword,
                'name': name,
                'price': price,
                'category': category,
                'rate': rate,
                'commission': commission,
                'rocket': rocket,
                'url': url,  # ⭐ 파트너스 링크
                'image_url': '',
                'review_count': 0,
                'rating': 4.5
            }
            
            products.append(product)
            print(f"✅ {keyword}: {name[:40]}... (₩{price:,})")
        
        except Exception as e:
            print(f"⚠️ 섹션 파싱 중 오류: {e}")
            continue
    
    if not products:
        print("⚠️ 파싱된 제품이 없습니다.")
        print("🔄 더미 데이터로 대체합니다...\n")
        return get_dummy_products()
    
    print()
    print(f"📊 총 {len(products)}개 제품 파싱 완료")
    print("=" * 70)
    print()
    
    return products

def get_dummy_products():
    """더미 제품 데이터"""
    return [
        {
            'keyword': '여성의류',
            'name': '제니트 여성 군살 쏙 루즈핏 반오픈 하이넥 니트',
            'price': 19900,
            'category': '패션의류',
            'rate': 6.8,
            'commission': 1353,
            'rocket': True,
            'url': 'https://link.coupang.com/a/bXXXXX',
            'image_url': '',
            'review_count': 1234,
            'rating': 4.8
        },
        {
            'keyword': '화장품세트',
            'name': 'SK-II 피테라 풀라인 스킨케어 세트',
            'price': 98600,
            'category': '뷰티',
            'rate': 5.3,
            'commission': 5225,
            'rocket': True,
            'url': 'https://link.coupang.com/a/bYYYYY',
            'image_url': '',
            'review_count': 856,
            'rating': 4.9
        },
        {
            'keyword': '건강식품',
            'name': '황제기력 침향 고함량 28% 침향환 골드',
            'price': 99900,
            'category': '식품',
            'rate': 5.3,
            'commission': 5294,
            'rocket': False,
            'url': 'https://link.coupang.com/a/bZZZZZ',
            'image_url': '',
            'review_count': 423,
            'rating': 4.5
        }
    ]

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
                file_size = os.path.getsize(video_file)
                created_videos.append({
                    'keyword': product['keyword'],
                    'video_file': video_file,
                    'file_size': file_size,
                    'product': product
                })
                print(f"✅ 생성 완료: {video_file} ({file_size/1024/1024:.1f} MB)")
            else:
                print(f"❌ 생성 실패: {product['keyword']}")
        
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        
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
        total_size = 0
        for video in videos:
            size_mb = video['file_size'] / 1024 / 1024
            total_size += video['file_size']
            print(f"  ✅ {video['video_file']} ({size_mb:.1f} MB)")
            print(f"     제품: {video['product']['name'][:40]}...")
            print(f"     가격: ₩{video['product']['price']:,}")
            print(f"     파트너스 링크: {video['product']['url'][:50]}...")  # ⭐ 링크 표시
            print()
        
        print(f"📦 총 용량: {total_size/1024/1024:.1f} MB")
        print()
    
    # summary.txt 저장
    with open('summary.txt', 'w', encoding='utf-8') as f:
        f.write(f"쿠팡 쇼츠 자동 생성 요약\n")
        f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"\n")
        f.write(f"검색된 제품: {len(products)}개\n")
        f.write(f"생성된 쇼츠: {len(videos)}개\n")
        f.write(f"\n")
        if videos:
            f.write(f"생성된 파일:\n")
            for video in videos:
                f.write(f"  - {video['video_file']}\n")
                f.write(f"    링크: {video['product']['url']}\n")
        else:
            f.write(f"생성된 파일: 없음\n")
    
    print("💾 요약 저장: summary.txt")
    print("=" * 70)

def main():
    """전체 파이프라인 실행"""
    print()
    print("=" * 70)
    print("🚀 쿠팡 쇼츠 자동 생성 파이프라인")
    print("=" * 70)
    print()
    
    try:
        products = parse_result_txt('result.txt')
        
        if not products:
            print("❌ 제품 데이터를 가져올 수 없습니다.")
            return
        
        save_products_json(products)
        print()
        
        videos = create_all_shorts(products)
        
        generate_summary(products, videos)
        
        print()
        print("🎉 모든 작업 완료!")
        print()
        
        if videos:
            exit(0)
        else:
            print("⚠️ 생성된 쇼츠가 없습니다.")
            exit(1)
    
    except Exception as e:
        print(f"❌ 치명적 오류: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()
