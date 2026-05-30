import requests 
import os
import time
import logging
from dotenv import load_dotenv

# 💡 안전장치: 현재 파일(weather_service.py)과 같은 폴더 또는 상위 폴더의 .env를 명확하게 지정해서 로드합니다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# --- 캐시 설정을 위한 전역 변수 ---
weather_cache = {
    "data": None,
    "last_updated": 0
}
CACHE_DURATION = 600  # 캐시 유지 시간: 10분 (600초)

def fetch_weather_forecast():
    current_time = time.time()

    # 1. 캐시 확인 (10분 이내에 받아온 데이터가 있으면 바로 반환)
    if weather_cache["data"] and (current_time - weather_cache["last_updated"] < CACHE_DURATION):
        print("Using cached weather data...")
        return weather_cache["data"]

    api_key = os.getenv("OPENWEATHER_API_KEY")
    
    # 💡 API Key가 제대로 로드되었는지 체크하는 방어 로직
    if not api_key:
        logging.error("❌ [weather_service] OPENWEATHER_API_KEY를 .env 파일에서 찾을 수 없습니다!")
        return None

    # 5일 / 3시간 간격 예보 API (Cheongju 기준)
    url = f"https://api.openweathermap.org/data/2.5/forecast?q=Cheongju&appid={api_key}&units=metric" 
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            weather_dict = {
                "Clear": "맑음", "Clouds": "흐림", "Rain": "비", 
                "Drizzle": "이슬비", "Thunderstorm": "천둥번개", 
                "Snow": "눈", "Mist": "안개", "Fog": "안개"
            }

            forecast_list = []
            api_list = data.get('list', [])
            
            for i in range(min(4, len(api_list))): 
                item = api_list[i]
                
                main_info = item.get('main', {})
                wind_info = item.get('wind', {})
                weather_info = item.get('weather', [{}])[0]
                weather_main = weather_info.get('main', 'Clouds')
                
                # 💡 핵심 수정: 'condition'을 'status'로 변경하여 app.py와 연동되게 만듭니다!
                forecast_list.append({
                    "temp": round(main_info.get('temp', 0)),
                    "humidity": main_info.get('humidity', 0),       # 습도 (%)
                    "wind_speed": wind_info.get('speed', 0),        # 풍속 (m/s)
                    "status": weather_dict.get(weather_main, "알 수 없음"), # ✨ condition -> status로 변경!
                    "icon": get_icon_class(weather_main),
                    "dt_txt": item.get('dt_txt', '')
                })
            
            # 2. 캐시 갱신
            weather_cache["data"] = forecast_list
            weather_cache["last_updated"] = current_time
            
            print("Fetched new weather data from API.")
            return forecast_list
        else:
            logging.error(f"Weather API error: Status code {response.status_code}. API 키나 URL을 확인하세요.")
            return None

    except Exception as e:
        logging.error(f"Weather service exception: {e}")
        return None

def get_icon_class(weather_main):
    icons = {
        "Clear": "fa-sun",
        "Clouds": "fa-cloud-sun",
        "Rain": "fa-cloud-showers-heavy",
        "Snow": "fa-snowflake",
        "Thunderstorm": "fa-bolt"
    }
    return icons.get(weather_main, "fa-cloud")