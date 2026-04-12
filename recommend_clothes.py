from test_data import test_db   #테스트용 데이터베이스
import colorsys

# 하의 선택 시 허용할 온도 레벨 오차 범위 (±1 레벨까지 허용)
BOTTOM_TOLERANCE = 1

# 기본 색상(무채색 계열)
NEUTRAL_CHROMA = 15           # 채도가 15% 미만이면 무채색으로 간주
NEUTRAL_LIGHTNESS_LOW = 15    # 명도가 15% 이하이면 블랙 계열(무채색)
NEUTRAL_LIGHTNESS_HIGH = 90   # 명도가 90% 이상이면 화이트 계열(무채색)

#레벨 별 온도 기준
def get_target_level(temp):
    if temp >= 30: return 1
    elif temp >= 25: return 2
    elif temp >= 21: return 3
    elif temp >= 17: return 4
    elif temp >= 13: return 5
    elif temp >= 9:  return 6
    elif temp >= 5:  return 7
    elif temp >= 0:  return 8
    elif temp >= -5: return 9
    else: return 10

# [하의 필터링 함수]
def get_bottoms(clothes_db, target_lv):
    return [c for c in clothes_db if c.get('main_category') == '하의' 
            and abs(c['temp_level'] - target_lv) <= BOTTOM_TOLERANCE]

# [상의 + 아우터 조합 생성 함수]
def get_top_combinations(clothes_db, target_lv):
    inners = [c for c in clothes_db if c.get('main_category') == '상의' and c.get('sub_category') == '이너']
    outers = [c for c in clothes_db if c.get('main_category') == '상의' and c.get('sub_category') == '아우터']
    
    valid_combos = []   # 가능한 조합 저장 리스트
    
    # 이너 단독 조합
    for inner in inners:
        if inner['temp_level'] == target_lv:
            valid_combos.append([inner])

    # 2. 이너 + 아우터 조합
    for inner in inners:
        for outer in outers:
            # 두 옷의 온도 레벨 합이 목표 레벨과 일치하면 조합 저장
            if inner['temp_level'] + outer['temp_level'] == target_lv:
                valid_combos.append([inner, outer])
                
    return valid_combos

# [#FFFFFF 형식의 헥사 코드를 HSL로 변환하는 함수]
def hex_to_hsl(hex_str):
    try:
        hex_str = hex_str.lstrip('#')
        r, g, b = tuple(int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4))
        h, l, s = colorsys.rgb_to_hls(r, g, b) # H, L, S 순서로 반환
        return h * 360, s * 100, l * 100
    except:
        return 0, 0, 0 # 에러 발생 시 기본값

# [스타일 점수 계산 함수]
def calculate_style_score(full_outfit, target_tpo):
    """전체 코디(상의+하의)의 TPO 일치도를 계산"""
    score = 0
    for cloth in full_outfit:
        if target_tpo in cloth.get('tpo', []):
            score += 1
    return score

