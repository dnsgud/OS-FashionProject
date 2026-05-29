import os
import sys
import logging
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

# [수정] 경로 설정을 최상단에서 진행
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)
app.secret_key = "my_fashion_app_secret_1234"

# 세션 유지 및 전역 변수 설정
@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=30)

@app.context_processor
def inject_user():
    return dict(logged_in='user_email' in session)

# 서비스 모듈 임포트 (try-except로 감싸서 에러 추적)
try:
    from config import supabase
    from weather_service import fetch_weather_forecast
    from auth_service import sign_up_user, login_user
    from services.imgproc import process_user_upload
    from services.recommend_clothes import recommend_clothes_logic
    print("✅ 서비스 모듈 로드 성공")
except Exception as e:
    print(f"❌ 서비스 임포트 중 오류: {e}")
    fetch_weather_forecast = None

# 업로드 폴더 설정
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- [날씨 API 캐싱 레이어 시스템 구현] ---
WEATHER_CACHE = {
    "data": None,
    "last_updated": None
}
CACHE_TTL = timedelta(minutes=10)  # 기획서 요구사항: TTL 10분 설정

def get_cached_weather():
    """매 요청마다 외부 API를 호출하지 않고, 메모리(캐시)에서 즉시 반환하는 함수"""
    now = datetime.now()
    
    # 캐시 데이터가 존재하고, 설정한 TTL(10분)이 지나지 않았다면 외부 서버 통신 생략 (CACHE HIT)
    if WEATHER_CACHE["data"] and WEATHER_CACHE["last_updated"]:
        if now - WEATHER_CACHE["last_updated"] < CACHE_TTL:
            print("⚡ [CACHE HIT] 외부 API를 호출하지 않고, 서버 메모리에서 즉시 데이터를 반환합니다.")
            return WEATHER_CACHE["data"]
            
    # 캐시가 없거나 10분이 지났다면(TTL 만료), 그때만 새로 외부 API 호출 (CACHE MISS)
    if fetch_weather_forecast:
        print("🌐 [CACHE MISS] 캐시가 만료되었거나 비어있습니다. 외부 API를 호출하여 캐시를 갱신합니다.")
        fresh_data = fetch_weather_forecast()
        if fresh_data:
            WEATHER_CACHE["data"] = fresh_data
            WEATHER_CACHE["last_updated"] = now
            return fresh_data
            
    return WEATHER_CACHE["data"]

# [유기적 연결] 하위 라우터들이 호출하는 fetch_weather가 캐시 함수를 바라보도록 바인딩
fetch_weather = get_cached_weather


# --- [라우트 설정] ---
   
@app.route('/')
def home():
    try:
        # [교정] 외부 API 직접 호출 대신 캐시 제어 함수 호출하도록 수정
        forecast_data = get_cached_weather() 
        
        if forecast_data:
            # 첫 번째(현재 시간대) 날씨를 메인 화면용으로 전달
            current_weather = forecast_data[0]
            return render_template('index.html', weather=current_weather)
        else:
            return render_template('index.html', weather=None)
            
    except Exception as e:
        logging.error(f"Home route error: {e}")
        return render_template('index.html', weather=None)

@app.route('/home')
def home_page(): 
    is_logged_in = 'user_email' in session
    user_email = session.get('user_email')
    
    if not user_email:
        return redirect(url_for('login'))

    # [연동] 캐시 레이어를 거쳐 데이터 수집 (10분 이내 연타 시 레이턴시 0ms)
    raw_weather = fetch_weather()
    
    current_weather = None
    if raw_weather and isinstance(raw_weather, list) and len(raw_weather) > 0:
        current_weather = raw_weather[0]

    return render_template('home.html',
                           weather=current_weather,
                           user_email=user_email,
                           logged_in=is_logged_in)

