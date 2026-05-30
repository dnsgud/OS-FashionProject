import requests
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY") 

def sign_up_user(email, password, nickname, gender=None):
    """
    1단계: Supabase Auth에 계정 생성
    2단계: 성공 시 public.users 테이블에 추가 정보(닉네임, 성별 등) 동시 저장
    """
    # [1단계] Supabase 내장 인증 시스템(GoTrue)에 가입
    auth_url = f"{Config.SUPABASE_URL}/auth/v1/signup"
    auth_headers = {
        "apikey": Config.SUPABASE_KEY,
        "Content-Type": "application/json"
    }
    auth_data = {
        "email": email,
        "password": password
    }
    
    try:
        auth_response = requests.post(auth_url, headers=auth_headers, json=auth_data)
        
        if auth_response.status_code in [200, 201]:
            auth_json = auth_response.json()
            
            # 인증 시스템이 발급한 유저 고유 UUID 추출 (버전별 예외 방지 가드)
            user_id = auth_json.get("id") or auth_json.get("user", {}).get("id")
            
            if not user_id:
                print("⚠️ Supabase 인증에는 성공했으나, UUID를 가져오지 못했습니다.")
                return False
                
            # [2단계] 생성된 UUID와 회원 정보를 내 'users' 테이블에 강제로 매칭하여 삽입
            db_url = f"{Config.SUPABASE_URL}/rest/v1/users"
            db_headers = {
                "apikey": Config.SUPABASE_KEY,
                "Authorization": f"Bearer {Config.SUPABASE_KEY}", # DB 조작을 위한 인증 토큰
                "Content-Type": "application/json",
                "Prefer": "return=minimal"                       # 불필요한 반환값 생략으로 속도 최적화
            }
            db_data = {
                "id": user_id,          # auth.users의 UUID와 1:1 매칭
                "email": email,         # 최적화된 DB 규격 매칭
                "pw": password,         # DB의 pw NOT NULL 조건 충족
                "nickname": nickname,   # DB의 nickname NOT NULL 조건 충족
                "gender": gender
            }
            
            db_response = requests.post(db_url, headers=db_headers, json=db_data)
            
            if db_response.status_code in [200, 201]:
                print(f"🎉 [성공] '{nickname}'님 회원가입 및 테이블 데이터 저장 완료!")
                return True
            else:
                print(f"❌ [오류] 인증은 되었으나 테이블 저장 실패: {db_response.status_code}, {db_response.text}")
                return False
        else:
            print(f"❌ [Supabase 인증 에러]: {auth_response.status_code}, {auth_response.json()}")
            return False
            
    except Exception as e:
        print(f"네트워크 에러: {e}")
        return False

def login_user(email, password):
    """
    사용자 정보를 대조하여 인증 토큰을 생성하는 기능 (로그인)
    """
    url = f"{Config.SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": Config.SUPABASE_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "email": email,
        "password": password
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print(f"로그인 실패: {response.json()}")
        return None
