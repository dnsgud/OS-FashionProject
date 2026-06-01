import random
import traceback
import smtplib
import os
from email.mime.text import MIMEText
from dotenv import load_dotenv
import time

# 기본 시스템 환경 변수와 꼬이지 않도록, 메일 전용 설정 파일만 특정해서 로드
load_dotenv(".mail_env")

try:
    from config import supabase
    from services.user_profile import update_account_password
    from auth_service import login_user
except ImportError as e:
    print(f"[시스템 에러] 모듈 임포트 실패 (account_recovery): {e}")

# 서버 구동 중 인증번호를 일시적으로 보관하는 딕셔너리 메모리
_verification_store = {}

def _generate_and_send_code(email):
    # 4자리 무작위 숫자 생성 및 임시 저장 처리 로직
    code = str(random.randint(1000, 9999))
    _verification_store[email] = code

    # .mail_env 파일에서 송신자 메일 정보를 안전하게 가져옴
    sender_email = os.getenv("SMTP_EMAIL")
    sender_pw = os.getenv("SMTP_PASSWORD")
    
    if not sender_email or not sender_pw:
        print("[알고리즘 에러] SMTP 환경변수가 설정되지 않아 메일을 발송할 수 없다")
        return False

    try:
        # 이메일 제목과 본문 세팅
        mail_content = f"요청하신 계정 복구 인증번호는 [{code}] 이다.\n타인에게 절대 공유하지 않도록 주의한다."
        msg = MIMEText(mail_content)
        msg['Subject'] = "[Smart Climate Fashion] 계정 인증번호 안내"
        msg['From'] = sender_email
        msg['To'] = email

        # 구글 메일 서버(SMTP)에 연결하여 실제 메일 발송을 수행
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls() # 보안 연결(TLS) 시작
        server.login(sender_email, sender_pw)
        server.send_message(msg)
        server.quit()
        
        print(f"[알고리즘 로그] {email} 계정으로 실제 인증번호 메일 발송 완료")
        return True
        
    except Exception as e:
        print(f"[서버 에러] 실제 이메일 발송 중 오류 발생: {e}")
        return False

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
    
def verify_password_reset_code(email, input_code):
    # 비밀번호 신규 변경창 진입을 위한 최종 인증번호 검증 권한 부여 로직이다
    if _verify_email_code(email, input_code):
        print("[알고리즘 로그] 비밀번호 초기화용 이메일 인증 통과 (변경 창 진입 허가)")
        return True
        
    print("[알고리즘 에러] 비밀번호 초기화용 인증번호 불일치")
    return False

def reset_password_and_auto_login(login_id, new_pw, new_pw_confirm):
    # 비밀번호 갱신과 세션 발급을 한 번의 클릭으로 동시 처리하는 통합 파이프라인이다
    
    # 1. user_profile.py의 갱신 로직을 호출하여 DB의 비밀번호를 안전하게 덮어쓴다
    is_updated = update_account_password(login_id, new_pw, new_pw_confirm)
    
    if not is_updated:
        print("[알고리즘 에러] 무결성 검증 실패로 초기화 및 로그인이 취소되었다")
        return None
        
    print("[DB 로그] 비밀번호 초기화 완료, 즉각적인 자동 로그인 세션으로 전환한다")
    
    time.sleep(1)
    
    # 2. 갱신 성공 시 auth_service.py의 커스텀 로그인 모듈을 호출하여 인증을 수행
    login_result = login_user(login_id, new_pw)
    
    if login_result:
        print(f"[DB 로그] 자동 로그인 처리 및 세션 발급 완료: {login_id}")
        return login_result
        
    print("[알고리즘 에러] 비밀번호 변경은 성공했으나 세션 발급에 실패했다")
    return None