@app.route('/weather_detail')
def weather_detail():
    is_logged_in = 'user_email' in session
    
    try:
        # [연동] 캐시 레이어 연동
        raw_data = fetch_weather()
        print(f"--- 캐시 레이어 데이터 확인: {raw_data} ---")

        if raw_data and isinstance(raw_data, list):
            main_data = raw_data[0]
            
            temp = main_data.get('temp', '--')
            humidity = main_data.get('humidity', '--')
            wind_speed = main_data.get('wind_speed', '0')
            icon = main_data.get('icon', 'fa-sun')
        else:
            temp, humidity, wind_speed, icon = "ERR", "--", "0", "fa-exclamation-triangle"

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        temp, humidity, wind_speed, icon = "ERR", "--", "0", "fa-exclamation-triangle"

    hourly_data = [{
        'temp': temp,
        'humidity': humidity,
        'wind_speed': wind_speed,
        'wind_status': "보통" if wind_speed != "0" and float(wind_speed) < 5 else "강함",
        'icon': icon
    }]

    return render_template('weather_detail.html', hourly_data=hourly_data, logged_in=is_logged_in)

def process_weather_item(data, index, start_time):
    """각 예보 항목을 화면 표시용 포맷으로 변환"""
    target_time = start_time + timedelta(hours=index * 3)
    
    am_pm = "오전" if target_time.hour < 12 else "오후"
    display_hour = target_time.hour % 12
    display_hour = 12 if display_hour == 0 else display_hour
    
    wind_speed = data.get('wind_speed', 0)
    if wind_speed < 3.4:
        wind_status = "약함"
    elif wind_speed < 8.0:
        wind_status = "보통"
    else:
        wind_status = "강함"

    return {
        "time": f"{am_pm} {display_hour}시",
        "temp": data.get('temp', 0),
        "icon": data.get('icon', 'fa-cloud'),
        "humidity": data.get('humidity', 0),
        "wind_speed": wind_speed,
        "wind_status": wind_status
    }

@app.route('/login', methods=['GET', 'POST']) 
def login():
    if request.method == 'GET':
        return render_template('login.html')

    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        print(f"로그인 시도: {email}")

        is_success = login_user(email, password)
        print(f"Supabase 결과: {is_success}")

        if is_success:
            session['user_email'] = email
            return jsonify({"message": "로그인 성공"}), 200
        else:
            return jsonify({"error": "로그인 실패"}), 401

@app.route('/register') 
def register_page():
    return render_template('login_detail.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "이메일과 비밀번호를 입력해주세요."}), 400

    success = sign_up_user(email, password)

    if success:
        return jsonify({"message": "회원가입 성공!"}), 201
    else:
        return jsonify({"error": "회원가입에 실패했습니다. 이미 존재하는 계정일 수 있습니다."}), 400
    
@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('home')) 

@app.route('/api/upload', methods=['POST'])
def upload_cloth():
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({"error": "로그인이 필요합니다."}), 401

        if 'cloth_image' not in request.files:
            return jsonify({"error": "사진 파일이 없습니다."}), 400
        
        file = request.files['cloth_image']
        if file.filename == '':
            return jsonify({"error": "선택된 파일이 없습니다."}), 400

        name = request.form.get('name', '이름 없음')
        main_category = request.form.get('main_category', 'top')
        sub_category = request.form.get('sub_category', '')
        color = request.form.get('color', '#000000')
        tpo = request.form.get('tpo', '')

        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        try:
            db_data = {
                "user_email": user_email,
                "name": name,
                "main_category": main_category,
                "sub_category": sub_category,
                "color": color,
                "tpo": tpo,
                "image_url": f"/static/uploads/{filename}" 
            }
            response = supabase.table("clothes").insert(db_data).execute()
            result = response.data
        except Exception as db_err:
            print(f"❌ DB 삽입 오류: {db_err}")
            result = None

        if result:
            return jsonify({"message": "옷 등록 성공!", "data": result}), 200
        else:
            return jsonify({"error": "데이터베이스 저장 실패"}), 500

    except Exception as e:
        return jsonify({"error": f"서버 오류: {str(e)}"}), 500

@app.route('/api/recommend')
def recommend():
    try:
        # [연동] 캐시 적용된 날씨 사용
        weather_data = fetch_weather()
        
        # 구조가 데이터 타입에 따라 안전하도록 방어 코드 구현
        if isinstance(weather_data, list) and len(weather_data) > 0:
            temp = weather_data[0].get("temp", 20)
        else:
            temp = 20
            
        target_tpo = request.args.get('tpo', '캐주얼')

        user_email = session.get('user_email')
        if not user_email:
            return jsonify({"error": "로그인이 필요합니다."}), 401

        response = supabase.table("clothes").select("*").eq("user_email", user_email).execute()
        user_clothes = response.data

        top_5_outfits = recommend_clothes_logic(temp, target_tpo, user_clothes)
        
        return jsonify({
            "current_temp": temp,
            "target_tpo": target_tpo,
            "recommendations": top_5_outfits
        })
    except Exception as e:
        return jsonify({"error": f"추천 실패: {str(e)}"}), 500

