from db import service_supabase

def restore_memberships():
    print("--- Restoring Legacy Membership Identity ---")
    
    NEW_ID = "2ae8b5e0-11e9-4ad5-bab6-5fc321a195a0"
    LEGACY_SEOUL_ID = "7662acf7-89a4-49b7-97ed-ad94a4a548aa" # 정재훈2
    LEGACY_MUMBAI_ID = "0014c533-ad54-42a3-b2cf-b5eb49eae54e" # 정재훈 (legacy)

    # Find all topics where NEW_ID is a member
    try:
        res = service_supabase.table("chat_topic_members").select("topic_id").eq("user_id", NEW_ID).execute()
        current_topics = [t['topic_id'] for t in res.data]
        print(f"Current User {NEW_ID} is in {len(current_topics)} topics.")
        
        # We'll put the legacy IDs back in THESE same topics.
        # This is an approximation since we don't know exactly which legacy ID was in which topic originally,
        # but since they all belong to the same user (just separate accounts), giving them all access is safe.
        for tid in current_topics:
            for old_id in [LEGACY_SEOUL_ID, LEGACY_MUMBAI_ID]:
                print(f" - Adding {old_id} to Topic {tid}...")
                service_supabase.table("chat_topic_members").upsert({
                    "topic_id": tid,
                    "user_id": old_id,
                    "permission_level": "member"
                }).execute()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    restore_memberships()
