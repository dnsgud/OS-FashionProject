import requests
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY") 

def sign_up_user(email, password):
    """
    개별 사용자의 고유 계정을 생성하는 기능 (회원가입)
    """
    url = f"{Config.SUPABASE_URL}/auth/v1/signup"
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
        return True
    else:
        print(f"회원가입 실패: {response.json()}")
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
        # 인증 성공 시 액세스 토큰 반환
        return response.json().get("access_token")
    else:
        print(f"로그인 실패: {response.json()}")
        return None