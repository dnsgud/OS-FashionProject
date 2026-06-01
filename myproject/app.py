import os
import sys
import logging
import traceback
import uuid
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, make_response, flash
from flask_cors import CORS
from werkzeug.utils import secure_filename

supabase = None
fetch_weather_forecast = None
process_user_upload = None
recommend_clothes_logic = None
request_find_id = None
verify_and_get_login_id = None
request_find_password = None
verify_password_reset_code = None
reset_password_and_auto_login = None
add_scrap_to_db = None
delete_scrap_from_db = None
get_user_scraps_with_details = None

try:
    from config import supabase
    from weather_service import fetch_weather_forecast
    from auth_service import sign_up_user, login_user, get_email_by_login_id, fetch_user_profile
    from services.imgproc import update_closet_cloth, delete_closet_cloth, process_user_upload, modify_and_confirm_ai_analysis, delete_unverified_cloth
    from services.recommend_clothes import recommend_clothes_logic
    from services.userprofile import update_account_password, change_profile_password, _filter_body_profile_data
    from services.auth import _validate_password_match
    from services.scrap_service import add_scrap_to_db, delete_scrap_from_db, get_user_scraps_with_details
    from services.account_recovery import (
        request_find_id, verify_and_get_login_id, request_find_password, 
        verify_password_reset_code, reset_password_and_auto_login
    )
    print("✅ 모든 서비스 모듈 로드 및 임포트 완료")
except Exception as e:
    print(f"❌ 모듈 로드 중 치명적 오류 발생: {e}")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app, supports_credentials=True)
app.secret_key = "my_fashion_app_secret_1234"

UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

WEATHER_CACHE = {
    "data": None,
    "last_updated": None
}

# 날씨 API 호출 결과를 10분간 캐싱하여 반환하는 함수
def get_cached_weather():
    now = datetime.now()
    if WEATHER_CACHE["data"] and WEATHER_CACHE["last_updated"]:
        if now - WEATHER_CACHE["last_updated"] < timedelta(minutes=10):
            return WEATHER_CACHE["data"]
            
    if fetch_weather_forecast:
        fresh_data = fetch_weather_forecast()
        if fresh_data:
            WEATHER_CACHE["data"] = fresh_data
            WEATHER_CACHE["last_updated"] = now
            return fresh_data
            
    return WEATHER_CACHE["data"]

fetch_weather = get_cached_weather

# 모든 요청 전에 세션 유지 시간을 제어하는 함수
@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=30)

# 전역 템플릿 영역에 세션 로그인 여부 변수를 주입하는 함수
@app.context_processor
def inject_user():
    is_logged_in = 'user_email' in session or 'login_id' in session
    return dict(logged_in=is_logged_in)

# 아이디 찾기 인증번호 발송을 요청하는 API 라우터
@app.route('/api/find-id/request', methods=['POST'])
def api_request_find_id():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    if not request_find_id: return jsonify({"success": False, "error": "모듈이 로드되지 않았습니다."}), 500
    if request_find_id(name, email): return jsonify({"success": True, "message": "입력하신 이메일로 4자리 인증번호가 발송되었습니다."}), 200
    return jsonify({"success": False, "error": "등록되지 않은 이름이거나 이메일 주소입니다."}), 400

# 아이디 찾기 인증번호를 대조 및 검증하는 API 라우터
@app.route('/api/find-id/verify', methods=['POST'])
def api_verify_find_id():
    data = request.get_json()  
    name = data.get('name')
    email = data.get('email')
    code = data.get('code')
    if not verify_and_get_login_id: return jsonify({"success": False, "error": "모듈이 로드되지 않았습니다."}), 500
    login_id = verify_and_get_login_id(name, email, code)
    if login_id: return jsonify({"success": True, "login_id": login_id}), 200
    return jsonify({"success": False, "error": "인증번호가 일치하지 않거나 만료되었습니다."}), 400

# 비밀번호 찾기 통과 후 최종 재설정을 처리하는 API 라우터
@app.route('/api/find-pw/reset', methods=['POST'])
def api_reset_pw():
    data = request.get_json()
    login_id = data.get('login_id')
    new_pw = data.get('new_pw')
    new_pw_confirm = data.get('new_pw_confirm')

    success = reset_password_and_auto_login(login_id, new_pw, new_pw_confirm)
    if success:
        return jsonify({"success": True, "message": "비밀번호가 성공적으로 변경되었습니다."}), 200
    return jsonify({"success": False, "error": "비밀번호 변경 중 오류가 발생했습니다."}), 400

