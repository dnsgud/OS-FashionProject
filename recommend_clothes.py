# 하의 선택 시 허용할 온도 레벨 오차 범위 (±1 레벨까지 허용)
BOTTOM_TOLERANCE = 1

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
        
# [옷 추천 함수](current_temp 테스트 과정 중 입력으로 대체)
def recommend_clothes(current_temp, clothes_db):
    target_lv = get_target_level(current_temp)
    
    tops = [c for c in clothes_db if c['main_category'] == '상의']
    bottoms = [c for c in clothes_db if c['main_category'] == '하의']
    
    print(f"목표 레벨: {target_lv}")
    for top in tops:
        for bottom in bottoms:
            if top['temp_level'] == target_lv:
                print(f"추천: {top['name']} + {bottom['name']}")

#테스트 입력
temp = int(input("현재 기온 입력(예: 14): "))
recommend_clothes(temp, clothes_db)
