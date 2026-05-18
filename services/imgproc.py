import os
import time
import traceback
import re
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
    
def _is_valid_hex(color_str):
    """[알고리즘] 순수하게 헥사코드 형식이 맞는지 True/False만 반환하는 순수 함수"""
    if not color_str or not isinstance(color_str, str):
        return False
        
    pattern = r'^#(?:[0-9a-fA-F]{3}){1,2}$'
    return bool(re.match(pattern, color_str))

def _sanitize_color_input(color_str):
    """[알고리즘] 색상 값을 검증, 실패 시 안전한 기본값을 반환하는 래퍼 함수"""
    if _is_valid_hex(color_str):
        return color_str
    else:
        print(f"[알고리즘 경고] 비정상 색상 데이터 감지({color_str}). 기본값(#FFFFFF) 강제 적용.")
        return "#FFFFFF"
    
def build_manual_cloth_data(user_id, input_data):
    """프론트엔드 전달 수동 입력 데이터를 DB 스키마에 맞게 구조화"""
    # 3줄 이상의 명확한 정제 로직 전개
    raw_color = input_data.get("color", "#FFFFFF")
    safe_color = _sanitize_color_input(raw_color)
    input_data["color"] = safe_color  # 검증된 색상으로 원본 데이터 덮어쓰기

    return {
        "user_id": user_id,
        "main_category": input_data.get("main_category", "상의"),
        "sub_category": input_data.get("sub_category", "이너"),
        "name": input_data.get("name", "기본 의류"),
        "temp_level": int(input_data.get("temp_level", 5)),
        "color": input_data["color"],  # 정제 완료된 데이터 매핑
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

def handle_cloth_registration(register_type, user_id, payload):
    """
    사용자의 선택(register_type)에 따라 데이터 흐름을 분기하는 통합 알고리즘
    - 'photo': payload가 파일 경로(file_path)로 들어옴
    - 'manual': payload가 사용자가 입력한 딕셔너리(input_data)로 들어옴
    """
    if register_type == 'photo':
        print("[알고리즘 로그] 사진 등록 방식 선택 -> AI 분석 파이프라인으로 라우팅")
        return process_user_upload(payload, user_id)
        
    elif register_type == 'manual':
        print("[알고리즘 로그] 직접 등록 방식 선택 -> 수동 DB 저장 파이프라인으로 라우팅")
        return insert_manual_cloth_to_db(user_id, payload)
        
    else:
        print(f"[알고리즘 에러] 알 수 없는 등록 방식이다: {register_type}")
        return None

def _filter_closet_keys(edit_data):
    """[알고리즘] 허용된 컬럼만 통과시키는 내부 필터링 함수"""
    allowed = ['main_category', 'sub_category', 'name', 'temp_level', 'color', 'style']
    filtered = {k: v for k, v in edit_data.items() if k in allowed}
    return filtered

def _validate_closet_types(filtered_data):
    """[알고리즘] 데이터 무결성을 검증, 타입을 강제 변환하는 함수"""
    if not filtered_data:
        raise ValueError("유효한 수정 데이터가 존재 X.")
        
    if 'temp_level' in filtered_data:
        filtered_data['temp_level'] = int(filtered_data['temp_level'])
        
    
    if 'color' in filtered_data:
        original_color = filtered_data['color']
        safe_color = _sanitize_color_input(original_color)
        filtered_data['color'] = safe_color
        
    return filtered_data

def _execute_closet_update_query(cloth_id, user_id, clean_data):
    """[DB] Supabase에 접근하여 실제 업데이트 쿼리를 수행"""
    query = supabase.table('clothes').update(clean_data)
    response = query.eq('id', cloth_id).eq('user_id', user_id).execute()
    return response.data

def update_closet_cloth(cloth_id, user_id, edit_data):
    """옷장 의류 정보 수정을 위한 전체 데이터 파이프라인을 제어"""
    try:
        # 1. 분리해둔 모듈들을 순차적으로 실행
        filtered = _filter_closet_keys(edit_data)
        clean_data = _validate_closet_types(filtered)
        
        # 2. DB 업데이트 실행
        result = _execute_closet_update_query(cloth_id, user_id, clean_data)
        
        print(f"[DB 로그] 수정 완료: {cloth_id}")
        return result
    except Exception as e:
        print(f"[DB 에러] 파이프라인 수정 실패: {e}")
        return None

def _execute_unverified_delete_query(cloth_id, user_id):
    """[DB] 미승인 데이터 삭제 쿼리를 전담하여 실행하는 계층"""
    # 안전장치: eq('is_verified', False)를 DB 레벨에서 강제 적용
    query = supabase.table('clothes').delete()
    response = query.eq('id', cloth_id).eq('user_id', user_id).eq('is_verified', False).execute()
    
    return response.data

# [수정 2] 로컬 테스트 블록 보호
# 서버 실행 시 이 부분이 지멋대로 실행되지 않도록 함
if __name__ == "__main__": 
    # 테스트가 필요할 때만 아래 주석을 풀고 실행
    # TEST_FILE = "test2.jpg"
    # TEST_UUID = "your-test-uuid"
    # process_user_upload(TEST_FILE, TEST_UUID)
    pass