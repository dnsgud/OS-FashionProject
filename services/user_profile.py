import traceback

try:
    from config import supabase
except ImportError:
    pass

def fetch_user_profile(login_id):
    # 기존 프로필 데이터를 조회하여 프론트엔드 입력칸에 미리 노출하기 위한 로직
    if not login_id:
        return None
        
    try:
        
        query = supabase.table('users').select('login_id, email, name, nickname').eq('login_id', login_id).execute()
        
        if query.data:
            print(f"[DB 로그] 기존 프로필 데이터 로드 완료: {login_id}")
            return query.data[0]
            
        print("[알고리즘 에러] 조회 가능한 프로필 데이터가 존재 X")
        return None
        
    except Exception as e:
        print(f"[DB 에러] 프로필 데이터 조회 쿼리 실행 실패: {e}")
        return None
    
# 기존 auth.py에 훌륭하게 구현된 검증 모듈들을 재사용
try:
    from auth import (
        _validate_login_id, _validate_email_format, _validate_name, _validate_nickname,
        check_login_id_duplicate, check_email_duplicate
    )
except ImportError:
    pass

def _filter_modified_profile_data(input_data, current_profile):
    # 프론트엔드 전송 데이터 중 실질적 변경이 발생한 항목만 이중 필터링하는 내부 로직
    clean_data = {}
    
    # 1. 텍스트 데이터(이름, 닉네임) 무결성 검증
    if "name" in input_data and _validate_name(input_data["name"]):
        clean_data["name"] = input_data["name"].strip()
    if "nickname" in input_data and _validate_nickname(input_data["nickname"]):
        clean_data["nickname"] = input_data["nickname"].strip()
        
    # 2. 고유 데이터(아이디, 이메일) 변경 시에만 중복 및 규격 검증 (백엔드 이중 잠금)
    if "login_id" in input_data:
        new_id = input_data["login_id"]
        if new_id != current_profile.get("login_id"):
            if _validate_login_id(new_id) and check_login_id_duplicate(new_id):
                clean_data["login_id"] = new_id
            else:
                raise ValueError("아이디 이중 검증 실패")
                
    if "email" in input_data:
        new_email = input_data["email"]
        if new_email != current_profile.get("email"):
            if _validate_email_format(new_email) and check_email_duplicate(new_email):
                clean_data["email"] = new_email
            else:
                raise ValueError("이메일 이중 검증 실패")
                
    return clean_data