import os
import time  # 시간 모듈 추가
import traceback
from dotenv import load_dotenv
from supabase import create_client

# AI 모듈을 불러오기
from ai_classifier import analyze_cloth

load_dotenv()
url = os.getenv("SUPABASE_URL") # supabase 주소를 가져와 url에 저장
key = os.getenv("SUPABASE_KEY") # api 키를 가져와 key 변수에 저장
supabase = create_client(url, key)

# 함수가 '어떤 파일'을 '누구의 아이디'로 저장할지 밖에서 받을 수 있게 (매개변수) 수정
def process_user_upload(file_path, user_id): 
    storage_path = f"cloth_{int(time.time())}.jpg" #사진 파일의 이름을 time.time()이 현재 시간을 아주 정밀한 숫자로 알려주는것 이용

    try:
        # AI 분석을 가장 먼저 실행 (여기서 1~2초 소요됨)
        print("\n 1단계: AI 의류 분석 시작...")
        ai_result = analyze_cloth(file_path)
        print(f" AI 분석 완료: {ai_result['name']} ({ai_result['color']})")

        print("--- 2단계: Storage 업로드 시도 중... ---")
        with open(file_path, 'rb') as f:  # 사진 파일을 (rb) 모드로 열어 f라는 이름으로 사용
            supabase.storage.from_('test-clothes-imgaes').upload(  # 지정한 버킷에 접근하여 업로드를 실행
                path=storage_path,  # 위에서 정한 storage_path 이름으로 서버에 저장
                file=f  # 실제로 열어둔 파일 객체 f를 서버로 전송
            )

        print("--- 3단계: 이미지 URL 확보 시도 중... ---")
        image_url = supabase.storage.from_('test-clothes-imgaes').get_public_url(storage_path)  # 주소를 생성
        print(f"🔗 이미지 URL 확보: {image_url}")  # 생성된 주소를 터미널에 출력

        #가짜 데이터 대신 AI가 분석한 진짜 데이터(ai_result)를 삽입
        data = {
            "user_id": user_id,                              # 입력받은 실제 유저 ID
            "main_category": ai_result["main_category"],     # AI 결과
            "sub_category": ai_result["sub_category"],       # AI 결과
            "name": ai_result["name"],                       # AI 결과
            "temp_level": 5,                                 # (일단 고정)
            "color": ai_result["color"],                     # AI 결과 (#000000 등)
            "style": ai_result["style"],                     # AI 결과
            "image_url": image_url,                          # 방금 올린 스토리지 주소
            "ai_tags": ai_result["ai_tags"],                 # AI 원본 태그
            "is_verified": False
        }

        print("--- 4단계: DB 저장 시도 중... ---")
        response = supabase.table('clothes').insert(data).execute()#DB에 데이터가 삽입된 걸 검사하기 위한 작성
        print("모든단계 성공, DB에 데이터 저장완료")   
        print(f"새로운 옷 ID: {response.data[0]['id']}")
        
        return response.data[0] # 웹 서버 쪽에 성공했다고 결과를 돌려줌

    except Exception as e:# 예외 처리로 에러가 발생 시 프로그램이 갑자기 종료 방지
        print(f"\n [에러 발생]")
        print(f"에러 메시지: {e}")
        traceback.print_exc()
        return None

# 로컬 테스트용 블록
if __name__ == "__main__": 
    # 내 컴퓨터에서 먼저 잘 합쳐졌는지 테스트
    TEST_FILE = "test2.jpg"
    TEST_UUID = "YOUR UUID" # (DB에 있는 실제 uuid 값으로 테스트)
    
    process_user_upload(TEST_FILE, TEST_UUID)