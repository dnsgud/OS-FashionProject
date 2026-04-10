from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "파이썬 패션 백엔드 서버가 가동되었습니다!"

if __name__ == '__main__':
    app.run(debug=True, port=5000)