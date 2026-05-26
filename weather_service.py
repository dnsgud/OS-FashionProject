import requests 
import os
from dotenv import load_dotenv

load_dotenv()

def fetch_weather():
    api_key = os.getenv("OPENWEATHER_API_KEY")
    url = f"https://api.openweathermap.org/data/2.5/weather?q=Cheongju&appid={api_key}&units=metric&lang=kr" # lang=kr 추가 시 한국어 설명 가능
    
    response = requests.get(url)
    if response.status_code == 200:
        return response.json() 
    else:
        return None