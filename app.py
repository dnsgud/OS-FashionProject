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
    fetch_weather = fetch_weather_forecast  # 별칭 설정
    from auth_service import sign_up_user, login_user
    from services.imgproc import process_user_upload
    from services.recommend_clothes import recommend_clothes_logic
    print("✅ 서비스 모듈 로드 성공")
except Exception as e:
    print(f"❌ 서비스 임포트 중 오류: {e}")
    fetch_weather = None

# 업로드 폴더 설정
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- [라우트 설정] ---
   
@app.route('/')
def home():
    try:
        forecast_data = fetch_weather_forecast() # 리스트 형태 [{}, {}, {}, {}]
        
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

    # 날씨 데이터 가져오기
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
        raw_data = fetch_weather()
        print(f"--- API 데이터 확인: {raw_data} ---")

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

# [핵심 수동 업로드 연동 구현] add_clothes.html의 비동기 폼 요청 수신 라우터
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

        # 데이터베이스 필드 값 수집
        name = request.form.get('name', '이름 없음')
        main_category = request.form.get('main_category', 'top')
        sub_category = request.form.get('sub_category', '')
        color = request.form.get('color', '#000000')
        tpo = request.form.get('tpo', '')

        # 서버에 임시 이미지 저장 후 보관
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        # 수동 등록 데이터를 데이터베이스에 직접 삽입 처리합니다.
        # (기존 AI 분석 프로세스인 process_user_upload 대신 사용자가 채운 값을 직접 바인딩)
        try:
            # 원하시는 Supabase 테이블 형태 및 컬럼 구조에 맞춰 딕셔너리를 구성하여 보냅니다.
            db_data = {
                "user_email": user_email,
                "name": name,
                "main_category": main_category,
                "sub_category": sub_category,
                "color": color,
                "tpo": tpo,
                "image_url": f"/static/uploads/{filename}" # 로컬 static 경로 맵핑
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
        weather_data = fetch_weather()
        temp = weather_data.get("main", {}).get("temp")
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
    return render_template('guide.html')

@app.route('/body-guide')
def body_guide():
    return "<h3>준비 중입니다!</h3><br><a href='/guide'>가이드로 돌아가기</a>"


@app.route('/codi')
def codi_page():
    return render_template('codi.html')

@app.route('/my_closet')
def my_closet():
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('login'))
    
    # 템플릿 내비바 분기용 세션 플래그 체크
    is_logged_in = 'user_email' in session
    
    try:
        response = supabase.table("clothes").select("*").eq("user_email", user_email).execute()
        clothes_list = response.data
    except Exception as e:
        print(f"❌ DB에서 옷 목록 가져오기 실패: {e}")
        clothes_list = []

    # [교정] home.html과 똑같이 weather, user_email, logged_in을 전부 바인딩해서 넘겨줍니다.
    # 메인 화면 날씨 규격을 유지하기 위해 날씨 정보도 함께 서빙
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

# [수정 연동 완료] clothes_detail.html을 열 때 실제 DB 단일 행 데이터를 함께 넘겨줍니다.
@app.route('/clothes_detail/<int:cloth_id>')
def clothes_detail(cloth_id):
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    try:
        # 단일 고유 옷의 상세 정보를 DB에서 매핑해 가져옵니다.
        response = supabase.table("clothes").select("*").eq("id", cloth_id).execute()
        cloth_data = response.data[0] if response.data else None
    except Exception as e:
        print(f"❌ DB 상세 조회 실패: {e}")
        cloth_data = None

    return render_template('clothes_detail.html', cloth=cloth_data)

# [신규 연동 구현] clothes_detail.html 내에서 보낸 비동기 '수정 요청' 처리 라우터
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

# [신규 연동 구현] clothes_detail.html 내에서 보낸 비동기 '삭제 요청' 처리 라우터
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
    
    app.run(host='0.0.0.0', port=5000, debug=False)