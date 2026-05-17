import os
import time
import traceback
from dotenv import load_dotenv
from supabase import create_client

# [수정 1] 상대 경로 에러 방지 (서버 실행 위치 기준)
try:
    from services.ai_classifier import analyze_cloth
except ImportError:
    from ai_classifier import analyze_cloth

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

def process_user_upload(file_path, user_id): 
    # 파일명 중복 방지를 위한 타임스탬프 기반 이름 생성
    storage_path = f"cloth_{int(time.time())}.jpg"

    try:
        # 1단계: AI 분석 (사용자가 업로드 버튼을 눌렀을 때만 호출됨)
        print(f"\n[서버 로그] 1단계: AI 의류 분석 시작 (파일: {file_path})")
        ai_result = analyze_cloth(file_path)
        
        # 에러 체크
        if "error" in ai_result:
            raise Exception(f"AI 분석 실패: {ai_result['error']}")

        print(f"[서버 로그] AI 분석 완료: {ai_result['name']} / {ai_result['color']}")

        # 2단계: Supabase Storage 업로드
        print("[서버 로그] 2단계: Storage 업로드 중...")
        with open(file_path, 'rb') as f:
            supabase.storage.from_('test-clothes-imgaes').upload(
                path=storage_path,
                file=f
            )

        # 3단계: 이미지 URL 확보
        image_url = supabase.storage.from_('test-clothes-imgaes').get_public_url(storage_path)

        # 4단계: DB 저장 데이터 구성
        data = {
            "user_id": user_id,
            "main_category": ai_result["main_category"],
            "sub_category": ai_result["sub_category"],
            "name": ai_result["name"],
            "temp_level": 5, # 기본값 설정
            "color": ai_result["color"],
            "style": ai_result["style"],
            "image_url": image_url,
            "is_verified": False
        }

        print("[서버 로그] 3단계: DB 데이터 Insert 시도...")
        response = supabase.table('clothes').insert(data).execute()
        
        print("[서버 로그] ✅ 모든 단계 성공: DB 저장 완료")
        return response.data[0]

    except Exception as e:
        print(f"\n[서버 로그] ❌ 업로드 프로세스 에러: {e}")
        traceback.print_exc()
        return None

def confirm_ai_analysis(cloth_id, user_id):
    """AI 분석 결과 정확, 사용자가 승인하는 DB 로직"""
    try:
        update_data = {"is_verified": True}
        response = supabase.table('clothes').update(update_data).eq('id', cloth_id).eq('user_id', user_id).execute()
        return response.data
    except Exception as e:
        print(f"[DB 에러] 승인 업데이트 실패: {e}")
        return None

def modify_and_confirm_ai_analysis(cloth_id, user_id, modified_data):
    """사용자가 직접 수정한 데이터를 반영"""
    try:
        update_data = modified_data.copy()
        update_data["is_verified"] = True
        
        response = supabase.table('clothes').update(update_data).eq('id', cloth_id).eq('user_id', user_id).execute()
        return response.data
    except Exception as e:
        print(f"[DB 에러] 수정 및 승인 업데이트 실패: {e}")
        return None
    
def build_manual_cloth_data(user_id, input_data):
    """프론트엔드 전달 수동 입력 데이터를 DB 스키마에 맞게 구조화"""
    return {
        "user_id": user_id,
        "main_category": input_data.get("main_category", "상의"),
        "sub_category": input_data.get("sub_category", "이너"),
        "name": input_data.get("name", "기본 의류"),
        "temp_level": int(input_data.get("temp_level", 5)),
        "color": input_data.get("color", "#FFFFFF"),
        "style": input_data.get("style", []),
        "image_url": None,   
        "is_verified": True  
    }

def insert_manual_cloth_to_db(user_id, input_data):
    """구조화된 수동 입력 데이터를 Supabase DB에 직접 저장"""
    try:
        final_data = build_manual_cloth_data(user_id, input_data)
        response = supabase.table('clothes').insert(final_data).execute()
        print(f"[DB 로그] 수동 옷 등록 완료: {final_data['name']}")
        return response.data[0]
    except Exception as e:
        print(f"[DB 에러] 수동 옷 등록 실패: {e}")
        return None

# [수정 2] 로컬 테스트 블록 보호
# 서버 실행 시 이 부분이 지멋대로 실행되지 않도록 합니다.
if __name__ == "__main__": 
    # 테스트가 필요할 때만 아래 주석을 풀고 실행하세요.
    # TEST_FILE = "test2.jpg"
    # TEST_UUID = "your-test-uuid"
    # process_user_upload(TEST_FILE, TEST_UUID)
    pass