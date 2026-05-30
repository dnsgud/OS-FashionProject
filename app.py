import os
import sys
import logging
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from services import userprofile
from services.userprofile import update_account_password, change_profile_password


# 경로 설정을 최상단에서 진행
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


# --- [서비스 모듈 안전 임포트 구조 및 가드] ---
supabase = None
fetch_weather_forecast = None
sign_up_user = None
login_user = None
process_user_upload = None
recommend_clothes_logic = None

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
    from services.imgproc import process_user_upload
    from services.recommend_clothes import recommend_clothes_logic
    print("✅ AI 이미지 분석 및 추천 핵심 모듈 최고 제어권 확보 완료")
except Exception as e:
    print(f"⚠️ 외부 서비스 파일 로드 해제 체크 필요: {e}")


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
    
    # 캐시 유효 시간: 10분
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


# --- [라우트 설정] ---
   
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
    is_logged_in = 'user_email' in session
    user_email = session.get('user_email')
    
    if not user_email:
        return redirect(url_for('login'))

    raw_weather = fetch_weather()
    current_weather = raw_weather[0] if raw_weather and isinstance(raw_weather, list) and len(raw_weather) > 0 else None

    return render_template('home.html',
                           weather=current_weather,
                           user_email=user_email,
                           logged_in=is_logged_in)

@app.route('/weather_detail')
def weather_detail():
    is_logged_in = 'user_email' in session
    
    try:
        raw_data = fetch_weather()
    except Exception as e:
        print(f"❌ 날씨 가져오기 치명적 오류: {e}")
        raw_data = None

    hourly_data = []
    start_time = datetime.now()

    # 데이터가 정상적인 리스트 형태이고 내부에 요소가 있을 때만 실행
    if raw_data and isinstance(raw_data, list) and len(raw_data) > 0:
        for idx, data in enumerate(raw_data):
            # 안전장치: 내부 요소가 딕셔너리가 아니라면 강제 변환하거나 방어 처리
            if not isinstance(data, dict):
                continue
                
            target_time = start_time + timedelta(hours=idx * 3)
            am_pm = "오전" if target_time.hour < 12 else "오후"
            display_hour = target_time.hour % 12
            display_hour = 12 if display_hour == 0 else display_hour
            
            wind_speed = data.get('wind_speed', 0)
            wind_status = "약함" if wind_speed < 3.4 else "보통" if wind_speed < 8.0 else "강함"

            hourly_data.append({
                "time": f"{am_pm} {display_hour}시", 
                "temp": data.get('temp', '--'),
                "icon": data.get('icon', 'fa-cloud'),
                "status": data.get('status', '맑음'),  # 💡 필수 누락 키 방어 추가
                "humidity": data.get('humidity', 0),
                "wind_speed": wind_speed,
                "wind_status": wind_status
            })

    # 만약 위의 루프를 돌았음에도 hourly_data가 비어있다면, 
    # HTML의 {% else %} 문이 작동할 수 있도록 아예 '빈 리스트'로 넘겨줍니다.
    if not hourly_data:
        hourly_data = []

    return render_template('weather_detail.html', hourly_data=hourly_data, logged_in=is_logged_in)

@app.route('/login', methods=['GET', 'POST']) 
def login():
    if request.method == 'GET':
        return render_template('login.html')

    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        is_success = login_user(email, password) if login_user else False

        if is_success:
            session['user_email'] = email
            return jsonify({"message": "로그인 성공"}), 200
        else:
            return jsonify({"error": "로그인 실패"}), 401

