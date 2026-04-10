from flask import Flask, request, jsonify, render_template, session, redirect
import auth_service
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# 1. 초기 화면
@app.route('/')
def index():
    if 'user' in session:
        return render_template('main_home.html', user=session['user'])
    return render_template('login.html')

# 2. 회원가입 페이지 이동
@app.route('/signup')
def signup_page():
    return render_template('signup.html')

# 3. 회원가입 API
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get('email')
    password = data.get('password')
   
    if auth_service.sign_up_user(email, password):
        return jsonify({"message": "회원가입 성공"}), 201
    return jsonify({"error": "회원가입 실패"}), 400

# 4. 로그인 API
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
   
    token = auth_service.login_user(email, password)
   
    if token:
        session['user'] = email
        return jsonify({"message": "로그인 성공"}), 200
    return jsonify({"error": "인증 실패"}), 401

# 5. 로그아웃 API
@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({"message": "로그아웃 완료"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
