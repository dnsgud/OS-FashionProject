import colorsys
from services.utils.weather_utils import calculate_sensory_temp

BOTTOM_TOLERANCE = 1
TOP_TOLERANCE = 1
SHOES_TOLERANCE = 2
NEUTRAL_CHROMA = 15
NEUTRAL_LIGHTNESS_LOW = 15
NEUTRAL_LIGHTNESS_HIGH = 90

# 기온별 목표 두께 레벨 반환 함수
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

# HEX 색상 코드를 HSL 포맷으로 변환하는 함수
def hex_to_hsl(hex_str):
    try:
        hex_str = hex_str.lstrip('#')
        r, g, b = tuple(int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4))
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        return h * 360, s * 100, l * 100
    except:
        return 0, 0, 0

# 유저가 선택한 TPO 스타일과의 일치도 점수 계산 함수
def calculate_style_score(full_outfit, target_tpo):
    # TPO 스타일이 지정되지 않은 경우 만점 처리
    if not target_tpo:
        return 30
    
    score = 0
    # 코디 조합 내 아이템들을 순회하며 스타일 태그 확인
    for cloth in full_outfit:
        if target_tpo in cloth.get('style', []):
            score += 10
    return score

# 상하의 색상 조화 점수 계산 함수
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

    # 상의나 하의 중 하나가 무채색일 경우 기본 점수 부여
    if is_top_neutral or is_bottom_neutral:
        score += 20

    # 상하의 모두 유채색일 경우 세부 배색 매칭 규칙 적용
    if not is_top_neutral and not is_bottom_neutral:
        if hue_diff < 30:
            score += 20 if light_diff > 20 else 6
        elif hue_diff >= 30:
            if chroma_diff < 15 and light_diff < 15:
                score += 15
            elif hue_diff > 150:
                score -= 10

    # 기온 레벨 및 계절별 톤에 따른 가산점 판별
    if target_lv <= 3 and (l1 >= 70 or l2 >= 60): score += 10
    elif target_lv >= 7 and (l1 <= 30 or l2 <= 40): score += 10

    return score

# 체감 기온 레벨과 의류 두께 레벨의 오차별 적합도 점수 계산 함수
def calculate_temperature_score(top_combo, bottom, target_lv):
    top_lv_sum = sum([c['temp_level'] for c in top_combo])
    
    top_diff = abs(top_lv_sum - target_lv)
    bottom_diff = abs(bottom['temp_level'] - target_lv)
    
    total_diff = top_diff + bottom_diff
    score = max(0, 20 - (total_diff * 10))
    
    return score

# 사용자 신체 체형과 의류 핏 간의 조화도 점수 계산 함수
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
    
    # 상의가 레이어드 조합일 때 내부 핏 조화도 검사
    if len(top_combo) == 2:
        inner_fit_str = top_combo[0].get('fit', '레귤러').strip()
        inner_lv = fit_map.get(inner_fit_str, 2)
        if inner_lv > top_lv:
            silhouette_score -= 4

    fit_diff = abs(top_lv - bottom_lv)
    
    if fit_diff == 2:
        silhouette_score -= 5
        
    silhouette_score = max(0, silhouette_score)

    # 체형 정보가 존재하지 않을 때 기본 점수 반환
    if not user_body_shape:
        return silhouette_score + 10
        
    body_shape = user_body_shape.strip()
    body_score = 10
    
    # 사용자 세부 체형별 기피 조건 검사
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
    
# 날씨, TPO, 체형 데이터를 총망라하여 최종 코디를 추천하는 메인 로직 함수
def recommend_clothes_logic(current_temp, humidity, wind_speed, target_tpo, user_body_shape, clothes_db, weights=None):
    sensory_temp = calculate_sensory_temp(current_temp, humidity, wind_speed)
    target_lv = get_target_level(sensory_temp)

    valid_bottoms = [c for c in clothes_db if c.get('main_category') == '하의' 
                     and abs(c['temp_level'] - target_lv) <= BOTTOM_TOLERANCE]

    valid_shoes = [c for c in clothes_db if c.get('main_category') in ['신발', 'shoes']
                   and abs(c['temp_level'] - target_lv) <= SHOES_TOLERANCE] 
    
    inners = [c for c in clothes_db if c.get('main_category') == '상의' and c.get('sub_category') == '이너']
    outers = [c for c in clothes_db if c.get('main_category') == '상의' and c.get('sub_category') == '아우터']
    
    valid_top_combos = []
    # 옷장 내 이너와 아우터를 순회하며 기온에 맞는 상의 세트 조합 구성
    for inner in inners:
        if abs(inner['temp_level'] - target_lv) <= TOP_TOLERANCE:
            valid_top_combos.append([inner])
        for outer in outers:
            if abs((inner['temp_level'] + outer['temp_level']) - target_lv) <= TOP_TOLERANCE:
                valid_top_combos.append([inner, outer])

    # 가중치 배열이 제공되지 않았을 때 균등 기본값 설정
    if not weights:
        weights = {"style": 1.0, "temp": 1.0, "color": 1.0, "fit": 1.0}
        
    total_w = float(sum(weights.values()))
    w_style = (weights.get("style", 0) / total_w) * 100
    w_temp = (weights.get("temp", 0) / total_w) * 100
    w_color = (weights.get("color", 0) / total_w) * 100
    w_fit = (weights.get("fit", 0) / total_w) * 100

    outfits = []
    # 유효 상하의 조합들을 매칭하여 100점 만점 체계의 최종 패션 점수 연산
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
