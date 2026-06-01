from config import supabase

def add_scrap_to_db(user_email, top_ids, bottom_id, title=None): 
    """
    유저가 선택한 코디 조합과 커스텀 이름을 scrapped_outfits 테이블에 저장함
    """
    try:
        data = {
            "user_email": user_email,
            "top_ids": top_ids,  
            "bottom_id": bottom_id,
            "title": title
        }
        response = supabase.table("scrapped_outfits").insert(data).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        return {"success": False, "error": str(e)}

def delete_scrap_from_db(scrap_id, user_email):
    """
    유저가 스크랩북에서 삭제를 요청했을 때 본인 확인 후 안전하게 삭제함
    """
    try:
        response = supabase.table("scrapped_outfits") \
                           .delete() \
                           .eq("id", scrap_id) \
                           .eq("user_email", user_email) \
                           .execute()
        if not response.data:
            return {"success": False, "error": "삭제 권한이 없거나 존재하지 않는 스크랩입니다."}
        return {"success": True, "message": "스크랩이 취소되었습니다."}
    except Exception as e:
        return {"success": False, "error": str(e)}
