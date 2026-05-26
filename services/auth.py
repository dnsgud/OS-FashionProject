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