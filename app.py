import os
import sys
import logging
import traceback
import random
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, make_response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from services.userprofile import update_account_password, change_profile_password
from auth_service import sign_up_user, login_user, get_email_by_login_id

# 경로 설정을 최상단에서 진행
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app, supports_credentials=True)
app.secret_key = "my_fashion_app_secret_1234"

# 세션 유지 및 전역 변수 설정
@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=30)

@app.context_processor
def inject_user():
    is_logged_in = 'user_email' in session or 'login_id' in session
    return dict(logged_in=is_logged_in)


# --- [서비스 모듈 안전 임포트 구조 및 가드] ---
supabase = None
fetch_weather_forecast = None
process_user_upload = None
recommend_clothes_logic = None

request_find_id = None
verify_and_get_login_id = None
request_find_password = None
verify_password_reset_code = None
reset_password_and_auto_login = None

try:
    from config import supabase
    print("✅ Supabase 임포트 성공")
except Exception as e:
    print(f"❌ config.py (Supabase) 로드 오류: {e}")

try:
    from weather_service import fetch_weather_forecast
    print("✅ 날씨 서비스 임포트 성공")
except Exception as e:
    print(f"❌ weather_service.py 로드 오류: {e}")

try:
    from auth_service import sign_up_user, login_user
    from services.imgproc import process_user_upload, modify_and_confirm_ai_analysis, delete_unverified_cloth
    from services.recommend_clothes import recommend_clothes_logic
    print("✅ AI 이미지 분석 및 추천 핵심 모듈 최고 제어권 확보 완료")
except Exception as e:
    print(f"⚠️ External module load check needed: {e}")

try:
    from services.account_recovery import (
        request_find_id, 
        verify_and_get_login_id, 
        request_find_password, 
        verify_password_reset_code, 
        reset_password_and_auto_login
    )
    print("✅ 계정 복구 알고리즘 모듈 임포트 성공")
except Exception as e:
    print(f"❌ account_recovery.py 로드 오류: {e}")


# 업로드 폴더 설정
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# --- [날씨 API 캐싱 레이어 시스템] ---
WEATHER_CACHE = {
    "data": None,
    "last_updated": None
}

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


# =============================================================
# ⭐ [아이디 / 비밀번호 찾기 API 라우터 통신 레이어] 
# =============================================================
# (기존 코드 유지)
@app.route('/api/find-id/request', methods=['POST'])
def api_request_find_id():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    if not request_find_id: return jsonify({"success": False, "error": "모듈이 로드되지 않았습니다."}), 500
    if request_find_id(name, email): return jsonify({"success": True, "message": "입력하신 이메일로 4자리 인증번호가 발송되었습니다."}), 200
    return jsonify({"success": False, "error": "등록되지 않은 이름이거나 이메일 주소입니다."}), 400

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

@app.route('/api/find-pw/request', methods=['POST'])
def api_request_find_pw():
    data = request.get_json()
    name = data.get('name')
    login_id = data.get('login_id')
    email = data.get('email')
    if not request_find_password: return jsonify({"success": False, "error": "모듈이 로드되지 않았습니다."}), 500
    if request_find_password(name, login_id, email): return jsonify({"success": True, "message": "본인 확인 성공! 이메일로 인증번호가 발송되었습니다."}), 200
    return jsonify({"success": False, "error": "입력하신 3가지 회원 정보가 일치하지 않습니다."}), 400

@app.route('/api/find-pw/verify', methods=['POST'])
def api_verify_find_pw():
    data = request.get_json()
    email = data.get('email')
    code = data.get('code')
    if not verify_password_reset_code: return jsonify({"success": False, "error": "모듈이 로드되지 않았습니다."}), 500
    if verify_password_reset_code(email, code): return jsonify({"success": True, "message": "본인 인증이 완료되었습니다. 새 비밀번호를 설정해 주세요."}), 200
    return jsonify({"success": False, "error": "인증번호가 일치하지 않습니다."}), 400

