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
        
#옷 추천 함수(current_temp 테스트 과정 중 입력으로 대체)
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
