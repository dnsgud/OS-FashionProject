from flask import Flask, render_template, jsonify
from weather_service import fetch_weather
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # 모든 경로에 대해 CORS 허용

@app.route('/')
def home():
    return render_template('weather_page.html')

@app.route('/api/weather')
def weather_api():
    try:
        # 1. weather_service.py에서 원본 데이터를 가져옴
        raw_data = fetch_weather()
        
        # 2. 프론트엔드 개발자가 사용하기 편하게 데이터를 보냄
        # (실시간 온도, 습도, 상태만 딱 골라주는 과정)
        refined_data = {
            "city": raw_data.get("name"),
            "temp": raw_data.get("main", {}).get("temp"),
            "humidity": raw_data.get("main", {}).get("humidity"),
            "condition": raw_data.get("weather", [{}])[0].get("description"),
            "icon": raw_data.get("weather", [{}])[0].get("icon")
        }
        
        return jsonify(refined_data)
        
    except Exception as e:
        # 에러 발생 시 프론트엔드가 알 수 있도록 메시지 전송
        return jsonify({"error": "실시간 데이터를 처리하는 중 오류가 발생했습니다."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
