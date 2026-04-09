import os
import time  # 시간 모듈 추가
import traceback
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL") # supabase 주소를 가져와 url에 저장
key = os.getenv("SUPABASE_KEY") # api 키를 가져와 key 변수에 저장
supabase = create_client(url, key) # 주소와 키 사용하여 실제 supabase 접속 객체 생성

def step2_db_integration():  # DB 연동 작업을 수행하는 함수를 정의
    file_path = "test.jpg"  # 로컬에 저장되어 있는 이미지 파일의 경로를 지정
    storage_path = f"test_{int(time.time())}.jpg" #사진 파일의 이름을 time.time()이 현재 시간을 아주 정밀한 숫자로 알려주는것 이용

    try:
        print("\n--- 1단계 Storage 업로드 시도 중... ---")  # 작업 시작을 알리는 로그를 출력
        with open(file_path, 'rb') as f:  # 사진 파일을 (rb) 모드로 열어 f라는 이름으로 사용
            supabase.storage.from_('test-clothes-imgaes').upload(  # 지정한 버킷에 접근하여 업로드를 실행
                path=storage_path,  # 위에서 정한 storage_path 이름으로 서버에 저장
                file=f  # 실제로 열어둔 파일 객체 f를 서버로 전송
            )

        print("--- 2단계 이미지 URL 확보 시도 중... ---")  # 2단계 시작
        image_url = supabase.storage.from_('test-clothes-imgaes').get_public_url(storage_path)  # 주소를 생성
        print(f"🔗 이미지 URL 확보: {image_url}")  # 생성된 주소를 터미널에 출력
    
        MY_USER_ID = "UUID"  # 내 계정의 고유 아이디 값을 변수에 담기

        data = {  # 테이블 컬럼에 맞춰서 데이터를 딕셔너리로 묶음
            "user_id": MY_USER_ID,
            "main_category": "상의",
            "sub_category": "이너",
            "name": "직접 찍은 테스트 옷",
            "temp_level": 5,
            "color": "black",
            "style": ["캐주얼"],
            "image_url": image_url,
            "ai_tags": ["direct_photo", "test"],
            "is_verified": False
        }

        print("--- 3단계 DB 저장 시도 중... ---")
        response = supabase.table('clothes').insert(data).execute()#DB에 데이터가 삽입된 걸 검사하기 위한 작성
        print("모든단계 성공, DB에 데이터 저장완료")   
        print(f"새로운 옷 ID: {response.data[0]['id']}")

    except Exception as e:# 예외 처리로 에러가 발생 시 프로그램이 갑자기 종료 방지
        print(f"\n❌ [에러 발생] 몇 단계에서 멈췄는지 확인")#에러 발생시 정확히 확인하기 위한 코드 작성
        print(f"에러 메시지: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__": 
    step2_db_integration() #정의해둔 함수 실행하여 프로그램 시작