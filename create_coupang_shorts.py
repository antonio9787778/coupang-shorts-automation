# create_coupang_shorts.py - 쿠팡 제품 쇼츠 생성 (이미지 포함)
from moviepy.editor import *
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import requests
import os
import tempfile

def download_product_image(image_url):
    """제품 이미지 다운로드"""
    try:
        if not image_url:
            return None
        
        # HTTPS 강제
        if image_url.startswith('//'):
            image_url = 'https:' + image_url
        elif image_url.startswith('http://'):
            image_url = image_url.replace('http://', 'https://')
        
        print(f"   📥 이미지 다운로드 중: {image_url[:60]}...")
        
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_file.write(response.content)
            temp_file.close()
            print(f"   ✅ 이미지 다운로드 완료")
            return temp_file.name
        
        print(f"   ⚠️ 이미지 다운로드 실패 (HTTP {response.status_code})")
        return None
    except Exception as e:
        print(f"   ⚠️ 이미지 다운로드 오류: {e}")
        return None

def create_shorts(product):
    """
    쿠팡 제품 데이터로 YouTube 쇼츠 생성 (제품 이미지 포함)
    """
    try:
        keyword = product.get('keyword', 'product')
        name = product.get('name', '쿠팡 추천 제품')
        price = product.get('price', 0)
        url = product.get('url', '')
        category = product.get('category', '')
        rocket = product.get('rocket', False)
        image_url = product.get('image_url', '')
        
        print(f"🎬 '{keyword}' 쇼츠 생성 중...")
        print(f"   제품: {name[:40]}...")
        print(f"   가격: ₩{price:,}")
        
        # 1. 음성 생성 (TTS)
        script = f"{name}. 가격은 {price:,}원입니다."
        if rocket:
            script += " 로켓배송 가능합니다."
        
        print(f"   🎤 음성 생성 중...")
        tts = gTTS(text=script, lang='ko')
        audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts.save(audio_file.name)
        
        audio_clip = AudioFileClip(audio_file.name)
        duration = audio_clip.duration
        print(f"   ✅ 음성 생성 완료 ({duration:.1f}초)")
        
        # 2. 제품 이미지 다운로드
        product_img_path = download_product_image(image_url)
        
        # 3. 배경 이미지 생성 (1080x1920 세로)
        print(f"   🎨 배경 이미지 생성 중...")
        img = Image.new('RGB', (1080, 1920), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # 폰트 로드
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 70)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 50)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 40)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # 4. 제품 이미지 삽입 (상단)
        y_position = 150
        
        if product_img_path and os.path.exists(product_img_path):
            try:
                product_img = Image.open(product_img_path)
                
                # 정사각형으로 크롭 (중앙)
                width, height = product_img.size
                min_dim = min(width, height)
                left = (width - min_dim) // 2
                top = (height - min_dim) // 2
                product_img = product_img.crop((left, top, left + min_dim, top + min_dim))
                
                # 리사이즈 (800x800)
                product_img = product_img.resize((800, 800), Image.Resampling.LANCZOS)
                
                # 배경에 붙여넣기 (중앙 정렬)
                img.paste(product_img, (140, y_position))
                
                y_position += 870  # 이미지 아래로 이동
                
                print(f"   ✅ 제품 이미지 추가 완료")
            except Exception as e:
                print(f"   ⚠️ 이미지 처리 실패: {e}")
                y_position = 400
        else:
            print(f"   ⚠️ 제품 이미지 없음 (텍스트만 사용)")
            y_position = 400
        
        # 5. 제목 (여러 줄 처리)
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
        
        # 최대 2줄만
        for line in lines[:2]:
            bbox = draw.textbbox((0, 0), line, font=font_medium)
            text_width = bbox[2] - bbox[0]
            x = (1080 - text_width) // 2
            draw.text((x, y_position), line, fill=(50, 50, 50), font=font_medium)
            y_position += 70
        
        # 6. 가격 (빨간색, 크게)
        y_position += 30
        price_text = f"₩{price:,}원"
        bbox = draw.textbbox((0, 0), price_text, font=font_large)
        text_width = bbox[2] - bbox[0]
        draw.text(((1080 - text_width) // 2, y_position), price_text, fill=(255, 50, 50), font=font_large)
        
        # 7. 로켓배송
        y_position += 100
        if rocket:
            rocket_text = "🚀 로켓배송 가능"
            bbox = draw.textbbox((0, 0), rocket_text, font=font_small)
            text_width = bbox[2] - bbox[0]
            draw.text(((1080 - text_width) // 2, y_position), rocket_text, fill=(0, 100, 255), font=font_small)
        
        # 8. 하단 정보
        link_text = "🔗 링크는 댓글 확인!"
        bbox = draw.textbbox((0, 0), link_text, font=font_small)
        text_width = bbox[2] - bbox[0]
        draw.text(((1080 - text_width) // 2, 1800), link_text, fill=(100, 100, 100), font=font_small)
        
        # 9. 이미지 저장
        img_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        img.save(img_file.name)
        
        # 10. 비디오 생성
        print(f"   🎬 비디오 생성 중...")
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
        if product_img_path and os.path.exists(product_img_path):
            os.unlink(product_img_path)
        
        print(f"✅ 쇼츠 생성 완료: {video_file}")
        
        return video_file
    
    except Exception as e:
        print(f"❌ 쇼츠 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None
