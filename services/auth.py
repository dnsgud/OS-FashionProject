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

def _extract_and_validate_signup_data(input_data):
    # 프론트엔드 전달 데이터 개별 추출 코드 작성
    email = input_data.get("email")
    password = input_data.get("password")
    password_confirm = input_data.get("password_confirm")
    nickname = input_data.get("nickname")

    # 전체 유효성 검사 통과 시 딕셔너리 포장 코드 작성
    if _validate_email_format(email) and _validate_password_match(password, password_confirm) and _validate_nickname(nickname):
        return {"email": email, "password": password, "nickname": nickname.strip()}
        
    return None

def _execute_signup_query(clean_data):
    # 정제된 회원가입 데이터 DB 삽입 쿼리 실행 코드 작성
    query = supabase.table('users').insert(clean_data)
    response = query.execute()
    
    return response.data