# 비밀번호 찾기 본인 인증번호 발송을 처리하는 API 라우터
@app.route('/api/find-pw/request', methods=['POST'])
def api_request_find_pw():
    data = request.get_json()
    name = data.get('name')
    login_id = data.get('login_id')
    email = data.get('email')
    print(f"DEBUG: 이메일 발송 요청 - {name}, {login_id}, {email}")
    if 'request_find_password' not in globals():
        return jsonify({"success": False, "error": "계정 복구 모듈이 로드되지 않았습니다."}), 500
    if request_find_password(name, login_id, email): 
        return jsonify({"success": True, "message": "인증번호가 발송되었습니다."}), 200
    return jsonify({"success": False, "error": "입력 정보와 일치하는 계정을 찾을 수 없습니다."}), 400

# 비밀번호 찾기 인증번호 유효성을 검증하는 API 라우터
@app.route('/api/find-pw/verify', methods=['POST'])
def api_verify_find_pw():
    data = request.get_json()
    email = data.get('email')
    input_code = data.get('input_code') 
    if not verify_password_reset_code: 
        return jsonify({"success": False, "error": "모듈이 로드되지 않았습니다."}), 500
    if verify_password_reset_code(email, input_code): 
        return jsonify({"success": True, "message": "본인 인증이 완료되었습니다. 새 비밀번호를 설정해 주세요."}), 200
    return jsonify({"success": False, "error": "인증번호가 일치하지 않습니다."}), 400

# 웹 서비스 인트로 메인 화면을 렌더링하는 라우터
@app.route('/')
def home():
    try:
        forecast_data = get_cached_weather() 
        if forecast_data:
            current_weather = forecast_data[0]
            return render_template('index.html', weather=current_weather)
        else:
            return render_template('index.html', weather=None)
    except Exception as e:
        logging.error(f"Home route error: {e}")
        return render_template('index.html', weather=None)

# 로그인 성공 회원용 대시보드 홈 화면을 렌더링하는 라우터
@app.route('/home')
def home_page(): 
    is_logged_in = 'user_email' in session or 'login_id' in session
    user_email = session.get('user_email')
    if not user_email: return redirect(url_for('login'))
    raw_weather = fetch_weather()
    current_weather = raw_weather[0] if raw_weather and isinstance(raw_weather, list) and len(raw_weather) > 0 else None
    return render_template('home.html', weather=current_weather, user_email=user_email, logged_in=is_logged_in)

# 3시간 단위 정밀 기상 정보 상세 페이지를 렌더링하는 라우터
@app.route('/weather_detail')
def weather_detail():
    is_logged_in = 'user_email' in session or 'login_id' in session
    try: raw_data = fetch_weather()
    except Exception as e:
        print(f"❌ 날씨 가져오기 치명적 오류: {e}")
        raw_data = None
    hourly_data = []
    start_time = datetime.now()
    
    # 예보 데이터 배열을 순회하며 정해진 시간 포맷 가이드라인에 맞춰 재가공하는 반복문
    if raw_data and isinstance(raw_data, list) and len(raw_data) > 0:
        for idx, data in enumerate(raw_data):
            if not isinstance(data, dict): continue
            target_time = start_time + timedelta(hours=idx * 3)
            am_pm = "오전" if target_time.hour < 12 else "오후"
            display_hour = target_time.hour % 12
            display_hour = 12 if display_hour == 0 else display_hour
            wind_speed = data.get('wind_speed', 0)
            wind_status = "약함" if wind_speed < 3.4 else "보통" if wind_speed < 8.0 else "강함"
            hourly_data.append({
                "time": f"{am_pm} {display_hour}시", "temp": data.get('temp', '--'), "icon": data.get('icon', 'fa-cloud'),
                "status": data.get('status', '맑음'), "humidity": data.get('humidity', 0), "wind_speed": wind_speed, "wind_status": wind_status
            })
    return render_template('weather_detail.html', hourly_data=hourly_data, logged_in=is_logged_in)

# 회원 자격 검증 및 로그인 세션을 생성 처리하는 라우터
@app.route('/login', methods=['GET', 'POST']) 
def login():
    if request.method == 'GET': 
        return render_template('login.html')
        
    if request.method == 'POST':
        data = request.get_json()
        login_id = data.get('login_id')
        password = data.get('password')    
        user_data = login_user(login_id, password) 
        
        # 인증 토큰 및 회원 정보 유효 유무를 가려 세션을 세팅하는 조건문
        if user_data:
            session['login_id'] = user_data.get('login_id')
            session['user_email'] = user_data.get('email') 
            return jsonify({"message": "로그인 성공"}), 200
        else:
            return jsonify({"error": "아이디 또는 비밀번호가 틀렸습니다."}), 401
        