@app.route('/api/find-pw/reset', methods=['POST'])
def api_reset_pw():
    data = request.get_json()
    login_id = data.get('login_id')
    new_pw = data.get('new_pw')
    new_pw_confirm = data.get('new_pw_confirm')
    if not reset_password_and_auto_login: return jsonify({"success": False, "error": "모듈이 로드되지 않았습니다."}), 500
    login_result = reset_password_and_auto_login(login_id, new_pw, new_pw_confirm)
    if login_result:
        session['login_id'] = login_id
        session['user_email'] = get_email_by_login_id(login_id)
        return jsonify({"success": True, "message": "비밀번호가 성공적으로 변경되었으며 자동 로그인 처리되었습니다!"}), 200
    return jsonify({"success": False, "error": "비밀번호 무결성 검증 규칙을 위반했거나 세션 발급에 실패했습니다."}), 400


# --- [기본 페이지 라우트 설정] ---
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

@app.route('/home')
def home_page(): 
    is_logged_in = 'user_email' in session or 'login_id' in session
    user_email = session.get('user_email')
    if not user_email: return redirect(url_for('login'))
    raw_weather = fetch_weather()
    current_weather = raw_weather[0] if raw_weather and isinstance(raw_weather, list) and len(raw_weather) > 0 else None
    return render_template('home.html', weather=current_weather, user_email=user_email, logged_in=is_logged_in)

@app.route('/weather_detail')
def weather_detail():
    is_logged_in = 'user_email' in session or 'login_id' in session
    try: raw_data = fetch_weather()
    except Exception as e:
        print(f"❌ 날씨 가져오기 치명적 오류: {e}")
        raw_data = None
    hourly_data = []
    start_time = datetime.now()
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

@app.route('/login', methods=['GET', 'POST']) 
def login():
    if request.method == 'GET': return render_template('login.html')
    if request.method == 'POST':
        data = request.get_json()
        login_id = data.get('login_id')
        password = data.get('password')
        is_success = login_user(login_id, password) if login_user else False
        if is_success:
            session['login_id'] = login_id
            session['user_email'] = get_email_by_login_id(login_id)
            return jsonify({"message": "로그인 성공"}), 200
        else:
            return jsonify({"error": "아이디 또는 비밀번호가 틀렸습니다."}), 401

@app.route('/register') 
def register_page():
    return render_template('sign_up.html')

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
    if not email or not password or not username: return jsonify({"error": "필수 정보를 모두 입력해주세요."}), 400
    try:
        success = sign_up_user(email, password, nickname, username, name, gender)
        if success: return jsonify({"message": "회원가입 성공!"}), 201
        else: return jsonify({"error": "DB 저장 실패"}), 400
    except Exception as e:
        print(f"서버 에러: {e}")
        return jsonify({"error": str(e)}), 500

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
        # 1. DB에서 현재 유저의 기존 비밀번호(pw) 가져오기
        user_data = supabase.table("users").select("pw").eq("login_id", login_id).execute()
        
        if not user_data.data:
            return jsonify({"status": "fail", "message": "회원 정보를 찾을 수 없습니다."}), 404
            
        # DB에서 가져온 기존 비밀번호 추출
        db_password = user_data.data[0].get("pw")
        
        # 2. 사용자가 입력한 '기존 비밀번호'가 실제 DB와 일치하는지 확인
        if db_password != current_pw:
            return jsonify({"status": "fail", "message": "기존 비밀번호가 올바르지 않습니다."}), 400
            
        # 3. 새 비밀번호(pw)로 업데이트 실행
        update_response = supabase.table("users").update({
            "pw": new_pw  # 🔥 실제 DB 컬럼명인 pw로 완벽히 일치시킴
        }).eq("login_id", login_id).execute()
        
        if not update_response.data:
            return jsonify({"status": "fail", "message": "비밀번호 업데이트에 실패했습니다."}), 400
            
        print(f"✅ [디버그] 비밀번호 변경 성공")
        return jsonify({"status": "success", "message": "비밀번호가 성공적으로 변경되었습니다."}), 200
        
    except Exception as e:
        print("\n❌ [디버그] 비밀번호 변경 중 에러 발생!")
        traceback.print_exc()
        return jsonify({"status": "fail", "message": "서버 DB 통신 중 오류가 발생했습니다."}), 500
    
