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