@app.route('/register') 
def register_page():
    return render_template('sign_up.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    nickname = data.get('nickname', '익명')  
    name = data.get('name', '이름 없음')         
    username = data.get('username', '')        
    gender = data.get('gender', '미선택')    

    if not email or not password:
        return jsonify({"error": "이메일과 비밀번호를 입력해주세요."}), 400

    success = False
    if sign_up_user:
        try:
            # 새로 추가된 이름(name)과 아이디(username)를 포함하여 회원가입 시도
            success = sign_up_user(email=email, password=password, nickname=nickname, gender=gender, name=name, username=username)
        except TypeError:
            # 만약 auth_service.py 내부 함수가 아직 옛날 규격(인자 4개)이라면 튕기지 않고 이전 버전으로 가입 처리
            success = sign_up_user(email, password, nickname, gender)

    if success:
        return jsonify({"message": "회원가입 성공!"}), 201
    else:
        return jsonify({"error": "회원가입에 실패했습니다."}), 400
    
@app.route('/api/update_password', methods=['POST'])
def update_password_api():
    data = request.json
    # userprofile.py의 함수 호출
    result = change_profile_password(
        data.get('login_id'), 
        data.get('currentPw'), 
        data.get('newPw'), 
        data.get('confirmPw')
    )
    # 결과에 따라 응답
    if result:
        return jsonify({"status": True, "message": "성공"}), 200
    else:
        return jsonify({"status": False, "message": "비밀번호 검증 실패"}), 400

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

        # --- [A 분기] 상세 페이지에서 온 확정(update) 저장 처리 ---
        if request.is_json:
            data = request.get_json()
            cloth_id = data.get('id') 
            
            # 상세 페이지에서 수정한 데이터를 반영하여 업데이트
            update_payload = {
                "name": data.get('name'),
                "main_category": data.get('main_category'),
                "sub_category": data.get('sub_category'),
                "color": data.get('color'),
                "style": data.get('tags'),
                "temp_level": int(data.get('temp_level', 5)),
                "is_verified": True  # 💡 이제 최종 저장으로 확정
            }

            if not supabase:
                return jsonify({"error": "데이터베이스 연결 오류"}), 500

            response = supabase.table("clothes").update(update_payload).eq("id", cloth_id).execute()
            return jsonify({"message": "최종 확정 저장 성공", "data": response.data}), 200

        # --- [B 분기] 사진 업로드 및 AI 분석 처리 (임시 저장) ---
        if 'cloth_image' not in request.files:
            return jsonify({"error": "사진 파일이 없습니다."}), 400
        
        file = request.files['cloth_image']
        if file.filename == '':
            return jsonify({"error": "파일이 선택되지 않았습니다."}), 400

        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        if process_user_upload:
            print(f"🚀 [app.py] AI 분석 시작: {user_email}")
            result = process_user_upload(file_path, user_email)
            
            if os.path.exists(file_path): os.remove(file_path)
            
            if result:
                # 💡 [핵심] 임시 저장 (is_verified: False)
                result['is_verified'] = False
                result['user_email'] = user_email
                
                # DB 저장 후 생성된 ID 반환
                response = supabase.table("clothes").insert(result).execute()
                inserted_data = response.data[0] 
                
                return jsonify({
                    "message": "AI 분석 및 임시 저장 성공!", 
                    "data": inserted_data
                }), 200
            else:
                return jsonify({"error": "AI 분석 실패"}), 500
        else:
            return jsonify({"error": "분석 모듈을 찾을 수 없습니다."}), 500

    except Exception as e:
        print(f"❌ 라우터 에러: {str(e)}")
        return jsonify({"error": f"서버 오류: {str(e)}"}), 500


# recommend_clothes.py 파일 변경 없이 호환 및 데이터 부족 방어 레이어 시스템 탑재
@app.route('/api/recommend')
def recommend():
    try:
        weather_data = fetch_weather()
        if isinstance(weather_data, list) and len(weather_data) > 0:
            temp = weather_data[0].get("temp", 20)
        else:
            temp = 20
            
        target_tpo = request.args.get('tpo', '캐주얼')
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({"error": "로그인이 필요합니다."}), 401

        user_clothes = []
        if supabase:
            response = supabase.table("clothes").select("*").eq("user_email", user_email).execute()
            user_clothes = response.data

        # 1단계: 원래 추천 모듈 실행
        # 만약 total_wear_count 부재로 내부 오류가 나면 가로채서 복구 로직을 가동합니다.
        top_5_outfits = []
        try:
            top_5_outfits = recommend_clothes_logic(temp, target_tpo, user_clothes) if recommend_clothes_logic else []
        except KeyError:
            # 💡 [추천 파일 무수정 패치 가드] total_wear_count 정렬 키 오류 발생 시 
            # app.py 단에서 순수 알고리즘 결합 루프까지만의 산출 데이터(outfits)를 수동 조립하여 원천 구원합니다.
            from services.recommend_clothes import get_target_level, calculate_style_score, calculate_color_score
            target_lv = get_target_level(temp)
            
            valid_bottoms = [c for c in user_clothes if c.get('main_category') == '하의' and abs(c['temp_level'] - target_lv) <= 1]
            inners = [c for c in user_clothes if c.get('main_category') == '상의' and c.get('sub_category') == '이너']
            outers = [c for c in user_clothes if c.get('main_category') == '상의' and c.get('sub_category') == '아우터']
            
            # 덧셈 조합의 유연성 완화 패치 적용 (후보 부족 시 최우선 노출 가드)
            valid_top_combos = []
            for inner in inners:
                if abs(inner['temp_level'] - target_lv) <= 1:
                    valid_top_combos.append([inner])
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
                    
                    outfits_backup.append({
                        "top_combo": top_combo,
                        "bottom": bottom,
                        "total_score": total_score,
                        "style_score": style_score,
                        "color_score": color_score
                    })
            top_5_outfits = sorted(outfits_backup, key=lambda x: x['total_score'], reverse=True)[:5]

        # 2단계: 후보군 타입 가드 앤 안전 리스트 정렬
        if not isinstance(top_5_outfits, list):
            top_5_outfits = []

        # 3단계: 최종 동적 딕셔너리로 캡슐화하여 전송 (1개든 2개든 있는 후보만큼만 화면에 유연하게 렌더링됨!)
        return jsonify({
            "current_temp": temp,
            "target_tpo": target_tpo,
            "recommendations": top_5_outfits
        })
    except Exception as e:
        print(f"❌ 추천 가드 오류 확인: {e}")
        return jsonify({"current_temp": 20, "target_tpo": "캐주얼", "recommendations": []})

@app.route('/guide')
def guide_main(): 
    user_email = session.get('user_email')
    # 💡 렌더링할 때 logged_in=is_logged_in 을 아예 제거합니다.
    # 이렇게 하면 템플릿이 @app.context_processor에 선언된 정확한 true/false 값만 깔끔하게 참조합니다.
    return render_template('guide.html', user_email=user_email)

@app.route('/guide/dictionary')
def guide_dictionary():
    try:
        return render_template('guide_dictionary.html')
    except Exception:
        return "<h3>기본 패션 아이템 도감 페이지 준비 중입니다!</h3><br><a href='/guide'>가이드로 돌아가기</a>"

@app.route('/body_guide')
def body_guide():
    try:
        # 로그인 세션 상태 가드 레이어 함께 전송
        is_logged_in = 'user_email' in session
        user_email = session.get('user_email')
        
        return render_template('body_guide.html', logged_in=is_logged_in, user_email=user_email)
    except Exception as e:
        print(f"❌ 체형 가이드 페이지 로드 실패: {e}")
        return "<h3>체형별 가이드 페이지 준비 중입니다!</h3><br><a href='/guide'>가이드로 돌아가기</a>"

@app.route('/codi')
def codi_page():
    is_logged_in = 'user_email' in session
    user_email = session.get('user_email')
    return render_template('codi.html', logged_in=is_logged_in, user_email=user_email)

@app.route('/tpo_guide')
def tpo_guide():
    try:
        is_logged_in = 'user_email' in session
        user_email = session.get('user_email')
        return render_template('tpo_guide.html', logged_in=is_logged_in, user_email=user_email)
    except Exception:
        return "<h3>TPO 가이드 페이지 준비 중입니다!</h3><br><a href='/guide'>가이드로 돌아가기</a>"
        
@app.route('/color_guide')
def color_guide():
    try:
        # 로그인 세션 상태 가드 레이어 함께 전송
        is_logged_in = 'user_email' in session
        user_email = session.get('user_email')
        
        return render_template('color_guide.html', logged_in=is_logged_in, user_email=user_email)
    except Exception as e:
        print(f"❌ 컬러 가이드 페이지 로드 실패: {e}")
        return "<h3>컬러 매칭 가이드 페이지 준비 중입니다!</h3><br><a href='/guide'>가이드로 돌아가기</a>"


@app.route('/my_closet')
def my_closet():
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('login'))
    
    is_logged_in = 'user_email' in session
    clothes_list = []
    
    try:
        if supabase:
            response = supabase.table("clothes").select("*").eq("user_email", user_email).execute()
            clothes_list = response.data
    except Exception as e:
        print(f"❌ 내 옷장 조회 실패: {e}")

    raw_weather = fetch_weather()
    current_weather = raw_weather[0] if raw_weather and isinstance(raw_weather, list) and len(raw_weather) > 0 else None

    return render_template('my_closet.html', 
                           clothes=clothes_list, 
                           weather=current_weather,
                           user_email=user_email,
                           logged_in=is_logged_in)