@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('home')) 


# =============================================================
# ⭐ [의류 등록 파이프라인 엔진 통합 레이어]
# =============================================================

# 1) 직접 입력 방식 등록 처리 라우트
@app.route('/add_clothes', methods=['GET', 'POST'])
def add_clothes():
    if 'user_email' not in session and 'login_id' not in session: return redirect(url_for('login'))
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
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            if process_user_upload:
                upload_res = process_user_upload(file_path, user_email)
                if upload_res and 'image_path' in upload_res:
                    storage_url = upload_res['image_path']
            if os.path.exists(file_path): os.remove(file_path)

        insert_payload = {
            "user_email": user_email,
            "name": cloth_name,
            "main_category": main_category,
            "sub_category": sub_category,
            "color": cloth_color,
            "style": styles.split(',') if styles else [],
            "temp_level": int(temp_level),
            "image_url": storage_url,
            "is_verified": True
        }
        if supabase: supabase.table("clothes").insert(insert_payload).execute()
        return redirect(url_for('my_closet'))

    return render_template('add_clothes.html')


# 2) AI 사진 등록 페이지 라우트
@app.route('/add_clothes_photo')
def add_clothes_photo():
    if 'user_email' not in session and 'login_id' not in session: return redirect(url_for('login'))
    return render_template('add_clothes_photo.html')


# 3) AI 사진 비동기/동기 분석 요청 라우트
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
        result = process_user_upload(file_path, user_email) # DB 임시저장(is_verified=False) 완료됨
        
        # 💡 [핵심 수정] return을 만나기 전에 무조건 임시 파일을 먼저 삭제합니다!
        if os.path.exists(file_path): 
            os.remove(file_path)
            
        if result:
            # ✅ [수정 완료] 중복 저장(insert) 제거. imgproc.py가 넘겨준 딕셔너리를 그대로 사용합니다.
            results_payload = {
                "id": result.get('id'),
                "image_path": result.get('image_url'), # imgproc.py의 반환 키에 맞춤
                "detected_name": result.get('name', 'AI 추출 의류 명칭'),
                "detected_main": result.get('main_category', '상의'),
                "detected_sub": result.get('sub_category', '이너'),
                "detected_color": result.get('color', '#ffffff'),
                "detected_tags": result.get('style', [])
            }
            return render_template('add_clothes_photo_detail.html', results=results_payload, user_email=user_email)
            
    # process_user_upload 로드에 실패했거나, result 분석 결과가 실패(None)했을 때만 여기까지 도달함
    return "AI 의상 인프라 분석 오류 발생", 500


# 4) AI 분석 결과 조절 후 최종 확정 저장 API 라우트
@app.route('/save-closet-item', methods=['POST'])
def save_clothes(): # ✅ [수정 완료] HTML의 action="{{ url_for('save_clothes') }}"와 맞춤
    if 'user_email' not in session and 'login_id' not in session: 
        return redirect(url_for('login'))
        
    cloth_id = request.form.get('cloth_id')  
    
    # ✅ [수정 완료] HTML 폼의 name 속성과 완벽 일치하도록 키 값 수정
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
        "is_verified": True # 사용자가 확인했으므로 정식 옷장으로 편입!
    }

    if supabase and cloth_id:
        supabase.table("clothes").update(update_payload).eq("id", cloth_id).execute()
        
    return redirect(url_for('my_closet'))


