import requests 
import os
from dotenv import load_dotenv

load_dotenv()

def fetch_weather():
    api_key = os.getenv("OPENWEATHER_API_KEY")
    url = f"https://api.openweathermap.org/data/2.5/weather?q=Cheongju&appid={api_key}&units=metric"
    
    response = requests.get(url)
    data = response.json()
    
    return {
        "temp": data['main']['temp'],
        "status": data['weather'][0]['main']
    }