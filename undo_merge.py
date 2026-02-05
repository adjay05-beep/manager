from db import service_supabase

def reverse_merge():
    print("--- Reversing Data Merge (Restore Separation) ---")
    
    NEW_ID = "2ae8b5e0-11e9-4ad5-bab6-5fc321a195a0"
    LEGACY_SEOUL_ID = "7662acf7-89a4-49b7-97ed-ad94a4a548aa" # 정재훈2
    LEGACY_MUMBAI_ID = "0014c533-ad54-42a3-b2cf-b5eb49eae54e" # 정재훈 (legacy)

    # 1. Recreate Profiles
    profiles_to_restore = [
        {"id": LEGACY_SEOUL_ID, "full_name": "정재훈2", "username": "정재훈2", "role": "member"},
        {"id": LEGACY_MUMBAI_ID, "full_name": "정재훈", "username": "정재훈_Legacy", "role": "member"}
    ]
    
    for p in profiles_to_restore:
        print(f" - Restoring Profile: {p['id']} ({p['full_name']})...")
        try:
            service_supabase.table("profiles").upsert(p).execute()
            print("   ✓ Done")
        except Exception as e:
            print(f"   ! Error: {e}")

    # 2. Identify and Move Messages Back
    # We'll use the counts from the previous audit:
    # 0014... (Mumbai) : 4 messages
    # 7662... (Seoul-old) : 73 messages
    try:
        res = service_supabase.table("chat_messages").select("id").eq("user_id", NEW_ID).order("created_at").execute()
        all_msgs = res.data
        print(f"Total current messages for {NEW_ID}: {len(all_msgs)}")
        
        if len(all_msgs) >= 77:
            mumbai_msgs = [m['id'] for m in all_msgs[:4]]
            seoul_msgs = [m['id'] for m in all_msgs[4:77]] # 4 to 76 (73 msgs)
            
            print(f" - Moving {len(mumbai_msgs)} messages back to Mumbai ID...")
            service_supabase.table("chat_messages").update({"user_id": LEGACY_MUMBAI_ID}).in_("id", mumbai_msgs).execute()
            
            print(f" - Moving {len(seoul_msgs)} messages back to Seoul-Old ID...")
            service_supabase.table("chat_messages").update({"user_id": LEGACY_SEOUL_ID}).in_("id", seoul_msgs).execute()
        else:
            print(" ! Warning: Not enough messages to precisely reverse. Skipping message move.")
    except Exception as e:
        print(f" ! Message Move Error: {e}")

    # 3. Restore Handovers
    try:
        res_h = service_supabase.table("handovers").select("id").eq("user_id", NEW_ID).order("created_at").execute()
        handovers = res_h.data
        if len(handovers) >= 3:
             # Move oldest 3 back to Seoul-Old
             seoul_h = [h['id'] for h in handovers[:3]]
             print(f" - Moving {len(seoul_h)} handovers back to Seoul-Old ID...")
             service_supabase.table("handovers").update({"user_id": LEGACY_SEOUL_ID}).in_("id", seoul_h).execute()
    except Exception as e:
        print(f" ! Handover Move Error: {e}")

    # 4. Link Access (The important part for "separate but visible")
    # Add NEW_ID to all topics the old ones were in
    for old_id in [LEGACY_SEOUL_ID, LEGACY_MUMBAI_ID]:
        try:
            res_t = service_supabase.table("chat_topic_members").select("topic_id").eq("user_id", old_id).execute()
            topic_ids = [t['topic_id'] for t in res_t.data]
            print(f" - Granting shared access for {NEW_ID} to {len(topic_ids)} topics from {old_id}...")
            
            for tid in topic_ids:
                service_supabase.table("chat_topic_members").upsert({
                    "topic_id": tid, 
                    "user_id": NEW_ID,
                    "permission_level": "member"
                }).execute()
        except Exception as e:
             print(f" ! Access Link Error for {old_id}: {e}")

    print("--- REVERSAL COMPLETE ---")

if __name__ == "__main__":
    reverse_merge()
