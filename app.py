from flask import Flask, render_template, jsonify
from weather_service import fetch_weather
app = Flask(__name__)

@app.route('/')
def home():
    return render_template('weather_page.html')

@app.route('/api/weather')
def weather_api():
    try:
        # weather_service.py의 함수를 실행해 실제 날씨 데이터를 가져옵니다
        data = fetch_weather()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)