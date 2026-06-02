from transformers import pipeline
from PIL import Image
import collections

# 1. AI 모델 초기화: 서버가 켜질 때 딱 한 번만 로드되도록 함 (서버 속도 최적화)
print(" 패션 분석 AI 엔진 시동 중 (정확도 강화 버전 3-네 모서리 픽셀 분석)")
detector = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")

# AI가 분석한 영어 결과를 DB 테이블 규격에 맞는 한글 데이터로 치환함
TRANSLATE_MAP = {
    "top": "상의", "bottom": "하의",
    "outerwear": "아우터", "innerwear": "이너", "pants": "바지",
    "hooded sweatshirt": "후드티", "heavy coat": "코트", 
    "knit cardigan": "가디건", "cotton t-shirt": "티셔츠", 
    "denim jeans": "청바지", "suit slacks": "슬랙스",
    "short-sleeved shirt": "반팔셔츠",
    "long-sleeved shirt": "긴팔셔츠",
    "sweatpants": "추리닝",

    # 7대 스타일 반영
    "casual style": "캐주얼", 
    "date look": "데이트", 
    "formal style": "포멀", 
    "street fashion": "스트릿",
    "military look": "밀리터리룩",
    "athleisure look": "애슬레저",
    "gorpcore look": "고프코어"
}

def get_hex_color(image):
    """이미지 중앙 영역의 픽셀을 분석하여 지배적인 색상을 헥사 코드로 추출하는 함수"""
    small_img = image.copy().resize((100, 100)).convert('RGB')
    
    corners = [
        small_img.getpixel((5, 5)),   # 좌상단
        small_img.getpixel((95, 5)),  # 우상단
        small_img.getpixel((5, 95)),  # 좌하단
        small_img.getpixel((95, 95))  # 우하단
    ]
    bg_r = sum(c[0] for c in corners) / 4
    bg_g = sum(c[1] for c in corners) / 4
    bg_b = sum(c[2] for c in corners) / 4

    width, height = small_img.size
    left, top, right, bottom = width * 0.3, height * 0.3, width * 0.7, height * 0.7
    center_img = small_img.crop((left, top, right, bottom))
    
    result = center_img.convert('P', palette=Image.ADAPTIVE, colors=8).convert('RGB')
    colors = result.getcolors(100 * 100)
    
    if not colors:
        return "#FFFFFF"

    colors.sort(key=lambda x: x[0], reverse=True)
    
    most_common_color = colors[0][1]
    
    for count, color in colors:
        dist = ((color[0] - bg_r)**2 + (color[1] - bg_g)**2 + (color[2] - bg_b)**2) ** 0.5
        if dist > 50:
            most_common_color = color
            break

    return '#{:02x}{:02x}{:02x}'.format(*most_common_color).upper()

def analyze_cloth(image_path):
    """이미지 경로를 받아 DB 컬럼(main, sub, name, color, style)에 들어갈 값을 추출하는 함수"""
    try:
        image = Image.open(image_path)
        
        def query(labels):
            prompts = [f"a professional photo of a {l}" for l in labels]
            res = detector(image, candidate_labels=prompts)
            return res[0]['label'].replace("a professional photo of a ", "")

        # 1. 상세 명칭 및 카테고리 분석 (새로운 옷 종류 라벨 후보 추가)
        name_eng = query([
            "hooded sweatshirt", "heavy coat", "knit cardigan", "cotton t-shirt", 
            "denim jeans", "suit slacks", "short-sleeved shirt", "long-sleeved shirt", "sweatpants"
        ])
        
        # 2. 카테고리 분석: 대분류(main)와 중분류(sub) 판별
        main_eng = query(["top", "bottom"])
        sub_eng = query(["outerwear", "innerwear", "pants"])
        
        style_eng = query([
            "casual style", "date look", "formal style", "street fashion", 
            "military look", "athleisure look", "gorpcore look"
        ])
        
        # 3. 픽셀 기반 헥사 코드 직접 추출
        hex_color = get_hex_color(image)

        # [보정 로직 수정] 상세 명칭 결과에 따라 상위 카테고리를 강제 교정
        if name_eng == "hooded sweatshirt":
            main_eng, sub_eng = "top", "innerwear"
            
        # 셔츠(반팔/긴팔)를 상의(top) 및 아우터(outerwear)로 강제 고정
        elif name_eng in ["heavy coat", "knit cardigan", "short-sleeved shirt", "long-sleeved shirt"]:
            main_eng, sub_eng = "top", "outerwear"
            
        # 추리닝을 하의(bottom) 및 바지(pants)로 강제 고정
        elif name_eng in ["denim jeans", "suit slacks", "sweatpants"]:
            main_eng, sub_eng = "bottom", "pants"

        return {
            "main_category": TRANSLATE_MAP.get(main_eng, "상의"),
            "sub_category": TRANSLATE_MAP.get(sub_eng, "이너"),
            "name": TRANSLATE_MAP.get(name_eng, "의류"),
            "color": hex_color, 
            "style": [TRANSLATE_MAP.get(style_eng, "캐주얼")], 
            "ai_tags": [main_eng, sub_eng, name_eng],
            "is_verified": False
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    pass