@app.route('/add_clothes')
def add_clothes():
    if 'user_email' not in session: return redirect(url_for('login'))
    return render_template('add_clothes.html')

@app.route('/add_clothes_photo')
def add_clothes_photo():
    if 'user_email' not in session: return redirect(url_for('login'))
    return render_template('add_clothes_photo.html')

@app.route('/add_clothes_photo_detail')
def add_clothes_photo_detail():
    if 'user_email' not in session: return redirect(url_for('login'))
    return render_template('add_clothes_photo_detail.html')


@app.route('/clothes_detail/<int:cloth_id>')
def clothes_detail(cloth_id):
    if 'user_email' not in session: return redirect(url_for('login'))
    
    cloth_data = None
    try:
        if supabase:
            response = supabase.table("clothes").select("*").eq("id", cloth_id).execute()
            cloth_data = response.data[0] if response.data else None
    except Exception as e:
        print(f"❌ 옷 상세 데이터 조회 실패: {e}")

    return render_template('clothes_detail.html', cloth=cloth_data)

@app.route('/api/clothes/update/<int:cloth_id>', methods=['POST'])
def update_cloth_api(cloth_id):
    if 'user_email' not in session: return jsonify({"error": "로그인이 필요합니다."}), 401
        
    data = request.get_json()
    tpo = data.get('tpo') 
    season = data.get('season')  # ✨ [최신 프론트엔드 대응 추가]: 프론트에서 보낸 계절 데이터 수신
    
    try:
        if not supabase: return jsonify({"error": "데이터베이스가 연결되어 있지 않습니다."}), 500
            
        # Supabase 업데이트 구문에 "season" 필드 매핑 추가
        response = supabase.table("clothes").update({
            "name": data.get('name'),
            "main_category": data.get('main_category'),
            "sub_category": data.get('sub_category'),
            "color": data.get('color'),
            "season": season,  # ✨ [최신 프론트엔드 대응 추가]: DB 테이블의 season 컬럼에 값 저장
            "style": [tpo] if tpo else []
        }).eq("id", cloth_id).execute()
        
        return jsonify({"message": "수정 성공", "data": response.data}), 200
    except Exception as e:
        return jsonify({"error": f"수정 실패: {str(e)}"}), 500

