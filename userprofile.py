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
        # 1. 🔥 [핵심 추가] 유저의 고유 식별자(UUID) 추출
        user_query = supabase.table('users').select('id').eq('login_id', login_id).execute()
        
        if not user_query.data:
            print("[알고리즘 에러] 해당 아이디를 가진 유저의 고유 식별자를 찾을 수 없다")
            return False
            
        user_uuid = user_query.data[0]['id']

        # 2. 🔥 [핵심 추가] Admin API를 활용하여 토큰 없이 Auth 서버 비밀번호 강제 덮어쓰기
        supabase.auth.admin.update_user_by_id(user_uuid, {"password": new_pw})
        
        # 3. DB users 테이블 레코드 갱신
        response = supabase.table('users').update({'pw': new_pw}).eq('login_id', login_id).execute()
        
        print(f"[DB 로그] 신규 비밀번호 Auth 서버 및 DB 다이렉트 갱신 처리 완료: {login_id}")
        return bool(response.data)
        
    except Exception as e:
        print(f"[DB 에러] 통합 비밀번호 업데이트 파이프라인 붕괴: {e}")
        return False
    
def fetch_user_body_profile(login_id):
    # 화면 진입 시 빈칸 또는 기존 데이터를 채워주기 위한 체형 정보 단일 조회 로직
    if not login_id:
        return None
        
    try:
        # users 테이블에서 키, 몸무게, 체형 데이터만 정확히 타겟팅하여 가져옴
        query = supabase.table('users').select('height, weight, body_shape').eq('login_id', login_id).execute()
        
        # 데이터가 존재하면 반환하고, 최초 가입자라 데이터가 없으면 None을 반환하여 프론트엔드가 빈칸을 띄우게 유도
        if query.data:
            print(f"[DB 로그] 기존 체형 데이터 로드 완료: {login_id}")
            return query.data[0]
            
        print("[알고리즘 로그] 등록된 체형 데이터가 존재 X")
        return None
        
    except Exception as e:
        print(f"[DB 에러] 체형 데이터 조회 쿼리 실행 실패: {e}")
        return None
    
def _filter_body_profile_data(input_data):
    # 입력받은 키, 몸무게, 체형 데이터의 무결성과 정상 범위를 판별하는 필터링 로직이다
    clean_data = {}
    
    # 1. 키 데이터 검증 (문자열 방어 및 100.0cm ~ 250.0cm 허용)
    if "height" in input_data and input_data["height"]:
        try:
            height = float(input_data["height"])
            if 100.0 <= height <= 250.0:
                clean_data["height"] = round(height, 1)
        except ValueError:
            pass # 숫자가 아닌 값이 들어오면 무시하고 필터링한다
            
    # 2. 몸무게 데이터 검증 (문자열 방어 및 30.0kg ~ 200.0kg 허용)
    if "weight" in input_data and input_data["weight"]:
        try:
            weight = float(input_data["weight"])
            if 30.0 <= weight <= 200.0:
                clean_data["weight"] = round(weight, 1)
        except ValueError:
            pass
            
    # 3. 체형 선택 데이터 카테고리 검증 (지정된 3개 외의 임의 조작 값 차단)
    valid_shapes = ["삼각형", "역삼각형", "일자형"]
    if "body_shape" in input_data and input_data["body_shape"] in valid_shapes:
        clean_data["body_shape"] = input_data["body_shape"]
        
    return clean_data

def update_user_body_profile(current_login_id, input_data):
    # 하단 확인 버튼 클릭 시 정제된 체형 데이터를 DB에 일괄 반영하는 제어 로직이다
    try:
        # 필터링 헬퍼 함수를 호출하여 유효한 숫자 및 카테고리 데이터만 추출한다
        clean_data = _filter_body_profile_data(input_data)
        
        # 검증을 통과한 데이터가 존재할 경우 DB 일괄 업데이트 쿼리를 수행한다
        if clean_data:
            response = supabase.table('users').update(clean_data).eq('login_id', current_login_id).execute()
            print(f"[DB 로그] 체형 정보 갱신 처리 완료: {clean_data}")
            return bool(response.data)
            
        print("[알고리즘 로그] 유효한 체형 변경 데이터가 없어 업데이트가 생략되었다")
        return True
        
    except Exception as e:
        print(f"[DB 에러] 체형 정보 갱신 파이프라인 붕괴: {e}")
        return False
    
def _verify_current_password(login_id, current_pw):
    # 입력받은 현재 비밀번호와 DB에 저장된 비밀번호의 일치 여부를 대조하는 유틸리티이다
    if not login_id or not current_pw:
        return False
        
    try:
        # DB에서 사용자의 기존 암호(pw)만 단일 조회한다
        query = supabase.table('users').select('pw').eq('login_id', login_id).execute()
        
        # 조회된 데이터가 존재하고 입력값과 완전히 일치할 경우 승인(True)을 반환한다
        if query.data and query.data[0].get('pw') == current_pw:
            return True
            
        print("[알고리즘 경고] 현재 비밀번호 불일치 감지")
        return False
        
    except Exception as e:
        print(f"[DB 에러] 비밀번호 대조 쿼리 실행 실패: {e}")
        return False
    
def authorize_profile_edit(login_id, current_pw):
    # 회원정보 수정 화면 진입 전 비밀번호를 검증하여 접근 권한 및 데이터를 부여하는 컨트롤러이다
    
    # 1단계에서 만든 검증 모듈을 호출하여 일치 여부를 판별한다
    is_authorized = _verify_current_password(login_id, current_pw)
    
    if is_authorized:
        print(f"[DB 로그] 회원정보 수정 화면 진입 보안 승인 완료: {login_id}")
        # 보안 통과 시, 프론트엔드 입력칸에 뿌려줄 기존 데이터를 fetch_user_profile을 재사용해 반환한다
        return fetch_user_profile(login_id)
        
    print("[알고리즘 에러] 비밀번호 불일치로 회원정보 수정 접근이 거부되었다")
    return None

def change_profile_password(login_id, current_pw, new_pw, new_pw_confirm):
    # 3중 입력 폼 값을 동시에 받아 기존 암호 검증과 신규 갱신을 일괄 처리하는 메인 제어기
    
    # 1. 선행 보안 관문으로 현재 비밀번호의 일치 여부 판별
    if not _verify_current_password(login_id, current_pw):
        print("[알고리즘 에러] 기존 비밀번호 불일치로 변경 파이프라인 즉시 차단")
        return False
        
    print("[알고리즘 로그] 기존 비밀번호 일치 확인 완료, 신규 갱신 파이프라인 이관")
    
    # 2. 검증 완료 시 위쪽의 원본 갱신 모듈을 호출하여 새 비밀번호 무결성 검증 및 DB 적재 위임
    return update_account_password(login_id, new_pw, new_pw_confirm)