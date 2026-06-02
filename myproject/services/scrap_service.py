from config import supabase

# 코디 조합과 커스텀 이름을 데이터베이스에 저장하는 함수
def add_scrap_to_db(user_email, top_ids, bottom_id, shoes_id, custom_title):
    try:
        insert_payload = {
            "user_email": user_email,
            "top_ids": top_ids,
            "bottom_id": bottom_id,
            "shoes_id": shoes_id,
            "title": custom_title
        }
        res = supabase.table("scrapped_outfits").insert(insert_payload).execute()
        return {"success": True, "data": res.data}
    except Exception as e:
        return {"success": False, "error": str(e)}

# 스크랩된 코디를 유저 본인 확인 후 삭제하는 함수
def delete_scrap_from_db(scrap_id, user_email):
    try:
        response = supabase.table("scrapped_outfits") \
                           .delete() \
                           .eq("id", scrap_id) \
                           .eq("user_email", user_email) \
                           .execute()
        # 삭제 대상 데이터가 존재하지 않거나 권한이 없는지 체크하는 조건문
        if not response.data:
            return {"success": False, "error": "삭제 권한이 없거나 존재하지 않는 스크랩입니다."}
        return {"success": True, "message": "스크랩이 취소되었습니다."}
    except Exception as e:
        return {"success": False, "error": str(e)}

# 유저의 스크랩 이력을 상세 의류 데이터와 결합하여 반환하는 함수
def get_user_scraps_with_details(user_email):
    try:
        scrap_response = supabase.table("scrapped_outfits") \
                                 .select("id, top_ids, bottom_id, shoes_id, title, created_at") \
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
            shoes_id = scrap.get("shoes_id")
            db_title = scrap.get("title")

            top_response = supabase.table("clothes") \
                                   .select("id, main_category, sub_category, name, color, fit, image_url") \
                                   .in_("id", top_ids) \
                                   .execute()
            top_combo_details = top_response.data

            bottom_response = supabase.table("clothes") \
                                     .select("id, main_category, sub_category, name, color, fit, image_url") \
                                     .eq("id", bottom_id) \
                                     .execute()
            bottom_details_list = bottom_response.data

            if not top_combo_details or not bottom_details_list:
                continue

            bottom_detail = bottom_details_list[0]
            
            shoes_detail = None
            if shoes_id:
                shoes_response = supabase.table("clothes") \
                                         .select("id, main_category, sub_category, name, color, fit, image_url") \
                                         .eq("id", shoes_id) \
                                         .execute()
                if shoes_response.data:
                    shoes_detail = shoes_response.data[0]

            scrapped_outfits_list.append({
                "scrap_id": scrap_id,
                "title": db_title,
                "custom_title": db_title,
                "top_combo": top_combo_details,
                "bottom": bottom_detail,
                "shoes": shoes_detail,
                "created_at": scrap["created_at"]
            })

        return {"success": True, "scraps": scrapped_outfits_list}
    except Exception as e:
        return {"success": False, "error": str(e)}
