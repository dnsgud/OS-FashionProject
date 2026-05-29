import random
import traceback

try:
    from config import supabase
    from user_profile import update_account_password
    from auth import login_with_custom_id
except ImportError:
    pass

# 서버 구동 중 인증번호를 일시적으로 보관하는 딕셔너리 메모리
_verification_store = {}

def _generate_and_send_code(email):
    # 4자리 무작위 숫자 생성 및 임시 저장 처리 로직
    code = str(random.randint(1000, 9999))
    _verification_store[email] = code

    # 실제 이메일 발송 API가 연동될 자리이다
    print(f"[알고리즘 로그] {email} 계정으로 인증번호 발송 시뮬레이션 완료: {code}")
    return True

def _verify_email_code(email, input_code):
    # 메모리 저장소의 난수와 사용자의 입력값 일치 여부 대조 로직이다
    if email in _verification_store and _verification_store[email] == str(input_code):
        # 인증 성공 시 재사용 방지를 위해 즉시 데이터를 폐기한다
        del _verification_store[email]
        return True
        
    return False

def request_find_id(name, email):
    # 이름 및 이메일 기반 DB 회원 정보 탐색 및 인증번호 발송 제어 로직이다
    try:
        query = supabase.table('users').select('login_id').eq('name', name).eq('email', email).execute()
        
        # 회원이 존재할 경우에만 인증번호 발송 모듈을 호출한다
        if query.data:
            return _generate_and_send_code(email)
            
        print("[알고리즘 경고] 가입되지 않은 이름 또는 이메일 조합 감지")
        return False
        
    except Exception as e:
        print(f"[DB 에러] 아이디 찾기 대상자 조회 실패: {e}")
        return False
    
def verify_and_get_login_id(name, email, input_code):
    # 인증번호 4자리 성공 검증 시 DB 아이디 최종 추출 처리이다
    if _verify_email_code(email, input_code):
        query = supabase.table('users').select('login_id').eq('name', name).eq('email', email).execute()
        
        # 보안 검증이 끝난 후 사용자 고유 식별자(아이디)를 반환한다
        if query.data:
            print(f"[DB 로그] 아이디 찾기 인증 성공: {query.data[0]['login_id']}")
            return query.data[0]['login_id']
            
    print("[알고리즘 에러] 인증번호 불일치로 아이디 반환이 거부되었다")
    return None

def request_find_password(name, login_id, email):
    # 이름, 아이디, 이메일 3중 조건 완벽 일치 여부 대조 및 발송 제어이다
    try:
        # DB의 3개 컬럼이 모두 일치하는 레코드만 선택적으로 타겟팅한다
        query = supabase.table('users').select('login_id').eq('name', name).eq('login_id', login_id).eq('email', email).execute()
        
        if query.data:
            return _generate_and_send_code(email)
            
        print("[알고리즘 경고] 등록 정보와 불일치하는 비밀번호 찾기 시도 감지")
        return False
        
    except Exception as e:
        print(f"[DB 에러] 비밀번호 찾기 대상자 3중 조회 실패: {e}")
        return False