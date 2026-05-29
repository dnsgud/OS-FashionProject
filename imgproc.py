import os
import time  
import traceback
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

# [수정] 앱의 DB 구조가 이메일 기반이므로 파라미터 이름을 user_email로 맞춤
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

# 서버 실행 시 자동 실행 방지
if __name__ == "__main__": 
    pass
