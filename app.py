import os
import sys
import logging
from werkzeug.utils import secure_filename
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_cors import CORS

# [수정] 에러 로그 설정
logging.basicConfig(level=logging.INFO) 

# [중요] 경로 추가를 임포트보다 먼저 해야 안전합니다.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# [해결] Flask 임포트 후에 app을 선언해야 합니다.
app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)
app.secret_key = "my_fashion_app_secret_1234"
# 서비스 모듈 임포트
try:
    from config import supabase
    from weather_service import fetch_weather
    from auth_service import sign_up_user, login_user 
    from services.imgproc import process_user_upload
    from services.recommend_clothes import recommend_clothes_logic
except ImportError as e:
    print(f"❌ 임포트 에러 발생: {e}")
    
app = Flask(__name__)
CORS(app)
app.secret_key = "my_fashion_app_secret_1234"

# 업로드 폴더 설정
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- [라우트 설정] ---

@app.route('/')
def home():
    try:
        # weather_service.py에서 가져온 함수 사용
        weather_data = fetch_weather() 
        temp = weather_data.get("main", {}).get("temp", 0) if weather_data else 0
        # index.html을 렌더링하도록 수정 (현재 파일명이 index.html이므로)
        return render_template('index.html', temp=temp) 
    except Exception as e:
        logging.error(f"Home route error: {e}")
        return render_template('index.html', temp=0)
    
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "이메일과 비밀번호를 모두 입력해주세요."}), 400

    # auth_service.py의 login_user 함수 호출
    # (참고: auth_service.py의 login_user가 성공 시 True 또는 사용자 데이터를 반환하도록 확인 필요)
    is_success = login_user(email, password)

    if is_success:
        # 로그인 성공 시 세션에 이메일 저장
        session['user_email'] = email
        return jsonify({"message": "로그인 성공"}), 200
    else:
        return jsonify({"error": "아이디 또는 비밀번호가 일치하지 않습니다."}), 401
    
@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if sign_up_user(email, password):
            return redirect(url_for('login'))
        else:
            return "회원가입 실패!", 400
    return render_template('signup.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "이메일과 비밀번호를 입력해주세요."}), 400

    # [중요] auth_service.py에 정의된 함수명(sign_up_user)과 일치해야 함
    success = sign_up_user(email, password)

    if success:
        return jsonify({"message": "회원가입 성공!"}), 201
    else:
        return jsonify({"error": "회원가입에 실패했습니다. 이미 존재하는 계정일 수 있습니다."}), 400
    
@app.route('/logout')
def logout():
    session.clear() # 세션 데이터 모두 삭제
    return redirect(url_for('home')) # 메인 페이지로 리다이렉트

# [핵심] 옷 업로드 및 AI 분석 저장 로직
@app.route('/api/upload', methods=['POST'])
def upload_cloth():
    try:
        # 1. 로그인 확인
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({"error": "로그인이 필요합니다."}), 401

        # 2. 파일 확인
        if 'cloth_image' not in request.files:
            return jsonify({"error": "사진 파일이 없습니다."}), 400
        
        file = request.files['cloth_image']
        if file.filename == '':
            return jsonify({"error": "선택된 파일이 없습니다."}), 400

        # 3. 서버 임시 저장
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        # 4. imgproc.py의 로직 실행 (AI 분석 + Supabase 저장)
        # 현빈님이 원하신 대로 요청 시에만 AI가 돌아갑니다.
        result = process_user_upload(file_path, user_email)

        if result:
            if os.path.exists(file_path):
                os.remove(file_path) # 임시파일 삭제
            return jsonify({"message": "옷 등록 성공!", "data": result}), 200
        else:
            return jsonify({"error": "분석 또는 저장 실패"}), 500

    except Exception as e:
        return jsonify({"error": f"서버 오류: {str(e)}"}), 500

@app.route('/api/weather')
def weather_api():
    try:
        raw_data = fetch_weather()
        refined_data = {
            "city": raw_data.get("name"),
            "temp": raw_data.get("main", {}).get("temp"),
            "humidity": raw_data.get("main", {}).get("humidity"),
            "condition": raw_data.get("weather", [{}])[0].get("description")
        }
        return jsonify(refined_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/recommend')
def recommend():
    try:
        weather_data = fetch_weather()
        temp = weather_data.get("main", {}).get("temp")
        target_tpo = request.args.get('tpo', '캐주얼') 

        user_email = session.get('user_email')
        if not user_email:
            return jsonify({"error": "로그인이 필요합니다."}), 401

        # 내 아이디(user_email)로 저장된 옷만 가져오기
        response = supabase.table("clothes").select("*").eq("user_id", user_email).execute()
        user_clothes = response.data

        top_5_outfits = recommend_clothes_logic(temp, target_tpo, user_clothes)
        
        return jsonify({
            "current_temp": temp,
            "target_tpo": target_tpo,
            "recommendations": top_5_outfits
        })
    except Exception as e:
        return jsonify({"error": f"추천 실패: {str(e)}"}), 500

@app.route('/weather_detail')
def weather_detail():
    # templates 폴더 안에 있는 weather_detail.html을 브라우저에 보여줍니다.
    return render_template('weather_detail.html')


if __name__ == '__main__':
    # 서버 실행 시 주소를 수동으로 출력해서 확인하기 편하게 만듭니다.
    print("\n" + "="*50)
    print("🚀 패션 코드 서버가 가동되었습니다!")
    print("🔗 접속 주소: http://127.0.0.1:5000")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)