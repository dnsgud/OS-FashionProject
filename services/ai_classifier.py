from transformers import pipeline
from PIL import Image

TRANSLATE_MAP = {
    "top": "상의", "bottom": "하의",
    "outerwear": "아우터", "innerwear": "이너", "pants": "바지",
    "hooded sweatshirt": "후드티", "heavy coat": "코트", 
    "knit cardigan": "가디건", "cotton t-shirt": "티셔츠", 
    "denim jeans": "청바지", "suit slacks": "슬랙스",
    "casual style": "캐주얼", "business style": "비즈니스", "date look": "데이트", "street fashion": "스트릿"
}

# [중요] 이 함수가 analyze_cloth 밖으로(맨 왼쪽으로) 나와있어야 합니다!
def get_hex_color(image):
    """이미지 중앙 영역의 픽셀을 분석하여 색상을 추출 (들여쓰기 없음!)"""
    small_img = image.copy().resize((100, 100)).convert('RGB')
    # ... (기존 색상 추출 로직들) ...
    return "#FFFFFF" # 예시 결과

def analyze_cloth(image_path):
    """사용자가 요청할 때만 모델을 로드하여 분석"""
    
    # AI 모델 로드 (요청 시에만 실행)
    detector = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")
    
    image = Image.open(image_path)
    
    def query(labels):
        prompts = [f"a professional photo of a {l}" for l in labels]
        res = detector(image, candidate_labels=prompts)
        return res[0]['label'].replace("a professional photo of a ", "")

    # 분석 로직
    name_eng = query(["hooded sweatshirt", "heavy coat", "knit cardigan", "cotton t-shirt", "denim jeans", "suit slacks"])
    main_eng = query(["top", "bottom"])
    sub_eng = query(["outerwear", "innerwear", "pants"])
    style_eng = query(["casual style", "business style", "date look", "street fashion"])
    
    # 밖으로 꺼낸 get_hex_color 함수를 여기서 호출해서 사용함
    hex_color = get_hex_color(image)

    return {
        "main_category": TRANSLATE_MAP.get(main_eng, "상의"),
        "sub_category": TRANSLATE_MAP.get(sub_eng, "이너"),
        "name": TRANSLATE_MAP.get(name_eng, "의류"),
        "color": hex_color,
        "style": [TRANSLATE_MAP.get(style_eng, "캐주얼")],
        "is_verified": False
    }