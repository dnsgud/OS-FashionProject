import os
import time  
import traceback
import re
from dotenv import load_dotenv
from supabase import create_client

# [경로 수정] app.py(최상단)에서 실행되므로 services 패키지 경로를 명시
try:
    from services.ai_classifier import analyze_cloth
except ImportError:
    from ai_classifier import analyze_cloth

load_dotenv()
url = os.getenv("SUPABASE_URL") 
key = os.getenv("SUPABASE_KEY") 
supabase = create_client(url, key)

# ==========================================
# 1. 의류 사진 업로드 및 AI 분석 파이프라인 (첫 번째 코드 유지)
# ==========================================
def process_user_upload(file_path, user_email): 
    storage_path = f"cloth_{int(time.time())}.jpg" 

    try:
        # AI 분석을 가장 먼저 실행
        print(f"\n[서버 로그] 1단계: AI 의류 분석 시작 (파일: {file_path})")
        ai_result = analyze_cloth(file_path)
        
        if "error" in ai_result:
            raise Exception(f"AI 분석 실패: {ai_result['error']}")
            
        print(f"[서버 로그] AI 분석 완료: {ai_result['name']} ({ai_result['color']})")

        print("[서버 로그] 2단계: Storage 업로드 시도 중...")
        with open(file_path, 'rb') as f:  
            supabase.storage.from_('test-clothes-imgaes').upload(  
                path=storage_path,  
                file=f  
            )

        print("[서버 로그] 3단계: 이미지 URL 확보 시도 중...")
        image_url = supabase.storage.from_('test-clothes-imgaes').get_public_url(storage_path)  
        print(f"🔗 이미지 URL 확보: {image_url}")  

        # 가짜 데이터 대신 AI가 분석한 진짜 데이터(ai_result)를 삽입
        data = {
            "user_email": user_email,                        # app.py와 컬럼명 완벽 매칭
            "main_category": ai_result["main_category"],     
            "sub_category": ai_result["sub_category"],       
            "name": ai_result["name"],                       
            "temp_level": 5,                                 
            "color": ai_result["color"],                     
            "style": ai_result["style"],                     
            "image_url": image_url,                          
            "ai_tags": ai_result.get("ai_tags", []),         # 삭제되었던 AI 원본 태그 DB 저장 복구!
            "is_verified": False
        }

        print("[서버 로그] 4단계: DB 저장 시도 중...")
        response = supabase.table('clothes').insert(data).execute()
        
        print("[서버 로그] ✅ 모든 단계 성공: DB 저장 완료")   
        return response.data[0] 

    except Exception as e:
        print(f"\n[서버 로그] ❌ 업로드 프로세스 에러")
        print(f"에러 메시지: {e}")
        traceback.print_exc()
        return None


# ==========================================
# 2. AI 분석 결과 승인 및 수정 모듈 (user_email 구조로 변경)
# ==========================================
def confirm_ai_analysis(cloth_id, user_email):
    """AI 분석 결과 정확, 사용자가 승인하는 DB 로직"""
    try:
        update_data = {"is_verified": True}
        response = supabase.table('clothes').update(update_data).eq('id', cloth_id).eq('user_email', user_email).execute()
        return response.data
    except Exception as e:
        print(f"[DB 에러] 승인 업데이트 실패: {e}")
        return None

def modify_and_confirm_ai_analysis(cloth_id, user_email, modified_data):
    """사용자가 직접 수정한 데이터를 반영"""
    try:
        update_data = modified_data.copy()
        update_data["is_verified"] = True
        
        response = supabase.table('clothes').update(update_data).eq('id', cloth_id).eq('user_email', user_email).execute()
        return response.data
    except Exception as e:
        print(f"[DB 에러] 수정 및 승인 업데이트 실패: {e}")
        return None


# ==========================================
# 3. 수동 의류 등록 모듈 (사진 업로드 및 Fit 확장 버전)
# ==========================================
def _is_valid_hex(color_str):
    """[알고리즘] 순수하게 헥사코드 형식이 맞는지 True/False만 반환하는 순수 함수이다."""
    if not color_str or not isinstance(color_str, str):
        return False
        
    pattern = r'^#(?:[0-9a-fA-F]{3}){1,2}$'
    return bool(re.match(pattern, color_str))

def _sanitize_color_input(color_str):
    """[알고리즘] 색상 값을 검증, 실패 시 안전한 기본값을 반환하는 래퍼 함수이다."""
    if _is_valid_hex(color_str):
        return color_str
    else:
        print(f"[알고리즘 경고] 비정상 색상 데이터 감지({color_str}). 기본값(#FFFFFF) 강제 적용.")
        return "#FFFFFF"

def _upload_to_storage(file_path):
    """[스토리지] 수동 등록 시 넘어온 이미지를 Supabase에 업로드하고 URL을 반환한다."""
    if not file_path or not os.path.exists(file_path):
        return None
    
    storage_path = f"manual_cloth_{int(time.time())}.jpg"
    try:
        with open(file_path, 'rb') as f:
            supabase.storage.from_('test-clothes-imgaes').upload(path=storage_path, file=f)
        return supabase.storage.from_('test-clothes-imgaes').get_public_url(storage_path)
    except Exception as e:
        print(f"[스토리지 에러] 수동 이미지 업로드 실패: {e}")
        return None