@app.route('/guide')
def guide_page():
    # [연동] 가이드 페이지 이동 시에도 세션 유지 신호 전달
    is_logged_in = 'user_email' in session
    user_email = session.get('user_email')
    return render_template('guide.html', logged_in=is_logged_in, user_email=user_email)

@app.route('/body-guide')
def body_guide():
    return "<h3>준비 중입니다!</h3><br><a href='/guide'>가이드로 돌아가기</a>"

@app.route('/codi')
def codi_page():
    # [연동] 코디 페이지 이동 시에도 세션 유지 신호 전달
    is_logged_in = 'user_email' in session
    user_email = session.get('user_email')
    return render_template('codi.html', logged_in=is_logged_in, user_email=user_email)

@app.route('/my_closet')
def my_closet():
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('login'))
    
    is_logged_in = 'user_email' in session
    
    try:
        response = supabase.table("clothes").select("*").eq("user_email", user_email).execute()
        clothes_list = response.data
    except Exception as e:
        print(f"❌ DB에서 옷 목록 가져오기 실패: {e}")
        clothes_list = []

    raw_weather = fetch_weather()
    current_weather = None
    if raw_weather and isinstance(raw_weather, list) and len(raw_weather) > 0:
        current_weather = raw_weather[0]

    return render_template('my_closet.html', 
                           clothes=clothes_list, 
                           weather=current_weather,
                           user_email=user_email,
                           logged_in=is_logged_in)

@app.route('/add_clothes')
def add_clothes():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    return render_template('add_clothes.html')

@app.route('/add_clothes_photo')
def add_clothes_photo():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    return render_template('add_clothes_photo.html')

@app.route('/clothes_detail/<int:cloth_id>')
def clothes_detail(cloth_id):
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    try:
        response = supabase.table("clothes").select("*").eq("id", cloth_id).execute()
        cloth_data = response.data[0] if response.data else None
    except Exception as e:
        print(f"❌ DB 상세 조회 실패: {e}")
        cloth_data = None

    return render_template('clothes_detail.html', cloth=cloth_data)

@app.route('/api/clothes/update/<int:cloth_id>', methods=['POST'])
def update_cloth_api(cloth_id):
    if 'user_email' not in session:
        return jsonify({"error": "로그인이 필요합니다."}), 401
        
    data = request.get_json()
    try:
        response = supabase.table("clothes").update({
            "name": data.get('name'),
            "main_category": data.get('main_category'),
            "sub_category": data.get('sub_category'),
            "color": data.get('color'),
            "tpo": data.get('tpo')
        }).eq("id", cloth_id).execute()
        
        return jsonify({"message": "수정 성공", "data": response.data}), 200
    except Exception as e:
        return jsonify({"error": f"수정 실패: {str(e)}"}), 500

@app.route('/api/clothes/delete/<int:cloth_id>', methods=['POST'])
def delete_cloth_api(cloth_id):
    if 'user_email' not in session:
        return jsonify({"error": "로그인이 필요합니다."}), 401
        
    try:
        supabase.table("clothes").delete().eq("id", cloth_id).execute()
        return jsonify({"message": "삭제 성공"}), 200
    except Exception as e:
        return jsonify({"error": f"삭제 실패: {str(e)}"}), 500

@app.route('/my_scrap')
def my_scrap():
    return "<h3>스크랩북 기능은 개발 준비 중입니다!</h3><br><a href='/home'>돌아가기</a>"

@app.route('/my_profile')
def my_profile():
    return "<h3>스타일 설정 기능은 개발 준비 중입니다!</h3><br><a href='/home'>돌아가기</a>"

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 패션 코드 서버가 가동되었습니다!")
    print("🔗 접속 주소: http://127.0.0.1:5000")
    print("="*50 + "\n")
    
    # [팁] 디버그 모드를 True로 키면 세션 유지 및 코드 수정 테스트가 훨씬 안정적이고 편리해집니다.
    app.run(host='0.0.0.0', port=5000, debug=True)
