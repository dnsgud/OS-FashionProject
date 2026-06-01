import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# 환경 변수 읽기
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# 'supabase'라는 이름으로 직접 생성 (클래스 없이!)
supabase = create_client(url, key)