# --- [코디 및 가이드 핵심 라우터 레이어] ---
# (기존 코드 유지)
@app.route('/api/recommend')
def recommend():
    try:
        weather_data = fetch_weather()
        if isinstance(weather_data, list) and len(weather_data) > 0: temp = weather_data[0].get("temp", 20)
        else: temp = 20
        target_tpo = request.args.get('tpo', '캐주얼')
        user_email = session.get('user_email')
        if not user_email: return jsonify({"error": "로그인이 필요합니다."}), 401
        user_clothes = []
        if supabase:
            response = supabase.table("clothes").select("*").eq("user_email", user_email).execute()
            user_clothes = response.data
        top_5_outfits = []
        try:
            top_5_outfits = recommend_clothes_logic(temp, target_tpo, user_clothes) if recommend_clothes_logic else []
        except KeyError:
            from services.recommend_clothes import get_target_level, calculate_style_score, calculate_color_score
            target_lv = get_target_level(temp)
            valid_bottoms = [c for c in user_clothes if c.get('main_category') == '하의' and abs(c['temp_level'] - target_lv) <= 1]
            inners = [c for c in user_clothes if c.get('main_category') == '상의' and c.get('sub_category') == '이너']
            outers = [c for c in user_clothes if c.get('main_category') == '상의' and c.get('sub_category') == '아우터']
            valid_top_combos = []
            for inner in inners:
                if abs(inner['temp_level'] - target_lv) <= 1: valid_top_combos.append([inner])
                for outer in outers:
                    if abs((inner['temp_level'] + outer['temp_level']) - target_lv) <= 2:
                        valid_top_combos.append([inner, outer])
            outfits_backup = []
            for top_combo in valid_top_combos:
                for bottom in valid_bottoms:
                    full_outfit = top_combo + [bottom]
                    style_score = calculate_style_score(full_outfit, target_tpo)
                    color_score = calculate_color_score(top_combo, bottom, target_lv)
                    total_score = round(style_score + color_score, 2)
                    outfits_backup.append({"top_combo": top_combo, "bottom": bottom, "total_score": total_score, "style_score": style_score, "color_score": color_score})
            top_5_outfits = sorted(outfits_backup, key=lambda x: x['total_score'], reverse=True)[:5]
        return jsonify({"current_temp": temp, "target_tpo": target_tpo, "recommendations": top_5_outfits})
    except Exception as e:
        print(f"❌ 추천 가드 오류 확인: {e}")
        return jsonify({"current_temp": 20, "target_tpo": "캐주얼", "recommendations": []})

@app.route('/guide')
def guide_main(): 
    user_email = session.get('user_email')
    return render_template('guide.html', user_email=user_email)

@app.route('/guide/dictionary')
def guide_dictionary():
    try: return render_template('guide_dictionary.html')
    except Exception: return "<h3>기본 패션 아이템 도감 페이지 준비 중입니다!</h3><br><a href='/guide'>가이드로 돌아가기</a>"

@app.route('/body_guide')
def body_guide():
    try:
        is_logged_in = 'user_email' in session or 'login_id' in session
        user_email = session.get('user_email')
        return render_template('body_guide.html', logged_in=is_logged_in, user_email=user_email)
    except Exception as e:
        return "<h3>체형별 가이드 페이지 준비 중입니다!</h3><br><a href='/guide'>가이드로 돌아가기</a>"

@app.route('/codi')
def codi_page():
    is_logged_in = 'user_email' in session or 'login_id' in session
    user_email = session.get('user_email')
    return render_template('codi.html', logged_in=is_logged_in, user_email=user_email)

@app.route('/tpo_guide')
def tpo_guide():
    try:
        is_logged_in = 'user_email' in session or 'login_id' in session
        user_email = session.get('user_email')
        return render_template('tpo_guide.html', logged_in=is_logged_in, user_email=user_email)
    except Exception:
        return "<h3>TPO 가이드 페이지 준비 중입니다!</h3><br><a href='/guide'>가이드로 돌아가기</a>"
        
