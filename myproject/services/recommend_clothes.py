<<<<<<< HEAD
import colorsys
from services.utils.weather_utils import calculate_sensory_temp

BOTTOM_TOLERANCE = 1
TOP_TOLERANCE = 1
NEUTRAL_CHROMA = 15
NEUTRAL_LIGHTNESS_LOW = 15
NEUTRAL_LIGHTNESS_HIGH = 90

# 기온에 따른 목표 두께 레벨을 반환하는 함수
def get_target_level(temp):
    if temp >= 30: return 1
    elif temp >= 25: return 2
    elif temp >= 21: return 3
    elif temp >= 17: return 4
    elif temp >= 13: return 5
    elif temp >= 9: return 6
    elif temp >= 5: return 7
    elif temp >= 0: return 8
    elif temp >= -5: return 9
    else: return 10

# 색상 헥사 코드를 HSL 포맷으로 변환하는 함수
def hex_to_hsl(hex_str):
    try:
        hex_str = hex_str.lstrip('#')
        r, g, b = tuple(int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4))
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        return h * 360, s * 100, l * 100
    except:
        return 0, 0, 0

# 유저가 선택한 TPO 스타일과의 일치도 점수를 계산하는 함수
def calculate_style_score(full_outfit, target_tpo):
    # TPO 스타일이 선택되지 않았을 때 감점 없이 만점을 부여하는 조건문
    if not target_tpo:
        return 30
    
    score = 0
    # 의류 조합 내 아이템들을 순회하며 TPO 태그 일치 여부를 검사하는 반복문
    for cloth in full_outfit:
        if target_tpo in cloth.get('style', []):
            score += 10
    return score

# 상하의 색상 조화 점수를 계산하는 함수
def calculate_color_score(top_combo, bottom, target_lv):
    top_hex = top_combo[-1]['color'] 
    bottom_hex = bottom['color']
    h1, s1, l1 = hex_to_hsl(top_hex)
    h2, s2, l2 = hex_to_hsl(bottom_hex)

    score = 0
    is_top_neutral = s1 < NEUTRAL_CHROMA or l1 < NEUTRAL_LIGHTNESS_LOW or l1 > NEUTRAL_LIGHTNESS_HIGH
    is_bottom_neutral = s2 < NEUTRAL_CHROMA or l2 < NEUTRAL_LIGHTNESS_LOW or l2 > NEUTRAL_LIGHTNESS_HIGH

    hue_diff = abs(h1 - h2)
    if hue_diff > 180: hue_diff = 360 - hue_diff
    chroma_diff = abs(s1 - s2)
    light_diff = abs(l1 - l2)

    # 상하의 중 하나라도 무채색 계열일 때 기본 조화 점수를 부여하는 조건문
    if is_top_neutral or is_bottom_neutral:
        score += 20

    # 상하의가 모두 유채색 계열일 때 세부 배색 매칭 규칙을 타는 조건문
    if not is_top_neutral and not is_bottom_neutral:
        if hue_diff < 30:
            score += 20 if light_diff > 20 else 6
        elif hue_diff >= 30:
            if chroma_diff < 15 and light_diff < 15:
                score += 15
            elif hue_diff > 150:
                score -= 10

    # 기온 레벨 및 계절 톤에 맞춰 가산점을 판별하는 조건문
    if target_lv <= 3 and (l1 >= 70 or l2 >= 60): score += 10
    elif target_lv >= 7 and (l1 <= 30 or l2 <= 40): score += 10

    return score

# 체감 기온 레벨과 의류 두께 레벨의 오차별 적합도 점수를 계산하는 함수
def calculate_temperature_score(top_combo, bottom, target_lv):
    top_lv_sum = sum([c['temp_level'] for c in top_combo])
    
    top_diff = abs(top_lv_sum - target_lv)
    bottom_diff = abs(bottom['temp_level'] - target_lv)
    
    total_diff = top_diff + bottom_diff
    score = max(0, 20 - (total_diff * 10))
    
    return score

