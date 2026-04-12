from transformers import pipeline
from PIL import Image

# 1. AI 모델 초기화: 이미지와 텍스트의 유사도를 계산하는 CLIP 모델 로드
print(" 패션 분석 AI 엔진 시동 중 (정확도 강화 버전1)...")
detector = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")

# AI가 분석한 영어 결과를 DB 테이블 규격에 맞는 한글 데이터로 치환함
TRANSLATE_MAP = {
    # main_category: 상의, 하의 등 대분류
    "top": "상의", "bottom": "하의",
    
    # sub_category: 아우터, 이너, 바지 등 중분류
    "outerwear": "아우터", "innerwear": "이너", "pants": "바지",
    
    # name: DB의 'name' 컬럼에 들어갈 구체적인 옷 종류
    # AI 인식률을 높이기 위해 구체적인 단어(hooded sweatshirt 등)를 매핑함
    "hooded sweatshirt": "후드티", 
    "heavy coat": "코트", 
    "knit cardigan": "가디건", 
    "cotton t-shirt": "티셔츠", 
    "denim jeans": "청바지", 
    "suit slacks": "슬랙스",
    
    # style: DB의 text[] 배열에 들어갈 스타일 명칭
    "casual style": "캐주얼", 
    "business style": "비즈니스", 
    "date look": "데이트", 
    "street fashion": "스트릿",
    
    # color: 한글 단어로 매핑
    "black": "검정", "white": "흰색", "brown": "갈색", "sky blue": "하늘색", "gray": "회색"
}

def analyze_cloth(image_path):
    
    #이미지 경로를 받아 DB 컬럼(main, sub, name, color, style)에 들어갈 값을 추출하는 함수
    
    # 이미지 파일을 열어 AI가 읽을 수 있는 객체로 변환
    image = Image.open(image_path)
    
    # 정확도 향상위해 AI에게 구체적인 문맥을 제공하기 위한 프롬프트 헬퍼 함수
    def query(labels):
        prompts = [f"a professional photo of a {l}" for l in labels]
        res = detector(image, candidate_labels=prompts)
        return res[0]['label'].replace("a professional photo of a ", "")

    # 1. 상세 명칭(name) 분석: 가장 구체적인 단어로 먼저 분석하여 정확도 확보
    # 후드티를 'hooded sweatshirt'로 물어보아 코트(coat)와의 혼동을 줄임
    name_eng = query(["hooded sweatshirt", "heavy coat", "knit cardigan", "cotton t-shirt", "denim jeans", "suit slacks"])
    
    # 2. 카테고리 분석: 대분류(main)와 중분류(sub) 판별
    main_eng = query(["top", "bottom"])
    sub_eng = query(["outerwear", "innerwear", "pants"])
    
    # 3. 색상 및 스타일 분석
    color_eng = query(["black", "white", "brown", "sky blue", "gray"])
    style_eng = query(["casual style", "business style", "date look", "street fashion"])

    # [보정 로직] AI의 논리적 오판(후드티를 하의로 판단 등)을 강제 교정
    # 분석된 구체적 명칭(name_eng)을 기준으로 상위 카테고리를 재설정함
    if name_eng == "hooded sweatshirt":
        main_eng = "top"
        sub_eng = "innerwear" # 프로젝트 기준에 따라 'outerwear'로 변경 가능
    elif name_eng in ["heavy coat", "knit cardigan"]:
        main_eng = "top"
        sub_eng = "outerwear"
    elif name_eng in ["denim jeans", "suit slacks"]:
        main_eng = "bottom"
        sub_eng = "pants"

    # 최종 데이터 구성:Supabase 테이블 컬럼명과 1:1로 매칭
    return {
        "main_category": TRANSLATE_MAP.get(main_eng, "상의"),
        "sub_category": TRANSLATE_MAP.get(sub_eng, "이너"),
        "name": TRANSLATE_MAP.get(name_eng, "직접 찍은 테스트 옷"),
        "color": TRANSLATE_MAP.get(color_eng, color_eng),
        "style": [TRANSLATE_MAP.get(style_eng, "캐주얼")], # DB의 text[] 형식을 위해 리스트로 저장
        "ai_tags": [main_eng, sub_eng, name_eng],       # AI가 찾은 원래 영어 태그들 보관
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