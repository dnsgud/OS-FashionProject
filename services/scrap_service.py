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

def get_user_scraps_with_details(user_email):
    """
    유저의 스크랩 이력을 조회한 뒤, 옷 ID들을 실제 상세 데이터와 결합하여 반환함
    """
    try:
        # 1. 스크랩 테이블 기본 이력 및 title 컬럼을 동시 조회
        scrap_response = supabase.table("scrapped_outfits") \
                                 .select("id, top_ids, bottom_id, title, created_at") \
                                 .eq("user_email", user_email) \
                                 .order("created_at", desc=True) \
                                 .execute()
        raw_scraps = scrap_response.data
        if not raw_scraps:
            return {"success": True, "scraps": []}

        scrapped_outfits_list = []

        for scrap in raw_scraps:
            scrap_id = scrap["id"]
            top_ids = scrap["top_ids"]
            bottom_id = scrap["bottom_id"]
            db_title = scrap.get("title")

            # 2. 상의 리스트 상세 정보 대량 조회
            top_response = supabase.table("clothes") \
                                   .select("id, main_category, sub_category, name, color, fit, image_url") \
                                   .in_("id", top_ids) \
                                   .execute()
            top_combo_details = top_response.data

            # 3. 하의 상세 정보 단일 조회
            bottom_response = supabase.table("clothes") \
                                     .select("id, main_category, sub_category, name, color, fit, image_url") \
                                     .eq("id", bottom_id) \
                                     .execute()
            bottom_details_list = bottom_response.data

            # 스크랩된 옷 중 옷장에서 완전히 영구 삭제된 아이템이 있다면 패스
            if not top_combo_details or not bottom_details_list:
                continue

            bottom_detail = bottom_details_list[0]
