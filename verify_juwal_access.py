from db import service_supabase

def check_all_juwal_topics():
    JUWAL_ID = "020de13f-a84d-4441-8cd2-b03f4780dc19"
    print(f"--- Checking all Topics for {JUWAL_ID} ---")
    
    try:
        # 1. Get Topic IDs
        res_m = service_supabase.table("chat_topic_members").select("topic_id").eq("user_id", JUWAL_ID).execute()
        t_ids = [m['topic_id'] for m in res_m.data]
        print(f" User is in {len(t_ids)} topics: {t_ids}")
        
        # 2. Get Channels for these topics
        if t_ids:
            res_t = service_supabase.table("chat_topics").select("channel_id, name").in_("id", t_ids).execute()
            chans = set()
            for t in res_t.data:
                print(f" - Topic: {t['name']} -> Channel: {t['channel_id']}")
                chans.add(t['channel_id'])
            
            print(f"Total Unique Channels: {chans}")
            
            # 3. Verify Channel Memberships
            res_c = service_supabase.table("channel_members").select("channel_id").eq("user_id", JUWAL_ID).execute()
            existing_chans = [c['channel_id'] for c in res_c.data]
            print(f"User is currently a member of Channels: {existing_chans}")
            
            missing = chans - set(existing_chans)
            if missing:
                print(f" ! WARNING: User is in topics for channels {missing} but NOT in those channels.")
            else:
                print(" ✓ All channel memberships match topic presence.")
        else:
            print(" No topics found for this user.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_all_juwal_topics()
