import os
import traceback
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL") # supabase 주소를 가져와 url에 저장
key = os.getenv("SUPABASE_KEY") # api 키를 가져와 key 변수에 저장
supabase = create_client(url, key) # 주소와 키 사용하여 실제 supabase 접속 객체 생성
