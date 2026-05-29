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

def update_member_profile(current_login_id, input_data):
    # 최종 확인 버튼 클릭 시 변경된 유효 데이터를 일괄적으로 갱신하는 제어 로직
    try:
        # 기존 프로필 상태를 로드하여 변경 기준점으로 삼는다
        current_profile = fetch_user_profile(current_login_id)
        if not current_profile:
            return False
            
        # 헬퍼 함수를 통해 변경이 승인된 안전한 데이터만 추출
        final_clean_data = _filter_modified_profile_data(input_data, current_profile)
        
        # 갱신할 데이터가 존재할 경우 DB 일괄 업데이트 쿼리를 수행
        if final_clean_data:
            response = supabase.table('users').update(final_clean_data).eq('login_id', current_login_id).execute()
            print(f"[DB 로그] 회원 정보 일괄 갱신 성공: {final_clean_data}")
            return bool(response.data)
            
        print("[알고리즘 로그] 변경 사항이 존재하지 않아 업데이트가 생략")
        return True # 정상적인 변경 없음 상태이므로 승인 처리
        
    except ValueError as ve:
        print(f"[알고리즘 에러] 데이터 무결성 검증 차단: {ve}")
        return False
    except Exception as e:
        print(f"[DB 에러] 회원 정보 갱신 파이프라인 붕괴: {e}")
        return False
    
try:
    from auth import _validate_password_match
except ImportError:
    pass

def update_account_password(login_id, new_pw, new_pw_confirm):
    
    # auth.py 모듈을 재사용하여 새 비밀번호 길이 제약(6자) 및 두 입력값 불일치를 검증
    if not _validate_password_match(new_pw, new_pw_confirm):
        print("[알고리즘 에러] 새 비밀번호 규격 미달 또는 확인 데이터 불일치 감지")
        return False
        
    try:
        # 이중 검증 통과 시 DB 레코드를 업데이트
        response = supabase.table('users').update({'pw': new_pw}).eq('login_id', login_id).execute()
        
        print(f"[DB 로그] 신규 비밀번호 다이렉트 갱신 처리 완료: {login_id}")
        return bool(response.data)
        
    except Exception as e:
        print(f"[DB 에러] 비밀번호 다이렉트 업데이트 쿼리 실행 실패: {e}")
        return False