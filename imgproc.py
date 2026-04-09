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

    
        print("\n--- 1단계 Storage 업로드 시도 중... ---")  # 작업 시작을 알리는 로그를 출력
        with open(file_path, 'rb') as f:  # 사진 파일을 (rb) 모드로 열어 f라는 이름으로 사용
            supabase.storage.from_('test-clothes-imgaes').upload(  # 지정한 버킷에 접근하여 업로드를 실행
                path=storage_path,  # 위에서 정한 storage_path 이름으로 서버에 저장
                file=f  # 실제로 열어둔 파일 객체 f를 서버로 전송
            )

        print("--- 2단계 이미지 URL 확보 시도 중... ---")  # 2단계 시작
        image_url = supabase.storage.from_('test-clothes-imgaes').get_public_url(storage_path)  # 주소를 생성
        print(f"🔗 이미지 URL 확보: {image_url}")  # 생성된 주소를 터미널에 출력