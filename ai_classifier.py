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