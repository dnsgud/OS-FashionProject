# 모듈 및 DB 연결 초기화 코드 작성
import os
import re
import traceback
from dotenv import load_dotenv
from supabase import create_client
from auth_service import sign_up_user

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

def _execute_signup_pipeline(clean_data):
    # 기존 auth_service의 가입 로직 호출 (이메일, 비밀번호)
    auth_success = sign_up_user(clean_data["email"], clean_data["password"])
    
    if auth_success:
        # 인증 계정 생성 성공 시, public.users 테이블에 닉네임 저장
        profile_data = {"email": clean_data["email"], "nickname": clean_data["nickname"]}
        query = supabase.table('users').insert(profile_data)
        response = query.execute()
        return response.data
    
    return None

def register_new_user(input_data):
    # 회원가입 파이프라인 전체 흐름 제어 코드 작성
    try:
        # 데이터 추출 및 통합 검증 실행 코드 작성
        clean_data = _extract_and_validate_signup_data(input_data)
        if not clean_data:
            # 유효성 검증 실패 시 중단 코드 작성
            print("[알고리즘 경고] 회원가입 데이터 유효성 검증 실패")
            return False

        # DB 적재 모듈 호출 및 결과 반환 코드 작성
        result = _execute_signup_query(clean_data)
        if result:
            print(f"[DB 로그] 회원가입 성공: {clean_data['email']}")
            return True
            
        return False

    except Exception as e:
        # 파이프라인 런타임 에러 예외 처리 코드 작성
        print(f"[DB 에러] 회원가입 파이프라인 붕괴: {e}")
        traceback.print_exc()
        return False