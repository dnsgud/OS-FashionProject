import colorsys
from utils.weather_utils import calculate_sensory_temp

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
    """스타일(TPO) 일치도 점수 계산 (최대 30점)"""
    if not target_tpo:
        return 30   # TPO 정보가 없으면 만점 부여
    
    score = 0
    for cloth in full_outfit:
        if target_tpo in cloth.get('style', []):
            score += 10  # 아이템당 10점 (3피스 풀착장 = 30점 만점)
    return score

def calculate_color_score(top_combo, bottom, target_lv):
    """색상 조화 점수 계산 (최대 30점)"""
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
        score += 20  # 기본 무채색 조화 베이스 (최대 20점)

    if not is_top_neutral and not is_bottom_neutral:
        if hue_diff < 30:
            score += 20 if light_diff > 20 else 6  # 유사색 조화 점수 조정
        elif hue_diff >= 30:
            if chroma_diff < 15 and light_diff < 15:
                score += 15  # 톤온톤 조화 점수 조정
            elif hue_diff > 150:
                score -= 10  # 보색 충돌 감점 조정

    # 계절별 톤 가산점 (최대 10점)
    if target_lv <= 3 and (l1 >= 70 or l2 >= 60): score += 10
    elif target_lv >= 7 and (l1 <= 30 or l2 <= 40): score += 10

    return score

def calculate_temperature_score(top_combo, bottom, target_lv):
    """온도 적합도 점수 계산 (최대 20점)"""
    top_lv_sum = sum([c['temp_level'] for c in top_combo])
    
    # 목표 레벨과의 오차 계산
    top_diff = abs(top_lv_sum - target_lv)
    bottom_diff = abs(bottom['temp_level'] - target_lv)
    
    # 총 오차 범위 1당 10점씩 감점
    total_diff = top_diff + bottom_diff
    score = max(0, 20 - (total_diff * 10))
    
    return score

def calculate_fit_score(top_combo, bottom, user_body_shape):
    """사용자 체형과 상/하의 핏 조화도 점수 계산 (최대 20점)"""
    # 기본 핏 텍스트 추출
    top_fit = top_combo[-1].get('fit', '스탠다드').strip()
    bottom_fit = bottom.get('fit', '스탠다드').strip()
    
    # 용어 기반 선형 레벨 매핑
    fit_map = {
        '슬림': 1, '슬림핏': 1,
        '스탠다드': 2, '스탠다드핏': 2,
        '세미와이드': 3, '세미와이드핏': 3,
        '와이드': 4, '와이드핏': 4,
        '오버': 5, '오버핏': 5
    }
    
    top_lv = fit_map.get(top_fit, 2)     # 맵에 없으면 기본값 스탠다드(2)로 방어
    bottom_lv = fit_map.get(bottom_fit, 2)
    
    # 1. 상/하의 핏 실루엣 조화도 (10점 만점)
    silhouette_score = 10
    
    # 상의가 레이어드(이너+아우터) 상태일 때 둘 간의 핏 충돌 검사 추가
    if len(top_combo) == 2:
        inner_fit_str = top_combo[0].get('fit', '스탠다드').strip()
        inner_lv = fit_map.get(inner_fit_str, 2)
        
        # 이너가 아우터보다 2단계 이상 품이 클 경우 물리적 충돌 감점
        if (inner_lv - top_lv) >= 2:
            silhouette_score -= 4

    # 상/하의 실루엣 오차 계산
    fit_diff = abs(top_lv - bottom_lv)
    if fit_diff >= 3:
        silhouette_score -= 7   # 극단적 미스매치 감점
    elif fit_diff == 2:
        silhouette_score -= 3   # 약간의 언밸런스 감점
        
    # 하한선 방어 (마이너스 점수 방지)
    silhouette_score = max(0, silhouette_score)

    # 2. 사용자 체형별 핏 적합도 (10점 만점)
    if not user_body_shape:
        return silhouette_score + 10  # 체형 정보가 선택 안 된 유저는 계산하지 않음
        
    body_shape = user_body_shape.strip()
    body_score = 10  # 기본 만점 부여 후 기피 조건 체크
    
    # [근육질 / 역삼각형 체형]
    if '근육' in body_shape or '역삼각형' in body_shape:
        if top_lv == 5:
            body_score = 7  # 너무 벙벙한 오버핏 상의는 다부진 체형 장점을 과도하게 가림
            
    # [마른 / 왜소한 체형]
    elif '마름' in body_shape or '슬림' in body_shape or '왜소' in body_shape:
        if top_fit in ['슬림', '슬림핏'] or bottom_lv in [4, 5]:
            body_score = 4  # 마른 뼈대를 부각하는 슬림핏 상의나, 몸이 왜소해 보일 수 있는 와이드/오버 하의 기피
            
    # [통통한 / 체격이 큰 체형]
    elif '통통' in body_shape or '큰' in body_shape:
        if top_lv == 1 or bottom_lv == 1:
            body_score = 3  # 신체 라인이 너무 직관적으로 드러나 부적합한 슬림 핏 라인 감점
            
    return silhouette_score + body_score
    
