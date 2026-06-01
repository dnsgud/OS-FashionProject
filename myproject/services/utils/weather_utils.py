import math

def calculate_sensory_temp(temp, humidity, wind_speed):
    """기온, 습도, 풍속으로 체감온도 계산"""
    try:
        e = (humidity / 100.0) * 6.105 * math.exp((17.27 * temp) / (237.7 + temp))
        sensory_temp = temp + (0.33 * e) - (0.70 * wind_speed) - 4.00
        return round(sensory_temp, 1)
    except Exception as e:
        print(f"체감온도 계산 오류: {e}")
        return temp