@app.route('/color_guide')
def color_guide():
    try:
        is_logged_in = 'user_email' in session or 'login_id' in session
        user_email = session.get('user_email')
        return render_template('color_guide.html', logged_in=is_logged_in, user_email=user_email)
    except Exception as e:
        return "<h3>컬러 매칭 가이드 페이지 준비 중입니다!</h3><br><a href='/guide'>가이드로 돌아가기</a>"

# --- [옷장 리스트 및 수정/삭제 상세 정보 레이어] ---
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

@app.route('/clothes_detail/<int:cloth_id>')
def clothes_detail(cloth_id):
    if 'user_email' not in session and 'login_id' not in session: return redirect(url_for('login'))
    cloth_data = None
    try:
        if supabase:
            response = supabase.table("clothes").select("*").eq("id", cloth_id).execute()
            cloth_data = response.data[0] if response.data else None
    except Exception as e: print(f"❌ 옷 상세 데이터 조회 실패: {e}")
    return render_template('clothes_detail.html', cloth=cloth_data)

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

@app.route('/api/clothes/delete/<int:cloth_id>', methods=['POST'])
def delete_cloth_api(cloth_id):
    if 'user_email' not in session and 'login_id' not in session: return jsonify({"error": "로그인이 필요합니다."}), 401
    try:
        if supabase: supabase.table("clothes").delete().eq("id", cloth_id).execute()
        return jsonify({"message": "삭제 성공"}), 200
    except Exception as e: return jsonify({"error": f"삭제 실패: {str(e)}"}), 500

# 수정된 라우트
@app.route('/api/clothes/confirm', methods=['POST'])
def confirm_clothes():
    data = request.json
    cloth_id = data.get('cloth_id')
    user_email = data.get('user_email')
    modified_data = data.get('modified_data')

    if not cloth_id or not user_email or not modified_data:
        return jsonify({"error": "데이터 누락"}), 400

    # [핵심 수정] style 필드가 문자열이면 리스트로 변환
    style_data = modified_data.get('style')
    if isinstance(style_data, str):
        # 콤마로 구분된 문자열을 리스트로 변환 (빈 문자열이면 빈 리스트)
        modified_data['style'] = [s.strip() for s in style_data.split(',')] if style_data else []
    
    modified_data['is_verified'] = True
    
    # DB 업데이트 시도
    result = modify_and_confirm_ai_analysis(cloth_id, user_email, modified_data)
    
    if result is not None:
        return jsonify({"message": "완료"}), 200
    else:
        return jsonify({"error": "DB 업데이트 대상 없음"}), 500
    

@app.route('/api/clothes/cancel', methods=['POST'])
def cancel_clothes():
    try:
        data = request.json
        cloth_id = data.get('cloth_id')
        user_email = data.get('user_email')
        
        if not cloth_id or not user_email:
            return jsonify({"error": "데이터가 부족합니다."}), 400
            
        # 미승인 데이터 삭제 함수 호출
        result = delete_unverified_cloth(cloth_id, user_email)
        
        # result가 삭제된 데이터가 있음을 나타내는지 확인
        if result is not None:
            print(f"[서버 로그] 의류 삭제 성공: {cloth_id}")
            return jsonify({"message": "미승인 의류 데이터 삭제 완료"}), 200
        else:
            return jsonify({"error": "삭제 실패: 해당 ID의 데이터가 없거나 이미 승인되었습니다."}), 404
            
    except Exception as e:
        print(f"[서버 에러] cancel_clothes 내부 오류: {str(e)}")
        return jsonify({"error": f"서버 오류 발생: {str(e)}"}), 500
    
@app.route('/my_scrap')
def my_scrap():
    is_logged_in = 'user_email' in session or 'login_id' in session
    user_email = session.get('user_email')
    return render_template('my_scrap.html', logged_in=is_logged_in, user_email=user_email)

