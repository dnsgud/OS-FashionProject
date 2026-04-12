from transformers import pipeline
from PIL import Image

# 1. AI 모델 초기화: 이미지와 텍스트의 유사도를 계산하는 CLIP 모델 로드
print("⏳ 패션 분석 AI 엔진 시동 중...")
detector = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")

# AI가 분석한 영어 결과를 DB 테이블 규격에 맞는 한글 데이터로 치환함
TRANSLATE_MAP = {
    # main_category: 상의, 하의 등 대분류
    "top": "상의", "bottom": "하의",
    
    # sub_category: 아우터, 이너, 바지 등 중분류
    "outerwear": "아우터", "innerwear": "이너", "pants": "바지",
    
    # style: DB의 text[] 배열에 들어갈 스타일 명칭
    "casual": "캐주얼", "business": "비즈니스", "date": "데이트", "street": "스트릿",
    
    # color: 사용자의 요청에 따라 헥사코드 대신 한글 단어로 매핑
    "black": "검정", "white": "흰색", "brown": "갈색", "sky blue": "하늘색", "gray": "회색"
}

def analyze_cloth(image_path):
    
    #이미지 경로를 받아 DB 컬럼(main, sub, name, color, style)에 들어갈 값을 추출하는 함수
    
    image = Image.open(image_path)
    
    # 정확도 향상위해 AI에게 구체적인 문맥을 제공하기 위한 프롬프트 헬퍼 함수
    def query(labels):
        prompts = [f"a photo of {l}" for l in labels]
        res = detector(image, candidate_labels=prompts)
        return res[0]['label'].replace("a photo of ", "")

    # 1.카테고리 분석: 대분류(main)와 중분류(sub)를 각각 판별
    main_eng = query(["top", "bottom"])
    sub_eng = query(["outerwear", "innerwear", "pants"])
    
    # 2. 상세 명칭 분석: DB의 'name' 컬럼을 위한 구체적인 옷 종류 추출
    # 예: 코트, 가디건, 후드티, 청바지 등
    name_eng = query(["coat", "cardigan", "hoodie", "t-shirt", "jeans", "slacks"])
    
    # 3. 색상 및 스타일 분석: 색상과 분위기 파악
    color_eng = query(["black", "white", "brown", "sky blue", "gray"])
    style_eng = query(["casual", "business", "date", "street"])


    # 최종 데이터 구성:Supabase 테이블 컬럼명과 1:1로 매칭
    return {
        "main_category": TRANSLATE_MAP.get(main_eng, "상의"),
        "sub_category": TRANSLATE_MAP.get(sub_eng, "이너"),
        "name": TRANSLATE_MAP.get(name_eng, "직접 찍은 테스트 옷"), # 인식 안되면 기본값 사용(에러 대비)
        "color": TRANSLATE_MAP.get(color_eng, color_eng),
        "style": [TRANSLATE_MAP.get(style_eng, "캐주얼")], # DB의 text[] 형식을 위해 리스트로 저장
        "ai_tags": [main_eng, sub_eng, name_eng],       # AI가 찾은 원래 태그들
        "is_verified": False                            # 기본 FALSE 설정
    }

# 모듈 테스트 실행부
if __name__ == "__main__":
    try:
        # test.jpg으로 실제 DB 저장 형태 테스트
        test_result = analyze_cloth("test.jpg")
        print(f"\n DB 저장용 최종 데이터 셋:")
        for key, value in test_result.items():
            print(f"{key}: {value}")
    except Exception as e:
        print(f" 분석 에러: {e}")