def recommend_clothes_logic(current_temp, humidity, wind_speed, target_tpo, user_body_shape, clothes_db, weights=None):
    """웹 서버용 추천 메인 로직 (체형 및 핏 반영 100점 만점 버전)"""
    sensory_temp = calculate_sensory_temp(current_temp, humidity, wind_speed)
    target_lv = get_target_level(sensory_temp)

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

    # 3. 조합 및 4가지 점수 계산
    outfits = []
    for top_combo in valid_top_combos:
        for bottom in valid_bottoms:
            full_outfit = top_combo + [bottom]
            
            style_score = calculate_style_score(full_outfit, target_tpo)
            color_score = calculate_color_score(top_combo, bottom, target_lv)
            temp_score = calculate_temperature_score(top_combo, bottom, target_lv)
            fit_score = calculate_fit_score(top_combo, bottom, user_body_shape)
            
            # 만약 가중치 설정값이 안 넘어왔을 경우 기본 가중치(1.0배) 세팅
            if not weights:
                weights = {"style": 1.0, "color": 1.0, "temp": 1.0, "fit": 1.0}
            
            # 최종 패션 점수 계산 시 각 요소에 유저 커스텀 가중치 배율을 곱함.
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

    if not outfits:
        return []

    # 4. 구간제 필터링 및 최종 정렬
    outfits_sorted_by_fashion = sorted(outfits, key=lambda x: x['fashion_score'], reverse=True)
    highest_score = outfits_sorted_by_fashion[0]['fashion_score']

    # 오차 범위 (10점 이내)
    SCORE_TOLERANCE = 10
    
    top_tier_bucket = [
        outfit for outfit in outfits_sorted_by_fashion 
        if (highest_score - outfit['fashion_score']) <= SCORE_TOLERANCE
    ]

    final_recommendations = sorted(top_tier_bucket, key=lambda x: x['total_wear_count'])[:5]

    if len(final_recommendations) < 5:
        remaining = [o for o in outfits_sorted_by_fashion if o not in top_tier_bucket]
        final_recommendations.extend(remaining[:5 - len(final_recommendations)])

    if final_recommendations:
        max_style_score = max([o['style_score'] for o in final_recommendations])
    else:
        max_style_score = 0

    # TPO는 선택했지만 일치하는 옷이 없는 경우를 판별
    tpo_fallback_triggered = bool(target_tpo and max_style_score == 0)

    # 단순 리스트 반환이 아닌 딕셔너리로 상태값 함께 반환
    return {
        "recommendations": final_recommendations,
        "is_tpo_fallback": tpo_fallback_triggered,
        "message": "요청하신 TPO에 맞는 옷이 부족해, 날씨와 색상 조화가 가장 좋은 코디를 추천해드립니다." if tpo_fallback_triggered else "추천이 완료되었습니다."
    }
