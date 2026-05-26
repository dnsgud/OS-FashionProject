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