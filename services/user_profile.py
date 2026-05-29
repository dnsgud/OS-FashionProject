import traceback

try:
    from config import supabase
except ImportError:
    pass

def fetch_user_profile(login_id):
    # 기존 프로필 데이터를 조회하여 프론트엔드 입력칸에 미리 노출하기 위한 로직
    if not login_id:
        return None
        
    try:
        
        query = supabase.table('users').select('login_id, email, name, nickname').eq('login_id', login_id).execute()
        
        if query.data:
            print(f"[DB 로그] 기존 프로필 데이터 로드 완료: {login_id}")
            return query.data[0]
            
        print("[알고리즘 에러] 조회 가능한 프로필 데이터가 존재 X")
        return None
        
    except Exception as e:
        print(f"[DB 에러] 프로필 데이터 조회 쿼리 실행 실패: {e}")
        return None