@app.route('/api/clothes/delete/<int:cloth_id>', methods=['POST'])
def delete_cloth_api(cloth_id):
    if 'user_email' not in session: return jsonify({"error": "로그인이 필요합니다."}), 401
    try:
        if supabase:
            supabase.table("clothes").delete().eq("id", cloth_id).execute()
        return jsonify({"message": "삭제 성공"}), 200
    except Exception as e:
        return jsonify({"error": f"삭제 실패: {str(e)}"}), 500

@app.route('/my_scrap')
def my_scrap():
    # 세션 로그인 여부 가드 레이어 전송
    is_logged_in = 'user_email' in session
    user_email = session.get('user_email')
    
    # 비로그인 상태일 때 접근 제한을 주려면 주석을 해제하세요.
    # if not user_email: return redirect(url_for('login'))

    return render_template('my_scrap.html', logged_in=is_logged_in, user_email=user_email)

@app.route('/my_profile')
def my_profile():
    # 로그인 세션 유효성 안전 가드 작동
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('login'))
    
    is_logged_in = 'user_email' in session
    return render_template('my_profile.html', logged_in=is_logged_in, user_email=user_email)

if __name__ == '__main__':
    print("\n🚀 패션 앱 서버 웹 서비스 구동 중...")
    app.run(host='0.0.0.0', port=5000, debug=True)
