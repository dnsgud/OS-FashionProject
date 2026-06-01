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
