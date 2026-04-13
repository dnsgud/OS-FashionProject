from transformers import pipeline
from PIL import Image
import collections

# 1. AI 모델 초기화: 이미지 분류를 위한 CLIP 모델 로드
print(" 패션 분석 AI 엔진 시동 중 (정확도 강화 버전 2-헥사코드 추출)...")
detector = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")

# AI가 분석한 영어 결과를 DB 테이블 규격에 맞는 한글 데이터로 치환함
TRANSLATE_MAP = {
    "top": "상의", "bottom": "하의",
    "outerwear": "아우터", "innerwear": "이너", "pants": "바지",
    "hooded sweatshirt": "후드티", "heavy coat": "코트", 
    "knit cardigan": "가디건", "cotton t-shirt": "티셔츠", 
    "denim jeans": "청바지", "suit slacks": "슬랙스",
    "casual style": "캐주얼", "business style": "비즈니스", "date look": "데이트", "street fashion": "스트릿"
}

def get_hex_color(image):
    
    #이미지 중앙 영역의 픽셀을 분석하여 지배적인 색상을 헥사 코드로 추출하는 함수
    
    # 분석 효율을 위해 이미지 크기 최적화
    small_img = image.copy().resize((100, 100))
    
    # 배경 간섭을 피하기 위해 중앙 60% 영역만 크롭
    width, height = small_img.size
    left, top, right, bottom = width * 0.2, height * 0.2, width * 0.8, height * 0.8
    center_img = small_img.crop((left, top, right, bottom))
    
    # 대표 색상 16개로 단순화 및 최빈 색상 추출
    result = center_img.convert('P', palette=Image.ADAPTIVE, colors=16).convert('RGB')
    colors = result.getcolors(100 * 100)
    most_common_color = sorted(colors, key=lambda x: x[0], reverse=True)[0][1]
    
    # RGB를 헥사 코드로 변환 (#000000 형태)
    return '#{:02x}{:02x}{:02x}'.format(*most_common_color).upper()

def analyze_cloth(image_path):
    
    #이미지 경로를 받아 DB 컬럼(main, sub, name, color, style)에 들어갈 값을 추출하는 함수
    
    # 이미지 파일을 열어 AI가 읽을 수 있는 객체로 변환
    image = Image.open(image_path)
    
    # 정확도 향상위해 AI에게 구체적인 문맥을 제공하기 위한 프롬프트 헬퍼 함수
    def query(labels):
        prompts = [f"a professional photo of a {l}" for l in labels]
        res = detector(image, candidate_labels=prompts)
        return res[0]['label'].replace("a professional photo of a ", "")

    # 1. 상세 명칭 및 카테고리 분석 (정확도 향상을 위한 구체적 라벨 사용)
    name_eng = query(["hooded sweatshirt", "heavy coat", "knit cardigan", "cotton t-shirt", "denim jeans", "suit slacks"])
    
    # 2. 카테고리 분석: 대분류(main)와 중분류(sub) 판별
    main_eng = query(["top", "bottom"])
    sub_eng = query(["outerwear", "innerwear", "pants"])
    style_eng = query(["casual style", "business style", "date look", "street fashion"])
    
    # 2. 픽셀 기반 헥사 코드 직접 추출
    hex_color = get_hex_color(image)

    # [보정 로직] 상세 명칭 결과에 따라 상위 카테고리를 강제 교정
    if name_eng == "hooded sweatshirt":
        main_eng, sub_eng = "top", "innerwear"
    elif name_eng in ["heavy coat", "knit cardigan"]:
        main_eng, sub_eng = "top", "outerwear"
    elif name_eng in ["denim jeans", "suit slacks"]:
        main_eng, sub_eng = "bottom", "pants"

    # 최종 데이터 구성: Supabase 테이블 컬럼명과 1:1로 매칭
    return {
        "main_category": TRANSLATE_MAP.get(main_eng, "상의"),
        "sub_category": TRANSLATE_MAP.get(sub_eng, "이너"),
        "name": TRANSLATE_MAP.get(name_eng, "의류"),
        "color": hex_color, 
        "style": [TRANSLATE_MAP.get(style_eng, "캐주얼")], # DB text[] 대응 리스트
        "ai_tags": [main_eng, sub_eng, name_eng],       #AI가 찾은 원래 영어 태그들 보관
        "is_verified": False                            # 사용자 확인 전 기본값 FALSE 설정
    }

# 모듈 테스트 실행부
if __name__ == "__main__":
    try:
        # test2.jpg으로 실제 DB 저장 형태 테스트
        test_result = analyze_cloth("test2.jpg")
        print(f"\n DB 저장용 최종 데이터 셋:")
        for key, value in test_result.items():
            print(f"{key}: {value}")
    except Exception as e:
        print(f" 분석 에러: {e}")