from db import service_supabase

def sync_adjay_topics():
    CHAN_ID = 1
    ADJAY_ID = "2ae8b5e0-11e9-4ad5-bab6-5fc321a195a0"
    
    print(f"--- Syncing All Topics for ADJAY in Channel {CHAN_ID} ---")
    
    try:
        res_t = service_supabase.table("chat_topics").select("id, name").eq("channel_id", CHAN_ID).execute()
        topics = res_t.data
        
        for t in topics:
            try:
                service_supabase.table("chat_topic_members").upsert({
                    "topic_id": t['id'],
                    "user_id": ADJAY_ID,
                    "permission_level": "member"
                }).execute()
            except:
                pass
            
        print("--- ADJAY SYNC COMPLETE ---")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    sync_adjay_topics()
