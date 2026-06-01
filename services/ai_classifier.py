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
    "casual style": "캐주얼", "business style": "비즈니스", "date look": "데이트", "street fashion": "스트릿"
}

def get_hex_color(image):
    """이미지 중앙 영역의 픽셀을 분석하여 지배적인 색상을 헥사 코드로 추출하는 함수"""
    # 분석 효율을 위해 이미지 크기 최적화 및 RGB 모드 변환 (알파 채널 에러 방지)
    small_img = image.copy().resize((100, 100)).convert('RGB')
    
    # 개선 1. 배경색 추정: 사진의 네 모서리 색상을 가져와 평균 내기
    corners = [
        small_img.getpixel((5, 5)),   # 좌상단
        small_img.getpixel((95, 5)),  # 우상단
        small_img.getpixel((5, 95)),  # 좌하단
        small_img.getpixel((95, 95))  # 우하단
    ]
    bg_r = sum(c[0] for c in corners) / 4
    bg_g = sum(c[1] for c in corners) / 4
    bg_b = sum(c[2] for c in corners) / 4

    # 개선 2. 크롭 영역 축소: 배경이 덜 섞이도록 중앙 40% 영역만 아주 타이트하게 크롭
    width, height = small_img.size
    left, top, right, bottom = width * 0.3, height * 0.3, width * 0.7, height * 0.7
    center_img = small_img.crop((left, top, right, bottom))
    
    # 대표 색상 8개로 단순화 (비슷한 색상 묶어서 정확도 향상)
    result = center_img.convert('P', palette=Image.ADAPTIVE, colors=8).convert('RGB')
    colors = result.getcolors(100 * 100)
    
    if not colors:
        return "#FFFFFF" # 예외 발생 시 기본값

    # 픽셀 개수 기준으로 내림차순 정렬
    colors.sort(key=lambda x: x[0], reverse=True)
    
    # 개선 3. 배경색 필터링: 배경색과 확연히 다른 색상을 1순위로 찾기
    most_common_color = colors[0][1] # 기본값은 가장 많이 발견된 색
    
    for count, color in colors:
        # 현재 색상과 모서리(배경) 색상의 RGB 차이를 수학적으로 계산
        dist = ((color[0] - bg_r)**2 + (color[1] - bg_g)**2 + (color[2] - bg_b)**2) ** 0.5
        
        # 색상 차이가 크면(50 이상) 배경이 아닌 '옷'으로 간주하고 즉시 채택
        if dist > 50:
            most_common_color = color
            break

    # RGB를 헥사 코드로 변환 (#000000 형태)
    return '#{:02x}{:02x}{:02x}'.format(*most_common_color).upper()

def analyze_cloth(image_path):
    """이미지 경로를 받아 DB 컬럼(main, sub, name, color, style)에 들어갈 값을 추출하는 함수"""
    try:
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
        
        # 3. 픽셀 기반 헥사 코드 직접 추출
        hex_color = get_hex_color(image)

        # [보정 로직 복구 완료] 상세 명칭 결과에 따라 상위 카테고리를 강제 교정
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
            "style": [TRANSLATE_MAP.get(style_eng, "캐주얼")], 
            "ai_tags": [main_eng, sub_eng, name_eng],  # 삭제되었던 AI 원본 태그 보관 복구
            "is_verified": False                       # 사용자 확인 전 기본값 FALSE 설정
        }
    except Exception as e:
        return {"error": str(e)}

# 서버 실행 시 이 부분이 지멋대로 실행되지 않도록 pass 처리
if __name__ == "__main__":
    pass