def build_manual_cloth_data(user_email, input_data, image_url=None):
    """프론트엔드 전달 수동 입력 데이터를 DB 스키마에 맞게 구조화한다."""
    raw_color = input_data.get("color", "#FFFFFF")
    safe_color = _sanitize_color_input(raw_color)
    input_data["color"] = safe_color  

    return {
        "user_email": user_email,
        "main_category": input_data.get("main_category", "상의"),
        "sub_category": input_data.get("sub_category", "이너"),
        "name": input_data.get("name", "기본 의류"),
        "temp_level": int(input_data.get("temp_level", 5)),
        "color": input_data["color"], 
        "style": input_data.get("style", []),
        "fit": input_data.get("fit", "레귤러핏"),    # [추가] 프론트엔드에서 선택한 핏 매핑
        "image_url": image_url,                   # [수정] Storage에서 발급받은 URL 삽입
        "is_verified": True  
    }

def insert_manual_cloth_to_db(user_email, input_data, file_path=None):
    """구조화된 수동 입력 데이터를 Supabase DB에 직접 저장한다."""
    try:
        # 사진 파일이 전달된 경우 스토리지에 먼저 업로드한다.
        image_url = None
        if file_path:
            print("[알고리즘 로그] 수동 등록 이미지 스토리지 업로드 시도 중...")
            image_url = _upload_to_storage(file_path)

        final_data = build_manual_cloth_data(user_email, input_data, image_url)
        response = supabase.table('clothes').insert(final_data).execute()
        print(f"[DB 로그] 수동 옷 등록 완료: {final_data['name']}")
        return response.data[0]
    except Exception as e:
        print(f"[DB 에러] 수동 옷 등록 실패: {e}")
        return None

def handle_cloth_registration(register_type, user_email, payload, file_path=None):
    """
    사용자의 선택(register_type)에 따라 데이터 흐름을 분기하는 통합 알고리즘이다.
    """
    if register_type == 'photo':
        print("[알고리즘 로그] 사진 등록 방식 선택 -> AI 분석 파이프라인으로 라우팅")
        return process_user_upload(file_path, user_email) # payload 대신 명확하게 file_path 사용
        
    elif register_type == 'manual':
        print("[알고리즘 로그] 직접 등록 방식 선택 -> 수동 DB 저장 파이프라인으로 라우팅")
        # 수동 등록 시 텍스트 딕셔너리(payload)와 사진(file_path)을 함께 넘기도록 구조를 개선했다.
        return insert_manual_cloth_to_db(user_email, payload, file_path)
        
    else:
        print(f"[알고리즘 에러] 알 수 없는 등록 방식이다: {register_type}")
        return None

# ==========================================
# 4. 옷장 데이터 수정 및 삭제 모듈 (user_email 구조로 변경)
# ==========================================
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

def _execute_closet_update_query(cloth_id, user_email, clean_data):
    """[DB] Supabase에 접근하여 실제 업데이트 쿼리를 수행"""
    query = supabase.table('clothes').update(clean_data)
    response = query.eq('id', cloth_id).eq('user_email', user_email).execute()
    return response.data

def update_closet_cloth(cloth_id, user_email, edit_data):
    """옷장 의류 정보 수정을 위한 전체 데이터 파이프라인을 제어"""
    try:
        filtered = _filter_closet_keys(edit_data)
        clean_data = _validate_closet_types(filtered)
        
        result = _execute_closet_update_query(cloth_id, user_email, clean_data)
        
        print(f"[DB 로그] 수정 완료: {cloth_id}")
        return result
    except Exception as e:
        print(f"[DB 에러] 파이프라인 수정 실패: {e}")
        return None

def _execute_unverified_delete_query(cloth_id, user_email):
    """[DB] 미승인 데이터 삭제 쿼리를 전담하여 실행하는 계층"""
    query = supabase.table('clothes').delete()
    response = query.eq('id', cloth_id).eq('user_email', user_email).eq('is_verified', False).execute()
    return response.data

def delete_unverified_cloth(cloth_id, user_email):
    """미승인 임시 데이터를 삭제하는 메인 컨트롤러 함수"""
    try:
        deleted_data = _execute_unverified_delete_query(cloth_id, user_email)
        
        if deleted_data:
            print(f"[DB 로그] 미승인 데이터 삭제(Rollback) 완료: {cloth_id}")
            return True
            
        print(f"[DB 경고] 삭제할 미승인 데이터가 없거나 조건 불일치: {cloth_id}")
        return False
        
    except Exception as e:
        print(f"[DB 에러] 미승인 데이터 삭제 파이프라인 실패: {e}")
        return False


# [수정 2] 로컬 테스트 블록 보호
if __name__ == "__main__": 
    pass