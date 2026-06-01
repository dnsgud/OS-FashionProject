import requests
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY") 

def sign_up_user(email, password, nickname, login_id, name, gender=None):
    """
    1단계: Supabase Auth에 계정 생성
    2단계: 성공 시 public.users 테이블에 확장 정보(아이디, 이름 등) 동시 통합 저장
    """
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
            user_id = auth_json.get("id") or auth_json.get("user", {}).get("id")
            
            if not user_id:
                print("⚠️ Supabase 인증에는 성공했으나, UUID를 가져오기 실패")
                return False
                
            db_url = f"{Config.SUPABASE_URL}/rest/v1/users"
            db_headers = {
                "apikey": Config.SUPABASE_KEY,
                "Authorization": f"Bearer {Config.SUPABASE_KEY}", 
                "Content-Type": "application/json",
                "Prefer": "return=minimal"                      
            }
            db_data = {
                "id": user_id,          
                "login_id": login_id,   
                "email": email,         
                "pw": password,         
                "name": name,           
                "nickname": nickname,   
                "gender": gender
            }
            
            db_response = requests.post(db_url, headers=db_headers, json=db_data)
            
            if db_response.status_code in [200, 201]:
                print(f"[성공] '{nickname}'님 회원가입 및 테이블 데이터 저장 완료")
                return True
            else:
                print(f" [오류] 인증은 되었으나 테이블 저장 실패: {db_response.status_code}, {db_response.text}")
                return False
        else:
            print(f" [Supabase 인증 에러]: {auth_response.status_code}, {auth_response.json()}")
            return False
            
    except Exception as e:
        print(f"네트워크 에러: {e}")
        return False

def login_user(login_id, password):
    """
    [수정된 로그인 로직 - 다이렉트 로그인]
    Auth 서버를 거치지 않고, public.users DB의 pw 컬럼을 직접 확인합니다.
    """
    db_url = f"{Config.SUPABASE_URL}/rest/v1/users?login_id=eq.{login_id}&pw=eq.{password}"
    db_headers = {
        "apikey": Config.SUPABASE_KEY,
        "Authorization": f"Bearer {Config.SUPABASE_KEY}"
    }
    
    try:
        response = requests.get(db_url, headers=db_headers)
        
        if response.ok and response.json():
            user_data = response.json()[0]
            print(f"[DB 로그] DB 다이렉트 로그인 성공: {login_id}")
            return user_data 
            
        else:
            print(f" [오류] 아이디 또는 비밀번호 불일치")
            return None # 일치하는 정보가 없으면 None 반환
            
    except Exception as e:
        print(f"네트워크 에러: {e}")
        return None
    
def get_email_by_login_id(login_id):
    try:
        db_url = f"{Config.SUPABASE_URL}/rest/v1/users?login_id=eq.{login_id}&select=email"
        db_headers = {
            "apikey": Config.SUPABASE_KEY,
            "Authorization": f"Bearer {Config.SUPABASE_KEY}"
        }
        response = requests.get(db_url, headers=db_headers)
        if response.ok and response.json():
            return response.json()[0].get("email")
    except Exception as e:
        print(f"❌ 이메일 조회 실패: {e}")
    return None    

def fetch_user_profile(login_id):
    """
    login_id를 기반으로 public.users 테이블에서 해당 사용자의 
    모든 정보(닉네임, 이메일, 이름 등)를 가져옵니다.
    """
    # Supabase REST API 호출 경로
    db_url = f"{Config.SUPABASE_URL}/rest/v1/users?login_id=eq.{login_id}"
    db_headers = {
        "apikey": Config.SUPABASE_KEY,
        "Authorization": f"Bearer {Config.SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    try:
        response = requests.get(db_url, headers=db_headers)
        
        if response.status_code == 200:
            data = response.json()
            return data[0] if data else None
        else:
            print(f" [오류] 사용자 정보 조회 실패: {response.status_code}, {response.text}")
            return None
            
    except Exception as e:
        print(f" [에러] 네트워크 예외 발생: {e}")
        return None