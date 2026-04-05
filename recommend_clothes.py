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