# 회원가입 입력 폼 인터페이스를 렌더링하는 라우터
@app.route('/register') 
def register_page():
    return render_template('sign_up.html')

# 입력 명세 유효성 대조 후 신규 회원 레코드를 삽입하는 API 라우터
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data: return jsonify({"error": "데이터가 없습니다."}), 400
    email = data.get('email')
    password = data.get('password')
    nickname = data.get('nickname')
    username = data.get('username')
    name = data.get('name')
    gender = data.get('gender', '미선택')
    if not email or not password or not username: 
        return jsonify({"error": "필수 정보를 모두 입력해주세요."}), 400    
    try:
        from services.auth import _validate_login_id, _validate_email_format, check_login_id_duplicate, check_email_duplicate   
        if not _validate_email_format(email) or not check_email_duplicate(email):
            return jsonify({"error": "유효하지 않거나 이미 사용 중인 이메일입니다."}), 400       
        if not _validate_login_id(username) or not check_login_id_duplicate(username):
            return jsonify({"error": "아이디는 영문/숫자 4~15자여야 하며, 이미 사용 중일 수 없습니다."}), 400       
    except Exception as e:
        print(f"⚠️ 검증 모듈 로드 오류 (기존 가입 프로세스로 우회 진행): {e}")
    try:
        success = sign_up_user(email, password, nickname, username, name, gender)
        if success: return jsonify({"message": "회원가입 성공!"}), 201
        else: return jsonify({"error": "DB 저장 실패"}), 400
    except Exception as e:
        print(f"서버 에러: {e}")
        return jsonify({"error": str(e)}), 500
            
# 마이페이지 내 패스워드 테이블 정보 변경을 대행하는 API 라우터
@app.route('/api/update_password', methods=['POST'])
def update_password_api():
    login_id = session.get('login_id')
    data = request.json
    
    print("\n==================================")
    print(f"🔒 [디버그] 비밀번호 변경 시도")
    print(f" - 세션 login_id: {login_id}")
    print("==================================\n")
    
    if not login_id:
        return jsonify({"status": "fail", "message": "로그인 세션이 만료되었습니다. 다시 로그인해주세요."}), 401
        
    current_pw = data.get('currentPw')
    new_pw = data.get('newPw')
    
    try:
        user_data = supabase.table("users").select("pw").eq("login_id", login_id).execute()
        if not user_data.data:
            return jsonify({"status": "fail", "message": "회원 정보를 찾을 수 없습니다."}), 404
            
        db_password = user_data.data[0].get("pw")
        if db_password != current_pw:
            return jsonify({"status": "fail", "message": "기존 비밀번호가 올바르지 않습니다."}), 400

        update_response = supabase.table("users").update({
            "pw": new_pw 
        }).eq("login_id", login_id).execute()
        
        if not update_response.data:
            return jsonify({"status": "fail", "message": "비밀번호 DB 업데이트에 실패했습니다."}), 400
            
        print(f"✅ [디버그] DB 비밀번호 갱신 성공: {login_id}")
        return jsonify({"status": "success", "message": "비밀번호가 성공적으로 변경되었습니다."}), 200
    except Exception as e:
        print("\n❌ [디버그] 비밀번호 변경 중 에러 발생!")
        traceback.print_exc()
        return jsonify({"status": "fail", "message": "서버 시스템 통신 중 오류가 발생했습니다."}), 500        

# 유저 로그인 쿠키 및 세션 저장소를 비우는 로그아웃 라우터
@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('home')) 

