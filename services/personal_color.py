import os
import traceback
from PIL import Image

try:
    from services.ai_classifier import get_hex_color
except ImportError:
    from ai_classifier import get_hex_color

# ==========================================
# 1. 퍼스널 컬러 기반 추천 색상 데이터베이스
# ==========================================
RECOMMENDED_COLORS = {
    "봄 웜톤 (Spring Warm)": [
        {"name": "라이트 피치", "hex": "#FFDAB9"},
        {"name": "파스텔 옐로우", "hex": "#FFD700"},
        {"name": "애플 그린", "hex": "#8DB600"},
        {"name": "코랄 핑크", "hex": "#F88379"}
    ],
    "여름 쿨톤 (Summer Cool)": [
        {"name": "스카이 블루", "hex": "#87CEEB"},
        {"name": "라벤더", "hex": "#E6E6FA"},
        {"name": "베이비 핑크", "hex": "#F4C2C2"},
        {"name": "민트", "hex": "#98FF98"}
    ],
    "가을 웜톤 (Autumn Warm)": [
        {"name": "브릭 레드", "hex": "#CB4154"},
        {"name": "머스타드", "hex": "#FFDB58"},
        {"name": "올리브 그린", "hex": "#556B2F"},
        {"name": "카멜 브라운", "hex": "#C19A6B"}
    ],
    "겨울 쿨톤 (Winter Cool)": [
        {"name": "네이비 블루", "hex": "#000080"},
        {"name": "버건디", "hex": "#800020"},
        {"name": "퓨어 화이트", "hex": "#FFFFFF"},
        {"name": "마젠타", "hex": "#FF00FF"}
    ]
}

# ==========================================
# 2. 정확도 높은 3중 방어 정밀 추출 알고리즘 
# ==========================================
def extract_pure_skin_color(image):
    """
    [알고리즘] 배경 간섭을 최대한 차단하고, 중앙 얼굴 영역의 순수 피부 픽셀만 추출
    눈, 콧구멍, 입술, 머리카락(염색모 포함) 등을 필터링
    """
    img_full = image.copy().convert('RGB')
    w, h = img_full.size
    
    #  배경색 추정 (네 모서리 색상 평균)
    corners = [
        img_full.getpixel((int(w * 0.05), int(h * 0.05))),
        img_full.getpixel((int(w * 0.95), int(h * 0.05))),
        img_full.getpixel((int(w * 0.05), int(h * 0.95))),
        img_full.getpixel((int(w * 0.95), int(h * 0.95)))
    ]
    bg_r = sum(c[0] for c in corners) / 4
    bg_g = sum(c[1] for c in corners) / 4
    bg_b = sum(c[2] for c in corners) / 4

    #  공간 필터링: 가장자리 잘라내고 중앙 60% 영역만 남기기
    left, top = w * 0.2, h * 0.2
    right, bottom = w * 0.8, h * 0.8
    center_img = img_full.crop((left, top, right, bottom))
    
    img_rgb = center_img.resize((200, 200))
    img_ycbcr = img_rgb.convert('YCbCr')
    
    skin_pixels = []
    c_w, c_h = img_rgb.size
    
    for x in range(c_w):
        for y in range(c_h):
            r, g, b = img_rgb.getpixel((x, y))
            
            # 배경색과 유사한 픽셀 차단
            dist_from_bg = ((r - bg_r)**2 + (g - bg_g)**2 + (b - bg_b)**2) ** 0.5
            if dist_from_bg < 40:  
                continue
                
            y_val, cb_val, cr_val = img_ycbcr.getpixel((x, y))
            
            #노이즈(머리카락/눈/입술) 제거
            if y_val > 80 and (85 <= cb_val <= 120) and (135 <= cr_val <= 170):
                if r > 95 and g > 40 and b > 20 and (r > g) and (r > b):
                    if abs(r - g) > 15: 
                        skin_pixels.append((r, g, b))
                        
    if not skin_pixels:
        raise ValueError("사진에서 유효한 얼굴(피부) 영역을 분리하지 못함")
        
    avg_r = sum(p[0] for p in skin_pixels) // len(skin_pixels)
    avg_g = sum(p[1] for p in skin_pixels) // len(skin_pixels)
    avg_b = sum(p[2] for p in skin_pixels) // len(skin_pixels)
    
    return '#{:02x}{:02x}{:02x}'.format(avg_r, avg_g, avg_b).upper()