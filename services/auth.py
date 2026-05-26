# 모듈 및 DB 연결 초기화 코드 작성
import os
import re
import traceback
from dotenv import load_dotenv
from supabase import create_client

# 환경변수 로드 및 Supabase 클라이언트 세팅 코드 작성
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

def _validate_email_format(email):
    # 이메일 데이터 형식 검증 코드 작성
    if not email or not isinstance(email, str):
        return False
        
    # 정규식을 이용한 아이디 규격 판별 코드 작성
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def _validate_password_match(password, password_confirm):
    # 비밀번호 최소 길이 충족 여부 확인 코드 작성
    if not password or len(password) < 6:
        return False
        
    # 비밀번호와 비밀번호 확인 값 일치 검증 코드 작성
    if password != password_confirm:
        return False
        
    return True

def _validate_nickname(nickname):
    # 닉네임 문자열 여부 판별 코드 작성
    if not nickname or not isinstance(nickname, str):
        return False
        
    # 공백 제거 및 글자 수 제한 검사 코드 작성
    stripped_nick = nickname.strip()
    if len(stripped_nick) < 2 or len(stripped_nick) > 10:
        return False
        
    return True