# 수동 등록 양식 기반 신규 의류 품목을 옷장에 추가하는 라우터
@app.route('/add_clothes', methods=['GET', 'POST'])
def add_clothes():
    if 'user_email' not in session and 'login_id' not in session: 
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        user_email = session.get('user_email')
        cloth_name = request.form.get('cloth_name')
        main_category = request.form.get('main_category') 
        sub_category = request.form.get('sub_category')   
        fit = request.form.get('fit') 
        cloth_color = request.form.get('cloth_color')
        styles = request.form.get('styles')
        temp_level = request.form.get('temp_level', 5)
        file = request.files.get('cloth_image')
        storage_url = "" 
        
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1]
            unique_filename = f"{uuid.uuid4()}{ext}"
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(file_path) 
            try:
                bucket_name = 'test-clothes-imgaes' 
                with open(file_path, 'rb') as f:
                    supabase.storage.from_(bucket_name).upload(
                        path=unique_filename, file=f, file_options={"content-type": file.content_type}
                    )
                storage_url = supabase.storage.from_(bucket_name).get_public_url(unique_filename)
            except Exception as e:
                print(f"❌ Storage 업로드 에러: {e}")
            finally:
                if os.path.exists(file_path): 
                    os.remove(file_path)
        ai_tags_list = []
        if main_category:
            ai_tags_list.append(main_category)
        if sub_category:
            ai_tags_list.append(sub_category) 
        if main_category == "상의":
            ai_tags_list.append("top")
        elif main_category == "하의":
            ai_tags_list.append("bottom")
        if sub_category == "아우터":
            ai_tags_list.append("outerwear")
        elif sub_category == "이너":
            ai_tags_list.append("t-shirt") 
        elif sub_category == "바지":
            ai_tags_list.append("pants")

        insert_payload = {
            "user_email": user_email,
            "name": cloth_name,
            "main_category": main_category,
            "sub_category": sub_category,
            "fit": fit,  
            "color": cloth_color,
            "style": styles.split(',') if styles else [],
            "temp_level": int(temp_level),
            "image_url": storage_url,
            "ai_tags": ai_tags_list,
            "is_verified": True
        }
        if supabase: 
            try:
                supabase.table("clothes").insert(insert_payload).execute()
            except Exception as e:
                print(f"❌ DB 저장 에러: {e}")
        return redirect(url_for('my_closet'))
    return render_template('add_clothes.html')

# AI 자동 의상 사진 분석 대기 인터페이스를 호출하는 라우터
@app.route('/add_clothes_photo')
def add_clothes_photo():
    if 'user_email' not in session and 'login_id' not in session: return redirect(url_for('login'))
    return render_template('add_clothes_photo.html')

# 미디어 파일의 카테고리/컬러 정보를 컴퓨터 비전 분석 요청하는 API 라우터
@app.route('/ai_analysis', methods=['POST'])
def ai_analysis():
    user_email = session.get('user_email')
    if not user_email: return jsonify({"error": "로그인이 필요합니다."}), 401
    if 'ai_clothes_img' not in request.files: return "사진 파일이 누락되었습니다.", 400
    file = request.files['ai_clothes_img']
    if file.filename == '': return "선택된 파일이 없습니다.", 400
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    if process_user_upload:
        print(f"🚀 [app.py] AI 분석 엔진 시동: {user_email}")
        result = process_user_upload(file_path, user_email)
        
        if os.path.exists(file_path): 
            os.remove(file_path)
            
        if result:
            results_payload = {
                "id": result.get('id'),
                "image_path": result.get('image_url'), 
                "detected_name": result.get('name', 'AI 추출 의류 명칭'),
                "detected_main": result.get('main_category', '상의'),
                "detected_sub": result.get('sub_category', '이너'),
                "detected_color": result.get('color', '#ffffff'),
                "detected_tags": result.get('style', [])
            }
            return render_template('add_clothes_photo_detail.html', results=results_payload, user_email=user_email)
            
    return "AI 의상 인프라 분석 오류 발생", 500

# 가의류 임시 분석 리스트 보정 완료 후 정식 의류로 승인 인서트하는 라우터
@app.route('/save-closet-item', methods=['POST'])
def save_clothes():
    if 'user_email' not in session and 'login_id' not in session: 
        return redirect(url_for('login'))
    cloth_id = request.form.get('cloth_id')  
    cloth_name = request.form.get('item_name')
    main_category = request.form.get('category_main')
    sub_category = request.form.get('category_sub')
    cloth_color = request.form.get('color')
    styles = request.form.get('tpo_tags')  
    update_payload = {
        "name": cloth_name,
        "main_category": main_category,
        "sub_category": sub_category,
        "color": cloth_color,
        "style": styles.split(',') if styles and styles != "" else [],
        "is_verified": True 
    }
    if supabase and cloth_id:
        supabase.table("clothes").update(update_payload).eq("id", cloth_id).execute()
    return redirect(url_for('my_closet'))

