import os
import time  
import traceback
from dotenv import load_dotenv
from supabase import create_client

try:
    from services.ai_classifier import analyze_cloth
except ImportError:
    from ai_classifier import analyze_cloth

load_dotenv()
url = os.getenv("SUPABASE_URL") 
key = os.getenv("SUPABASE_KEY") 
supabase = create_client(url, key)

def process_user_upload(file_path, user_email): 
    storage_path = f"cloth_{int(time.time())}.jpg" 

    try:
        # 1단계: AI 분석 가동
        print(f"\n[서버 로그] 1단계: AI 의류 분석 시작 (파일: {file_path})")
        ai_result = analyze_cloth(file_path)
        
        if "error" in ai_result:
            raise Exception(f"AI 분석 실패: {ai_result['error']}")
            
        print(f"[서버 로그] AI 분석 결과 -> 대분류: {ai_result['main_category']}, 중분류: {ai_result['sub_category']}")

        # 2단계: Supabase Storage 업로드
        print("[서버 로그] 2단계: Storage 업로드 시도 중...")
        with open(file_path, 'rb') as f:  
            supabase.storage.from_('test-clothes-imgaes').upload(path=storage_path, file=f)

        # 3단계: 이미지 공개 URL 확보
        print("[서버 로그] 3단계: 이미지 URL 확보 시도 중...")
        image_url = supabase.storage.from_('test-clothes-imgaes').get_public_url(storage_path)  

        # 4단계: [교정] Supabase 테이블 컬럼 규격(text 타입) 및 없는 컬럼 완전 제거
        data = {
            "user_email": user_email,                        
            "main_category": ai_result["main_category"],     
            "sub_category": ai_result["sub_category"],       
            "name": ai_result["name"],                       
            "temp_level": "5",                               # ◀ [교정] 숫자 5에서 문자열 "5"로 변경 (DB 타입 일치)
            "color": ai_result["color"],                     
            "style": ai_result["style"],                     
            "image_url": image_url,                          
            "ai_tags": [ai_result["main_category"], ai_result["sub_category"], ai_result["style"]]
            # ◀ [교정] 테이블에 존재하지 않는 "is_verified" 컬럼 제거 완료!
        }

        print("[서버 로그] 4단계: DB 저장 시도 중...")
        response = supabase.table('clothes').insert(data).execute()
        
        print("[서버 로그] ✅ 모든 파이프라인 연동 성공! 옷장 등록이 완료되었습니다.")   
        return response.data

    except Exception as e:
        print(f"\n[서버 로그] ❌ 업로드 프로세스 에러 발생 원인")
        traceback.print_exc()
        return None
