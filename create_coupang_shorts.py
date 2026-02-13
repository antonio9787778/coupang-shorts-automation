# create_coupang_shorts.py - 쿠팡 제품 쇼츠 생성
from moviepy.editor import *
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import requests
import os
import tempfile

def create_shorts(product):
    """
    쿠팡 제품 데이터로 YouTube 쇼츠 생성
    
    Args:
        product: 제품 정보 딕셔너리
            - name: 제품명
            - price: 가격
            - url: 파트너스 링크
            - keyword: 검색 키워드
            - category: 카테고리
            - rocket: 로켓배송 여부
    
    Returns:
        video_file: 생성된 비디오 파일명 (shorts_키워드.mp4)
    """
    try:
        keyword = product.get('keyword', 'product')
        name = product.get('name', '쿠팡 추천 제품')
        price = product.get('price', 0)
        url = product.get('url', '')
        category = product.get('category', '')
        rocket = product.get('rocket', False)
        
        print(f"🎬 '{keyword}' 쇼츠 생성 중...")
        print(f"   제품: {name[:40]}...")
        print(f"   가격: ₩{price:,}")
        
        # 1. 음성 생성 (TTS)
        script = f"{name}. 가격은 {price:,}원입니다."
        if rocket:
            script += " 로켓배송 가능합니다."
        
        tts = gTTS(text=script, lang='ko')
        audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts.save(audio_file.name)
        
        audio_clip = AudioFileClip(audio_file.name)
        duration = audio_clip.duration
        
        # 2. 배경 이미지 생성 (1080x1920 세로)
        img = Image.new('RGB', (1080, 1920), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # 텍스트 추가
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 60)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 50)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 40)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # 제목 (여러 줄 처리)
        y_position = 300
        max_width = 950
        
        words = name.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + word + " "
            bbox = draw.textbbox((0, 0), test_line, font=font_medium)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line.strip())
                current_line = word + " "
        
        if current_line:
            lines.append(current_line.strip())
        
        # 최대 3줄만
        for line in lines[:3]:
            bbox = draw.textbbox((0, 0), line, font=font_medium)
            text_width = bbox[2] - bbox[0]
            x = (1080 - text_width) // 2
            draw.text((x, y_position), line, fill=(0, 0, 0), font=font_medium)
            y_position += 80
        
        # 가격
        price_text = f"₩{price:,}원"
        bbox = draw.textbbox((0, 0), price_text, font=font_large)
        text_width = bbox[2] - bbox[0]
        draw.text(((1080 - text_width) // 2, y_position + 50), price_text, fill=(255, 0, 0), font=font_large)
        
        # 로켓배송
        if rocket:
            rocket_text = "🚀 로켓배송"
            bbox = draw.textbbox((0, 0), rocket_text, font=font_small)
            text_width = bbox[2] - bbox[0]
            draw.text(((1080 - text_width) // 2, y_position + 150), rocket_text, fill=(0, 100, 255), font=font_small)
        
        # 카테고리
        if category:
            cat_text = f"📂 {category}"
            bbox = draw.textbbox((0, 0), cat_text, font=font_small)
            text_width = bbox[2] - bbox[0]
            draw.text(((1080 - text_width) // 2, 1700), cat_text, fill=(100, 100, 100), font=font_small)
        
        # 파트너스 링크
        link_text = "🔗 링크는 댓글 확인!"
        bbox = draw.textbbox((0, 0), link_text, font=font_small)
        text_width = bbox[2] - bbox[0]
        draw.text(((1080 - text_width) // 2, 1800), link_text, fill=(50, 50, 50), font=font_small)
        
        # 이미지 저장
        img_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        img.save(img_file.name)
        
        # 3. 비디오 생성
        img_clip = ImageClip(img_file.name).set_duration(duration)
        video = img_clip.set_audio(audio_clip)
        
        # 파일명 생성
        safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '_')).strip()
        safe_keyword = safe_keyword.replace(' ', '_')
        video_file = f"shorts_{safe_keyword}.mp4"
        
        # 비디오 저장
        video.write_videofile(
            video_file,
            fps=1,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            logger=None
        )
        
        # 임시 파일 정리
        os.unlink(audio_file.name)
        os.unlink(img_file.name)
        
        print(f"✅ 쇼츠 생성 완료: {video_file}")
        
        return video_file
    
    except Exception as e:
        print(f"❌ 쇼츠 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # 테스트
    test_product = {
        'keyword': '여성의류',
        'name': '제니트 여성 군살 쏙 루즈핏 반오픈 하이넥 니트',
        'price': 19900,
        'category': '패션의류',
        'rocket': True,
        'url': 'https://link.coupang.com/a/bXXXXX'
    }
    
    create_shorts(test_product)