# 날씨 및 개별 패션 평점 가중치를 집계하여 세트 리스트를 뿌려주는 API 라우터
@app.route('/api/recommend')
def recommend():
    try:
        weather_data = fetch_weather()
        if isinstance(weather_data, list) and len(weather_data) > 0:
            current_weather = weather_data[0]
            temp = current_weather.get("temp", 20)
            humidity = current_weather.get("humidity", 50)
            wind_speed = current_weather.get("wind_speed", 1.5)
        else:
            temp, humidity, wind_speed = 20, 50, 1.5

        target_tpo = request.args.get('tpo', '캐주얼')
        user_email = session.get('user_email')
        if not user_email: 
            return jsonify({"error": "로그인이 필요합니다."}), 401
            
        user_clothes = []
        user_body_shape = None
        user_weights = None

        if supabase:
            user_prof = supabase.table("users").select("body_shape").eq("email", user_email).execute()
            if user_prof.data:
                user_body_shape = user_prof.data[0].get("body_shape")

            response = supabase.table("clothes").select("*").eq("user_email", user_email).execute()
            user_clothes = response.data

            # 유저 옷 가방 루프 내에서 temp_level 사양을 정수 가공 처리하는 반복문
            for item in user_clothes:
                item['temp_level'] = int(item.get('temp_level', 5))
        if recommend_clothes_logic:
            algo_result = recommend_clothes_logic(
                current_temp=temp,
                humidity=humidity,
                wind_speed=wind_speed,
                target_tpo=target_tpo,
                user_body_shape=user_body_shape,
                clothes_db=user_clothes,
                weights=user_weights
            )
            
            if isinstance(algo_result, dict):
                recommendations = algo_result.get("recommendations", [])
                message = algo_result.get("message", "추천이 완료되었습니다.")
                is_tpo_fallback = algo_result.get("is_tpo_fallback", False)
            else:
                recommendations = algo_result
                message = "추천된 옷이 없습니다."
                is_tpo_fallback = False
        else:
            recommendations = []
            message = "추천 서비스 코드가 활성화되어 있지 않습니다."
            is_tpo_fallback = False

        return jsonify({
            "current_temp": temp, 
            "target_tpo": target_tpo, 
            "recommendations": recommendations,
            "message": message,
            "is_tpo_fallback": is_tpo_fallback
        })

    except Exception as e:
        print(f"❌ 추천 제어 레이어 동적 결합 오류 발생: {e}")
        traceback.print_exc()
        return jsonify({
            "current_temp": 20, 
            "target_tpo": "캐주얼", 
            "recommendations": [], 
            "message": "코디 엔진 연산 중 시스템 오류가 발생했습니다.",
            "is_tpo_fallback": False
        })

# 종합 패션 스타일 큐레이션 허브 안내창 렌더링 라우터
@app.route('/guide')
def guide_main(): 
    user_email = session.get('user_email')
    return render_template('guide.html', user_email=user_email)

# 의류 인프라 백과사전 사전 도감 명세 조회 라우터
@app.route('/guide/dictionary')
def guide_dictionary():
    try: return render_template('guide_dictionary.html')
    except Exception: return "<h3>기본 패션 아이템 도감 페이지 준비 중입니다!</h3><br><a href='/guide'>가이드로 돌아가기</a>"

# 삼각형/역삼각형 3대 체형별 가이드 명세 조회 라우터
@app.route('/body_guide')
def body_guide():
    try:
        is_logged_in = 'user_email' in session or 'login_id' in session
        user_email = session.get('user_email')
        return render_template('body_guide.html', logged_in=is_logged_in, user_email=user_email)
    except Exception as e:
        return "<h3>체형별 가이드 페이지 준비 중입니다!</h3><br><a href='/guide'>가이드로 돌아가기</a>"

# 보유 아이템 기온별 조합 연산 렌더링 라우터
@app.route('/codi')
def codi_page():
    is_logged_in = 'user_email' in session or 'login_id' in session
    user_email = session.get('user_email')
    return render_template('codi.html', logged_in=is_logged_in, user_email=user_email)

# 데이트/비즈니스 등 특수 상황 목적별 복장 명세 조회 라우터
@app.route('/tpo_guide')
def tpo_guide():
    try:
        is_logged_in = 'user_email' in session or 'login_id' in session
        user_email = session.get('user_email')
        return render_template('tpo_guide.html', logged_in=is_logged_in, user_email=user_email)
    except Exception:
        return "<h3>TPO 가이드 페이지 준비 중입니다!</h3><br><a href='/guide'>가이드로 돌아가기</a>"
        
# 톤온톤 매칭 가이드 정보 페이지 렌더링 라우터
@app.route('/color_guide')
def color_guide():
    try:
        is_logged_in = 'user_email' in session or 'login_id' in session
        user_email = session.get('user_email')
        return render_template('color_guide.html', logged_in=is_logged_in, user_email=user_email)
    except Exception as e:
        return "<h3>컬러 매칭 가이드 페이지 준비 중입니다!</h3><br><a href='/guide'>가이드로 돌아가기</a>"

