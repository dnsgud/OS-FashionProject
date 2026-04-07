# 하의 선택 시 허용할 온도 레벨 오차 범위 (±1 레벨까지 허용)
BOTTOM_TOLERANCE = 1
# 기본 색상(무채색 계열)
NEUTRAL_COLORS = ["블랙", "화이트", "그레이", "네이비", "아이보리", "베이지"] # 패션 기본/무채색

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
    return [c for c in clothes_db if c['main_category'] == '하의' 
            and abs(c['temp_level'] - target_lv) <= BOTTOM_TOLERANCE]

# [상의 + 아우터 조합 생성 함수]
def get_top_combinations(clothes_db, target_lv):
    tops = [c for c in clothes_db if c['main_category'] == '상의']  # 상의 리스트
    outers = [c for c in clothes_db if c['main_category'] == '아우터']  # 아우터 리스트
    valid_combos = []   # 가능한 조합 저장 리스트
    
    # 상의 단독 조합
    for top in tops:
        if top['temp_level'] == target_lv:
            valid_combos.append([top])

    # 상의 + 아우터 조합        
    for top in tops:
        for outer in outers:
            if top['temp_level'] + outer['temp_level'] == target_lv:
                valid_combos.append([top, outer])
                
    return valid_combos

# [스타일 점수 계산 함수]
def calculate_style_score(full_outfit, target_tpo):
    """전체 코디(상의+하의)의 TPO 일치도를 계산"""
    score = 0
    for cloth in full_outfit:
        if target_tpo in cloth.get('tpo', []):
            score += 1
    return score

# [색상 점수 계산 함수]
def calculate_color_score(top_combo, bottom):
    """상의(가장 겉옷)와 하의의 색상 조화 점수 계산"""
    score = 0
    # 가장 바깥쪽 상의의 색상 (아우터 있으면 아우터, 없으면 상의)
    main_top_color = top_combo[-1]['color']
    bottom_color = bottom['color']

    # 각각 무채색인지 여부 판단
    top_is_neutral = main_top_color in NEUTRAL_COLORS
    bottom_is_neutral = bottom_color in NEUTRAL_COLORS

    # 1. 무채색 매치 (안정적인 코디)
    if top_is_neutral or bottom_is_neutral:
        score += 1.0

    # 2. 톤온톤 / 깔맞춤 가점
    if main_top_color == bottom_color:
        score += 0.5
        
    # 3. 투머치 방지 (둘 다 튀는 색상인데 색이 다름)
    if not top_is_neutral and not bottom_is_neutral and main_top_color != bottom_color:
        score -= 1.0

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
    
    for top in tops:
        for bottom in bottoms:
            if top['temp_level'] == target_lv:
                print(f"추천: {top['name']} + {bottom['name']}")

# 테스트 환경
temp = int(input("현재 기온 입력(예: 14): "))
style = input("TPO 입력(예: 캐주얼, 미니멀, 포멀 등): ")
recommend_clothes(temp, style, mock_db)
