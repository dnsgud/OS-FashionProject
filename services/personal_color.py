import os
import traceback
from PIL import Image

try:
    from services.ai_classifier import get_hex_color
except ImportError:
    from ai_classifier import get_hex_color

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