# 보관 등록 완료된 내 의류 격자 앨범 조회 라우터
@app.route('/my_closet')
def my_closet():
    user_email = session.get('user_email')
    if not user_email: return redirect(url_for('login'))
    is_logged_in = 'user_email' in session or 'login_id' in session
    clothes_list = []
    try:
        if supabase:
            response = supabase.table("clothes").select("*").eq("user_email", user_email).execute()
            clothes_list = response.data
    except Exception as e:
        print(f"❌ 내 옷장 조회 실패: {e}")
    raw_weather = fetch_weather()
    current_weather = raw_weather[0] if raw_weather and isinstance(raw_weather, list) and len(raw_weather) > 0 else None
    return render_template('my_closet.html', clothes=clothes_list, weather=current_weather, user_email=user_email, logged_in=is_logged_in)

# 단일 의류 카드의 디테일 스펙(핏, 고유ID) 명세 렌더링 라우터
@app.route('/clothes_detail/<int:cloth_id>', methods=['GET'])
def clothes_detail(cloth_id):
    try:
        response = supabase.table("clothes").select("*").eq("id", cloth_id).execute()
        if not response.data:
            return "해당 옷 정보를 찾을 수 없습니다.", 404
        cloth = response.data[0]
        return render_template('clothes_detail.html', cloth=cloth)
    except Exception as e:
        print(f"Error: {e}")
        return "데이터를 불러오는 중 오류가 발생했습니다.", 500

# 모바일 웹 앱 컴포넌트 호출용 단일 의류 메타 갱신 API 라우터
@app.route('/api/clothes/update/<int:cloth_id>', methods=['POST'])
def update_cloth_api(cloth_id):
    if 'user_email' not in session and 'login_id' not in session: return jsonify({"error": "로그인이 필요합니다."}), 401
    data = request.get_json()
    tpo = data.get('tpo') 
    season = data.get('season')
    try:
        if not supabase: return jsonify({"error": "데이터베이스가 연결되어 있지 않습니다."}), 500
        response = supabase.table("clothes").update({
            "name": data.get('name'), "main_category": data.get('main_category'), "sub_category": data.get('sub_category'),
            "color": data.get('color'), "season": season, "style": [tpo] if tpo else []
        }).eq("id", cloth_id).execute()
        return jsonify({"message": "수정 성공", "data": response.data}), 200
    except Exception as e: return jsonify({"error": f"수정 실패: {str(e)}"}), 500

# 의류 영구 파기 소멸 처리 가동 API 라우터
@app.route('/api/clothes/delete/<int:cloth_id>', methods=['POST'])
def delete_cloth_api(cloth_id):
    if 'user_email' not in session and 'login_id' not in session: return jsonify({"error": "로그인이 필요합니다."}), 401
    try:
        if supabase: supabase.table("clothes").delete().eq("id", cloth_id).execute()
        return jsonify({"message": "삭제 성공"}), 200
    except Exception as e: return jsonify({"error": f"삭제 실패: {str(e)}"}), 500

# 동기 웹 폼 양식 스펙 변경 요청 수신 대응 라우터
@app.route('/update_clothes', methods=['POST'])
def update_clothes():
    user_email = session.get('user_email')
    if not user_email:
        flash("로그인이 필요합니다.")
        return redirect(url_for('login_page')) 
    cloth_id = request.form.get('cloth_id')
    if not cloth_id:
        flash("잘못된 접근입니다. (옷 ID 누락)")
        return redirect(url_for('my_closet'))
    styles_str = request.form.get('styles', '')
    edit_data = {
        'name': request.form.get('cloth_name'),
        'main_category': request.form.get('main_category'),
        'sub_category': request.form.get('sub_category'),
        'fit': request.form.get('fit'),
        'color': request.form.get('cloth_color'),
        'temp_level': int(request.form.get('temp_level', 5)),
        'style': styles_str.split(',') if styles_str else [] 
    }
    result = update_closet_cloth(cloth_id, user_email, edit_data)
    if result:
        flash("옷 정보가 성공적으로 수정되었습니다.")
        return redirect(url_for('my_closet')) 
    else:
        flash("옷 정보 수정에 실패했습니다.")
        return redirect(url_for('my_closet')) 

# 동기 웹 폼 버튼 트리거 대응 의류 영구 삭제 라우터
@app.route('/delete_clothes', methods=['POST'])
def delete_clothes():
    user_email = session.get('user_email')
    if not user_email:
        flash("로그인이 필요합니다.")
        return redirect(url_for('login_page'))
    cloth_id = request.form.get('cloth_id')
    if not cloth_id:
        flash("잘못된 접근입니다.")
        return redirect(url_for('my_closet'))
    success = delete_closet_cloth(cloth_id, user_email)
    if success:
        flash("옷이 성공적으로 삭제되었습니다.")
    else:
        flash("삭제에 실패했거나 권한이 없습니다.")
    return redirect(url_for('my_closet'))