# 사용자 신체 실루엣과 의류 핏 간의 조화도 점수를 계산하는 함수
def calculate_fit_score(top_combo, bottom, user_body_shape):
    top_fit = top_combo[-1].get('fit', '레귤러').strip()
    bottom_fit = bottom.get('fit', '레귤러').strip()
    
    fit_map = {
        '슬림': 1,
        '레귤러': 2,
        '오버': 3
    }
    
    top_lv = fit_map.get(top_fit, 2) 
    bottom_lv = fit_map.get(bottom_fit, 2)
    
    silhouette_score = 10
    
    if len(top_combo) == 2:
        inner_fit_str = top_combo[0].get('fit', '레귤러').strip()
        inner_lv = fit_map.get(inner_fit_str, 2)
        if inner_lv > top_lv:
            silhouette_score -= 4

    fit_diff = abs(top_lv - bottom_lv)
    
    if fit_diff == 2:
        silhouette_score -= 5
        
    silhouette_score = max(0, silhouette_score)

    # 신체 체형 프로필 정보가 존재하지 않을 때 계산을 생략하고 패스하는 조건문
    if not user_body_shape:
        return silhouette_score + 10
        
    body_shape = user_body_shape.strip()
    body_score = 10
    
    # 유저의 세부 체형 유형별 기피 조건에 걸리는지 검사하는 조건문
    if '역삼각형' in body_shape:
        if top_lv == 3:
            body_score = 7
    elif '삼각형' in body_shape:
        if bottom_lv == 1:
            body_score = 5
    elif '직사각형' in body_shape:
        if top_lv == 1 or bottom_lv == 1:
            body_score = 5
            
    return silhouette_score + body_score
    
# 날씨, TPO, 체형 데이터를 총망라하여 최종 코디 룩을 추천하는 메인 연산 함수
def recommend_clothes_logic(current_temp, humidity, wind_speed, target_tpo, user_body_shape, clothes_db, weights=None):
    sensory_temp = calculate_sensory_temp(current_temp, humidity, wind_speed)
    target_lv = get_target_level(sensory_temp)

    valid_bottoms = [c for c in clothes_db if c.get('main_category') == '하의' 
                     and abs(c['temp_level'] - target_lv) <= BOTTOM_TOLERANCE]
    
    inners = [c for c in clothes_db if c.get('main_category') == '상의' and c.get('sub_category') == '이너']
    outers = [c for c in clothes_db if c.get('main_category') == '상의' and c.get('sub_category') == '아우터']
    
    valid_top_combos = []
    # 옷장 내 이너 의류들을 순회하며 단품 및 아우터 레이어드 상의 후보를 필터링하는 반복문
    for inner in inners:
        if abs(inner['temp_level'] - target_lv) <= TOP_TOLERANCE:
            valid_top_combos.append([inner])
        for outer in outers:
            if abs((inner['temp_level'] + outer['temp_level']) - target_lv) <= TOP_TOLERANCE:
                valid_top_combos.append([inner, outer])

    outfits = []
    # 필터링된 모든 상하의 유효 조합들을 매칭하여 4대 평가 점수를 계산하는 반복문
    for top_combo in valid_top_combos:
        for bottom in valid_bottoms:
            full_outfit = top_combo + [bottom]
            
            style_score = calculate_style_score(full_outfit, target_tpo)
            color_score = calculate_color_score(top_combo, bottom, target_lv)
            temp_score = calculate_temperature_score(top_combo, bottom, target_lv)
            fit_score = calculate_fit_score(top_combo, bottom, user_body_shape)
            
            if not weights:
                weights = {"style": 1.0, "color": 1.0, "temp": 1.0, "fit": 1.0}
            
            fashion_score = (
                (style_score * weights.get("style", 1.0)) +
                (color_score * weights.get("color", 1.0)) +
                (temp_score * weights.get("temp", 1.0)) +
                (fit_score * weights.get("fit", 1.0))
            )
            total_wear_count = sum([c.get('monthly_wear_count', 0) for c in full_outfit])
            
            outfits.append({
                "top_combo": top_combo,
                "bottom": bottom,
                "fashion_score": fashion_score,
                "total_wear_count": total_wear_count,
                "style_score": style_score,
                "color_score": color_score,
                "temp_score": temp_score,
                "fit_score": fit_score,
                "total_lv": sum([c['temp_level'] for c in top_combo])
            })

    # 연산 결과 만들어진 조화 코디 조합이 한 개도 없을 때 빈 결과를 반환하는 조건문
    if not outfits:
        return []

    outfits_sorted_by_fashion = sorted(outfits, key=lambda x: x['fashion_score'], reverse=True)
    highest_score = outfits_sorted_by_fashion[0]['fashion_score']

    SCORE_TOLERANCE = 10
    
    top_tier_bucket = [
        outfit for outfit in outfits_sorted_by_fashion 
        if (highest_score - outfit['fashion_score']) <= SCORE_TOLERANCE
    ]

    final_recommendations = sorted(top_tier_bucket, key=lambda x: x['total_wear_count'])[:5]

    # 우수 점수대 코디 세트가 5벌 미만인 경우 나머지 차선책 조합으로 채우는 조건문
    if len(final_recommendations) < 5:
        remaining = [o for o in outfits_sorted_by_fashion if o not in top_tier_bucket]
        final_recommendations.extend(remaining[:5 - len(final_recommendations)])

    if final_recommendations:
        max_style_score = max([o['style_score'] for o in final_recommendations])
    else:
        max_style_score = 0

    tpo_fallback_triggered = bool(target_tpo and max_style_score == 0)

    return {
        "recommendations": final_recommendations,
        "is_tpo_fallback": tpo_fallback_triggered,
    }
