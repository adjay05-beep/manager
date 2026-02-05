from db import service_supabase

def sync_all_topics():
    CHAN_ID = 1
    ADJAY_ID = "2ae8b5e0-11e9-4ad5-bab6-5fc321a195a0"
    JUWAL_ID = "020de13f-a84d-4441-8cd2-b03f4780dc19"
    
    print(f"--- Syncing All Topics for {JUWAL_ID} in Channel {CHAN_ID} ---")
    
    try:
        # 1. Get all topics in Channel 1
        res_t = service_supabase.table("chat_topics").select("id, name").eq("channel_id", CHAN_ID).execute()
        topics = res_t.data
        print(f"Found {len(topics)} topics in Channel {CHAN_ID}.")
        
        # 2. Add juwal to all of them
        for t in topics:
            try:
                service_supabase.table("chat_topic_members").upsert({
                    "topic_id": t['id'],
                    "user_id": JUWAL_ID,
                    "permission_level": "member"
                }).execute()
                print(f"   ✓ Topic {t['id']} ({t['name']})")
            except Exception as e:
                if "duplicate key" in str(e).lower():
                    print(f"   - Topic {t['id']} (Already member)")
                else:
                    print(f"   ! Error on Topic {t['id']}: {e}")
            
        print("\n--- SYNC COMPLETE ---")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    sync_all_topics()