# 비정식 가의류 분석 정보 보정 내용 확인 및 검증 승인 API 라우터
@app.route('/api/clothes/confirm', methods=['POST'])
def confirm_clothes():
    data = request.json
    cloth_id = data.get('cloth_id')
    user_email = data.get('user_email')
    modified_data = data.get('modified_data')

    if not cloth_id or not user_email or not modified_data:
        return jsonify({"error": "데이터 누락"}), 400
    
    style_data = modified_data.get('style')
    if isinstance(style_data, str):
        modified_data['style'] = [s.strip() for s in style_data.split(',')] if style_data else []

    modified_data['is_verified'] = True
    result = modify_and_confirm_ai_analysis(cloth_id, user_email, modified_data)
    
    if result is not None:
        return jsonify({"message": "완료"}), 200
    else:
        return jsonify({"error": "DB 업데이트 대상 없음"}), 500
    

# 미승인 가의류 보관 레코드를 전면 취소 및 데이터 파기 처리하는 API 라우터
@app.route('/api/clothes/cancel', methods=['POST'])
def cancel_clothes():
    try:
        data = request.json
        cloth_id = data.get('cloth_id')
        user_email = data.get('user_email')
        
        if not cloth_id or not user_email:
            return jsonify({"error": "데이터가 부족합니다."}), 400
            
        result = delete_unverified_cloth(cloth_id, user_email)
        if result is not None:
            print(f"[서버 로그] 의류 삭제 성공: {cloth_id}")
            return jsonify({"message": "미승인 의류 데이터 삭제 완료"}), 200
        else:
            return jsonify({"error": "삭제 실패: 해당 ID의 데이터가 없거나 이미 승인되었습니다."}), 404
    except Exception as e:
        print(f"[서버 에러] cancel_clothes 내부 오류: {str(e)}")
        return jsonify({"error": f"서버 오류 발생: {str(e)}"}), 500
    
# 내 즐겨찾기 스크랩북 개인화 룩북 페이지 보관함 이동 라우터
@app.route('/my_scrap')
def my_scrap():
    user_email = session.get('user_email')
    if not user_email: return redirect(url_for('login'))
    
    result = get_user_scraps_with_details(user_email) if get_user_scraps_with_details else {"scraps": []}
    scraps_list = result.get("scraps", []) if result.get("success") else []
    return render_template('my_scrap.html', user_email=user_email, scraps=scraps_list)

# 마이 룩북 그리드 리스트 내 보관 코디 제거 파기 API 라우터
@app.route('/api/scraps/delete/<int:scrap_id>', methods=['POST'])
def api_delete_scrap(scrap_id):
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({"error": "로그인이 필요합니다."}), 401

    result = delete_scrap_from_db(scrap_id, user_email)
    if result.get("success"):
        return jsonify({"message": result.get("message")}), 200
    else:
        return jsonify({"error": result.get("error")}), 400

# 회원 본인의 기본 인적 사항 마이페이지 룩북 프로필 조회 라우터
@app.route('/my_profile')
def my_profile():
    user_email = session.get('user_email')
    login_id = session.get('login_id')
    if not user_email: 
        return redirect(url_for('login'))
    
    user_info = fetch_user_profile(login_id)
    return render_template('my_profile.html', logged_in=True, user_email=user_email, users=user_info or {}) 

# 사용자 지정 닉네임 및 기본 세부 이메일 정보 변경 보정 API 라우터
@app.route('/api/update_user_info', methods=['POST'])
def update_user_info_api():
    login_id = session.get('login_id')
    data = request.json
    
    print("\n==================================")
    print(f"🛠️ [디버그] 업데이트 시도")
    print(f" - 세션 login_id: {login_id} (타입: {type(login_id)})")
    print(f" - 전달받은 데이터: {data}")
    print("==================================\n")
    
    if not login_id:
        return jsonify({"status": "fail", "message": "서버에 로그인 세션이 없습니다. 다시 로그인해주세요."}), 401
    
    try:
        response = supabase.table("users").update({
            "nickname": data.get('nickname'), "email": data.get('email'), "name": data.get('name')
        }).eq("login_id", login_id).execute()
        
        print(f"✅ [디버그] DB 업데이트 성공 결과: {response}")
        return jsonify({"status": "success", "message": "수정 완료"}), 200
    except Exception as e:
        print("\n❌ [디버그] 치명적 에러 발생!")
        traceback.print_exc() 
        return jsonify({"status": "fail", "message": "DB 통신 중 오류가 발생했습니다."}), 500

