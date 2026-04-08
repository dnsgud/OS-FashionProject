import os
import traceback
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL") # supabase 주소를 가져와 url에 저장
key = os.getenv("SUPABASE_KEY") # api 키를 가져와 key 변수에 저장
supabase = create_client(url, key) # 주소와 키 사용하여 실제 supabase 접속 객체 생성

def step2_db_integration():  # DB 연동 작업을 수행하는 함수를 정의
    file_path = "test.jpg"  # 로컬에 저장되어 있는 이미지 파일의 경로를 지정
    storage_path = "test_upload.jpg"  # Supabase 스토리지에 저장될 때 사용할 파일의 이름을 정함