=======
import colorsys

# 설정값
BOTTOM_TOLERANCE = 1
NEUTRAL_CHROMA = 15
NEUTRAL_LIGHTNESS_LOW = 15
NEUTRAL_LIGHTNESS_HIGH = 90

def get_target_level(temp):
    """온도별 목표 레벨 반환"""
    if temp >= 30: return 1
    elif temp >= 25: return 2
    elif temp >= 21: return 3
    elif temp >= 17: return 4
    elif temp >= 13: return 5
    elif temp >= 9: return 6
    elif temp >= 5: return 7
    elif temp >= 0: return 8
    elif temp >= -5: return 9
    else: return 10

def hex_to_hsl(hex_str):
    """헥사 코드를 HSL로 변환"""
    try:
        hex_str = hex_str.lstrip('#')
        r, g, b = tuple(int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4))
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        return h * 360, s * 100, l * 100
    except:
        return 0, 0, 0

def calculate_style_score(full_outfit, target_tpo):
    """TPO 일치도 점수 계산"""
    score = 0
    for cloth in full_outfit:
        # DB의 'style' 컬럼(배열)에 사용자가 선택한 TPO가 있는지 확인
        if target_tpo in cloth.get('style', []):
            score += 1
    return score

def calculate_color_score(top_combo, bottom, target_lv):
    """색상 조화 점수 계산 (톤온톤, 톤앤톤)"""
    top_hex = top_combo[-1]['color'] 
    bottom_hex = bottom['color']
    h1, s1, l1 = hex_to_hsl(top_hex)
    h2, s2, l2 = hex_to_hsl(bottom_hex)

    score = 0
    is_top_neutral = s1 < NEUTRAL_CHROMA or l1 < NEUTRAL_LIGHTNESS_LOW or l1 > NEUTRAL_LIGHTNESS_HIGH
    is_bottom_neutral = s2 < NEUTRAL_CHROMA or l2 < NEUTRAL_LIGHTNESS_LOW or l2 > NEUTRAL_LIGHTNESS_HIGH

    hue_diff = abs(h1 - h2)
    if hue_diff > 180: hue_diff = 360 - hue_diff
    chroma_diff = abs(s1 - s2)
    light_diff = abs(l1 - l2)

    if is_top_neutral or is_bottom_neutral:
        score += 1.5

    if not is_top_neutral and not is_bottom_neutral:
        if hue_diff < 30:
            score += 1.5 if light_diff > 20 else 0.5
        elif hue_diff >= 30:
            if chroma_diff < 15 and light_diff < 15:
                score += 1.2
            elif hue_diff > 150:
                score -= 1.0

    # 계절별 가산점
    if target_lv <= 3 and (l1 >= 70 or l2 >= 60): score += 0.8
    elif target_lv >= 7 and (l1 <= 30 or l2 <= 40): score += 0.8

    return round(score, 2)

def recommend_clothes_logic(current_temp, target_tpo, clothes_db):
    """웹 서버용 추천 메인 로직 (JSON 반환용)"""
    target_lv = get_target_level(current_temp)

    # 1. 하의 필터링
    valid_bottoms = [c for c in clothes_db if c.get('main_category') == '하의' 
                    and abs(c['temp_level'] - target_lv) <= BOTTOM_TOLERANCE]
    
    # 2. 상의(이너/아우터) 필터링
    inners = [c for c in clothes_db if c.get('main_category') == '상의' and c.get('sub_category') == '이너']
    outers = [c for c in clothes_db if c.get('main_category') == '상의' and c.get('sub_category') == '아우터']
    
    valid_top_combos = []
    for inner in inners:
        if inner['temp_level'] == target_lv:
            valid_top_combos.append([inner])
        for outer in outers:
            if inner['temp_level'] + outer['temp_level'] == target_lv:
                valid_top_combos.append([inner, outer])

    # 3. 조합 및 점수 계산
    outfits = []
    for top_combo in valid_top_combos:
        for bottom in valid_bottoms:
            full_outfit = top_combo + [bottom]
            style_score = calculate_style_score(full_outfit, target_tpo)
            color_score = calculate_color_score(top_combo, bottom, target_lv)
            
            outfits.append({
                "top_combo": top_combo,
                "bottom": bottom,
                "total_score": round(style_score + color_score, 2),
                "style_score": style_score,
                "color_score": color_score,
                "total_lv": sum([c['temp_level'] for c in top_combo])
            })

    # 4. 정렬 후 상위 5개 반환
    return sorted(outfits, key=lambda x: x['total_score'], reverse=True)[:5]
>>>>>>> 1889af6a120fbb7084e7aa1bef728b06d9894457