# 가입 폼 내 주소 중복성 유무 체크 제어 API 라우터
@app.route('/api/check-email', methods=['POST'])
def check_email():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({"error": "이메일을 입력해주세요."}), 400
        
    try:
        from services.auth import check_email_duplicate
        if check_email_duplicate(email):
            return jsonify({"message": f"'{email}'은 사용 가능한 이메일입니다."}), 200
        else:
            return jsonify({"error": "이미 사용 중이거나 유효하지 않은 이메일입니다."}), 400
    except Exception as e:
        print(f"이메일 중복 확인 에러: {e}")
        return jsonify({"error": "서버 통신 중 오류가 발생했습니다."}), 500

# 마이페이지 내 닉네임 중복 유무 실시간 체크 제어 API 라우터
@app.route('/api/check-nickname', methods=['POST'])
def check_nickname():
    data = request.get_json()
    nickname = data.get('nickname')
    if not nickname:
        return jsonify({"error": "닉네임을 입력해주세요."}), 400
        
    try:
        from services.auth import check_nickname_duplicate
        if check_nickname_duplicate(nickname):
            return jsonify({"message": f"'{nickname}'은(는) 사용 가능한 닉네임입니다."}), 200
        else:
            return jsonify({"error": "이미 사용 중인 닉네임입니다."}), 400
    except Exception as e:
        print(f"닉네임 중복 확인 에러: {e}")
        return jsonify({"error": "서버 통신 중 오류가 발생했습니다."}), 500
        
# 구버전 전용 연동 갱신 우회 지원 API 라우터
@app.route('/api/update-user-info', methods=['POST'])
def update_user_info():
    data = request.get_json()
    return jsonify({"message": "수정이 완료되었습니다."})

# 유저 신장, 체중, 3대 체형 정보를 계정에 연동 및 갱신하는 API 라우터
@app.route('/api/update_body_info', methods=['POST'])
def update_body_info():
    login_id = session.get('login_id')
    if not login_id:
        return jsonify({"status": "error", "message": "로그인이 필요합니다."}), 401

    data = request.get_json()
    input_data = {
        "height": data.get('height'), "weight": data.get('weight'), "body_shape": data.get('bodyType') 
    }

    clean_data = _filter_body_profile_data(input_data)
    if not clean_data:
        return jsonify({"status": "error", "message": "입력한 데이터가 유효한 형식이 아닙니다."}), 400

    try:
        response = supabase.table('users').update(clean_data).eq('login_id', login_id).execute()
        return jsonify({"status": "success", "message": "체형 정보가 성공적으로 저장되었습니다."})
    except Exception as e:
        print(f"[DB 에러] 체형 정보 업데이트 실패: {e}")
        return jsonify({"status": "error", "message": "서버 오류로 저장에 실패했습니다."}), 500

# 프로필 편집 진입 전 기존 비밀번호 일치 유무를 검증하는 API 라우터
@app.route('/api/verify_password', methods=['POST'])
def verify_password_api():
    data = request.json
    input_pw = data.get('password')
    login_id = session.get('login_id')
    if not login_id:
        return jsonify({"status": "fail", "message": "로그인 세션이 만료되었습니다."}), 401

    try:
        from services.userprofile import _verify_current_password
        if _verify_current_password(login_id, input_pw):
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "fail", "message": "비밀번호가 일치하지 않습니다."}), 400
    except Exception as e:
        return jsonify({"status": "fail", "message": "서버 검증 중 오류가 발생했습니다."}), 500
    
# 가입 단계에서 사용자가 입력한 중복 아이디 존재 여부를 가리는 API 라우터
@app.route('/api/check-id', methods=['POST'])
def check_id():
    data = request.get_json()
    login_id = data.get('login_id') or data.get('username')
    if not login_id:
        return jsonify({"error": "아이디를 입력해주세요."}), 400
        
    try:
        from services.auth import check_login_id_duplicate
        if check_login_id_duplicate(login_id):
            return jsonify({"message": "사용 가능한 아이디입니다."}), 200
        else:
            return jsonify({"error": "이미 사용 중이거나 유효하지 않은 아이디입니다."}), 400
    except Exception as e:
        print(f"아이디 중복 확인 에러: {e}")
        return jsonify({"error": "서버 통신 중 오류가 발생했습니다."}), 500
    
# 메인 파일로 로컬 터미널 단독 실행되었을 때 Flask 내장 백서버를 띄우는 조건문
if __name__ == '__main__':
    print("\n🚀 패션 앱 서버 웹 서비스 구동 중...")
    app.run(host='0.0.0.0', port=5000, debug=True)