@app.route('/my_profile')
def my_profile():
    user_email = session.get('user_email')
    if not user_email: return redirect(url_for('login'))
    is_logged_in = 'user_email' in session or 'login_id' in session
    return render_template('my_profile.html', logged_in=is_logged_in, user_email=user_email)

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
            "nickname": data.get('nickname'),
            "email": data.get('email'),
            "name": data.get('name')
        }).eq("login_id", login_id).execute()
        
        print(f"✅ [디버그] DB 업데이트 성공 결과: {response}")
        return jsonify({"status": "success", "message": "수정 완료"}), 200
        
    except Exception as e:
        print("\n❌ [디버그] 치명적 에러 발생!")
        traceback.print_exc() # 에러가 발생한 정확한 원인을 터미널에 붉은 글로 띄워줍니다.
        return jsonify({"status": "fail", "message": "DB 통신 중 오류가 발생했습니다."}), 500
    
@app.route('/api/check-nickname', methods=['POST'])
def check_nickname():
    data = request.get_json()
    nickname = data.get('nickname')
  
    return jsonify({"message": "사용 가능한 닉네임입니다."}) 

@app.route('/api/check-email', methods=['POST'])
def check_email():
    data = request.get_json()
    email = data.get('email')

    return jsonify({"message": f"'{email}'은 사용 가능한 이메일입니다."})
@app.route('/api/update-user-info', methods=['POST'])
def update_user_info():
    data = request.get_json()
    # Supabase update 로직
    return jsonify({"message": "수정이 완료되었습니다."})

@app.route('/api/update_body_info', methods=['POST'])
def update_body_info_api():
    login_id = session.get('login_id')
    data = request.json
    
    print("\n==================================")
    print(f"🏋️ [디버그] 체형정보 업데이트 시도")
    print(f" - 세션 login_id: {login_id}")
    print(f" - 전달받은 데이터: {data}")
    print("==================================\n")
    
    # 1. 세션 검증 (로그인 안 된 사용자 차단)
    if not login_id:
        return jsonify({"status": "fail", "message": "서버에 로그인 세션이 없습니다. 다시 로그인해주세요."}), 401
    
    try:
        # 2. 데이터 안전 변환 (값이 있으면 정수형으로 변환, 없으면 None 처리)
        height_val = int(data.get('height')) if data.get('height') else None
        weight_val = int(data.get('weight')) if data.get('weight') else None
        
        # 3. Supabase DB 업데이트 쿼리 실행
        response = supabase.table("users").update({
            "height": height_val,
            "weight": weight_val,
            "body_shape": data.get('bodyType')  # 핵심 수정: DB 컬럼명(body_shape)에 정확히 매핑
        }).eq("login_id", login_id).execute()
        
        # 4. 방어 로직: Supabase가 빈 데이터를 반환했는지 검사 (Silent Failure 감지)
        if not response.data:
            print("⚠️ [디버그] DB에 해당 login_id를 가진 유저가 없어 업데이트가 무시되었습니다.")
            return jsonify({"status": "fail", "message": "회원 정보를 찾을 수 없어 저장에 실패했습니다."}), 400
        
        # 5. 정상 저장 완료
        print(f"✅ [디버그] 체형 DB 업데이트 성공: {response.data}")
        return jsonify({"status": "success", "message": "체형 정보가 정상적으로 저장되었습니다."}), 200
        
    except ValueError:
        # 키나 몸무게에 숫자가 아닌 값("abc" 등)이 들어와 int() 변환 중 에러가 날 경우
        return jsonify({"status": "fail", "message": "키와 몸무게는 숫자만 입력 가능합니다."}), 400
        
    except Exception as e:
        print("\n❌ [디버그] 체형 DB 업데이트 치명적 에러 발생!")
        traceback.print_exc() 
        return jsonify({"status": "fail", "message": "DB 통신 중 서버 내부 오류가 발생했습니다."}), 500
    
@app.route('/api/verify_password', methods=['POST'])
def verify_password_api():
    """비밀번호 검증 API"""
    data = request.json
    input_pw = data.get('password')
    user_email = session.get('user_email')

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    print("\n🚀 패션 앱 서버 웹 서비스 구동 중...")
    app.run(host='0.0.0.0', port=5000, debug=True)