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

def _validate_login_id(login_id):
    # 아이디 길이 및 영문/숫자 조합 검증 코드 작성
    if not login_id or not isinstance(login_id, str):
        return False
        
    pattern = r'^[a-z0-9]{4,15}$'
    return bool(re.match(pattern, login_id))

def _validate_name(name):
    # 이름 문자열 존재 및 길이 유효성 검증 코드 작성
    if not name or not isinstance(name, str):
        return False
        
    stripped_name = name.strip()
    if len(stripped_name) < 2 or len(stripped_name) > 10:
        return False
        
    return True

def _extract_and_validate_signup_data(input_data):
    # 프론트엔드 전달 데이터 개별 추출 및 확장 코드 작성
    login_id = input_data.get("login_id")
    email = input_data.get("email")
    password = input_data.get("password")
    password_confirm = input_data.get("password_confirm")
    nickname = input_data.get("nickname")
    name = input_data.get("name")

    # 전체 유효성 검사 통합 판별 로직
    if (_validate_login_id(login_id) and 
        _validate_email_format(email) and 
        _validate_password_match(password, password_confirm) and 
        _validate_nickname(nickname) and 
        _validate_name(name)):
        
        
        return {
            "login_id": login_id.strip(),
            "email": email.strip(),
            "password": password,
            "nickname": nickname.strip(),
            "name": name.strip()
        }
        
    return None

def _execute_signup_pipeline(clean_data):
    # 기존 auth_service의 가입 로직 호출 (이중 저장 방지를 위해 모든 확장 데이터를 한 번에 전달)
    auth_success = sign_up_user(
        email=clean_data["email"],
        password=clean_data["password"],
        nickname=clean_data["nickname"],
        login_id=clean_data["login_id"],  # [추가]
        name=clean_data["name"]           # [추가]
    )
    
    # DB 저장은 sign_up_user 내부에서 통합 처리되므로 성공 여부만 반환한다
    if auth_success:
        return True
    
    return None

def register_new_user(input_data):
    # 확장된 회원가입 파이프라인 전체 흐름 제어 로직
    try:
        clean_data = _extract_and_validate_signup_data(input_data)
        
        if not clean_data:
            print("[알고리즘 경고] 회원가입 데이터 유효성 검증 실패 (항목 누락/오류)")
            return False

        # 인증 및 DB 적재 파이프라인 실행
        result = _execute_signup_pipeline(clean_data)
        
        if result:
            print(f"[DB 로그] 회원가입 및 확장 프로필 적재 성공: {clean_data['login_id']}")
            return True
            
        return False

    except Exception as e:
        print(f"[DB 에러] 통합 회원가입 파이프라인 붕괴: {e}")
        traceback.print_exc()
        return False
    
def _execute_duplicate_query(column_name, value):
    # DB 테이블 특정 컬럼의 중복 데이터 존재 여부 파악 로직
    try:
        query = supabase.table('users').select(column_name).eq(column_name, value).execute()
        return query.data
    except Exception as e:
        # 쿼리 실패 시 에러 로그 출력 및 None 반환 처리
        print(f"[DB 에러] 중복 조회 쿼리 실행 실패: {e}")
        return None
    
def check_login_id_duplicate(login_id):
    # 빈 값 입력 방지 및 예외 처리
    if not login_id:
        return False

    # 공통 쿼리 모듈을 활용한 아이디 데이터 조회
    result = _execute_duplicate_query('login_id', login_id)

    # 조회 결과가 존재하거나 에러(None)일 경우 중복/사용 불가 판별
    if result is None or len(result) > 0:
        print(f"[알고리즘 경고] 중복 아이디 감지: {login_id}")
        return False

    # 빈 배열 반환 시 사용 가능 아이디 승인
    print(f"[DB 로그] 사용 가능 아이디: {login_id}")
    return True

def check_email_duplicate(email):
    # 빈 값 입력 방지 및 예외 처리
    if not email:
        return False

    # 공통 쿼리 모듈을 활용한 이메일 데이터 조회
    result = _execute_duplicate_query('email', email)

    # 조회 결과 존재 시 기가입 이메일로 분류하여 사용 불가 판별
    if result is None or len(result) > 0:
        print(f"[알고리즘 경고] 중복 이메일 감지: {email}")
        return False

    # 미존재 데이터 확인 시 신규 사용 가능 이메일 승인
    print(f"[DB 로그] 사용 가능 이메일: {email}")
    return True