# [색상 점수 계산 함수]
def calculate_color_score(top_combo, bottom, target_lv):
    # 가장 바깥쪽 상의의 색상 (아우터 있으면 아우터, 없으면 상의)
    top_hex = top_combo[-1]['color'] 
    bottom_hex = bottom['color']

    h1, s1, l1 = hex_to_hsl(top_hex)
    h2, s2, l2 = hex_to_hsl(bottom_hex)

    score = 0

    # 무채색(Neutral) 여부 판별
    is_top_neutral = s1 < NEUTRAL_CHROMA or l1 < NEUTRAL_LIGHTNESS_LOW or l1 > NEUTRAL_LIGHTNESS_HIGH
    is_bottom_neutral = s2 < NEUTRAL_CHROMA or l2 < NEUTRAL_LIGHTNESS_LOW or l2 > NEUTRAL_LIGHTNESS_HIGH

    # 색상/명도/채도 차이 계산
    hue_diff = abs(h1 - h2)
    if hue_diff > 180: hue_diff = 360 - hue_diff
    chroma_diff = abs(s1 - s2)
    light_diff = abs(l1 - l2)

    # 1. 무채색이 하나라도 있으면 가산점
    if is_top_neutral or is_bottom_neutral:
        score += 1.5

    # 둘다 무채색이 아닌 경우
    if not is_top_neutral and not is_bottom_neutral:
        
    # 2. 톤온톤 (동일 색상, 다른 명도)
        if hue_diff < 30:
            if light_diff > 20:
                score += 1.5
            else: # 명도가 비슷한 경우 보다 적은 가산점 
                score += 0.5

    # 3. 톤앤톤 (다른 색상, 비슷한 명도/채도)
        elif hue_diff >= 30:
            if chroma_diff < 15 and light_diff < 15:
                score += 1.2
            
    # 4. 보색 감점
            elif hue_diff > 150:
                score -= 1.0

    # 5. 계절별 어울리는 색상 가산점
    # 여름 -> 밝은색(고명도) 추천
    if target_lv <= 3:
        if l1 >= 70: score += 0.8   # 상의
        if l2 >= 60: score += 0.4   # 하의    
    # 겨울 -> 어두운색(저명도) 추천
    elif target_lv >= 7:
        if l1 <= 30: score += 0.8   # 상의
        if l2 <= 40: score += 0.4   # 하의

    return score

# [옷 추천 함수](current_temp 테스트 과정 중 입력으로 대체)
def recommend_clothes(current_temp, target_tpo, clothes_db):
    print(f"\n 기온: {current_temp}°C | 목적: {target_tpo}")
    
    # 목표 온도 레벨 계산
    target_lv = get_target_level(current_temp)
    print(f"목표 온도 레벨: Level {target_lv}\n")

    # 조건에 맞는 하의/상의 조합 가져오기
    valid_bottoms = get_bottoms(clothes_db, target_lv)
    valid_top_combos = get_top_combinations(clothes_db, target_lv)

    outfits = []    # 최종 코디 저장 리스트
    
    # 상의 + 하의 모든 조합 생성
    for top_combo in valid_top_combos:
        for bottom in valid_bottoms:
            full_outfit = top_combo + [bottom]
            
            # 각 항목 점수 계산
            style_score = calculate_style_score(full_outfit, target_tpo)
            color_score = calculate_color_score(top_combo, bottom, target_lv)
            
            # 총점
            total_score = style_score + color_score

            # 결과 저장
            outfits.append({
                "top_combo": top_combo,
                "bottom": bottom,
                "style_score": style_score,
                "color_score": color_score,
                "total_score": total_score
            })

    # 총점이 높은 순으로 정렬
    sorted_outfits = sorted(outfits, key=lambda x: x['total_score'], reverse=True)

    # 결과 출력
    print("[최종 코디 추천 Top 5]")
    if not sorted_outfits:
        print(" 조건에 맞는 코디 조합이 없습니다.")
        return

    # 상위 5개 출력
    for idx, outfit in enumerate(sorted_outfits[:5], 1):
        top_names = " + ".join([f"{c['name']}({c['color']})" for c in outfit['top_combo']])
        bottom_name = f"{outfit['bottom']['name']}({outfit['bottom']['color']})"
        
        # 총 레벨 계산
        total_lv = sum([c['temp_level'] for c in outfit['top_combo']])
        
        print(f"  {idx}위. \n 상의: {top_names} \n 하의: {bottom_name}")
        print(f"       ↳ [총점: {outfit['total_score']}점] (스타일: {outfit['style_score']} / 색상: {outfit['color_score']} / 온도 총합 Lv.{total_lv})\n")
    print("-" * 50)
    
# 테스트 환경 
temp = int(input("현재 기온 입력(예: 14): "))
style = input("TPO 입력(예: 캐주얼, 미니멀, 포멀 등): ")
recommend_clothes(temp, style, test_db)
