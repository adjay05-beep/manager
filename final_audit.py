from db import service_supabase

def final_count_check():
    ADJAY_ID = "2ae8b5e0-11e9-4ad5-bab6-5fc321a195a0"
    JUWAL_ID = "020de13f-a84d-4441-8cd2-b03f4780dc19"
    
    print("--- Final Accessibility Audit ---")
    
    for uid, label in [(ADJAY_ID, "adjay (정재훈)"), (JUWAL_ID, "juwal (정재훈24)")]:
        print(f"\nUser: {label}")
        # Channel Memberships
        res_c = service_supabase.table("channel_members").select("*").eq("user_id", uid).execute()
        print(f" - Channel Memberships: {len(res_c.data)}")
        
        # Topic Memberships
        res_t = service_supabase.table("chat_topic_members").select("*").eq("user_id", uid).execute()
        print(f" - Topic Memberships: {len(res_t.data)}")
        
        # Messages
        res_m = service_supabase.table("chat_messages").select("id", count="exact").eq("user_id", uid).execute()
        print(f" - Total Messages Sent: {res_m.count}")

if __name__ == "__main__":
    final_count_check()
