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
