from db import service_supabase

def check_channel1_topics():
    CHAN_ID = 1
    print(f"--- Topics and Members for Channel {CHAN_ID} (주월 사당점) ---")
    try:
        # Get topics for channel 1
        res_t = service_supabase.table("chat_topics").select("id, name").eq("channel_id", CHAN_ID).execute()
        for t in res_t.data:
            print(f"\nTopic {t['id']} ({t['name']}):")
            # Get members
            res_m = service_supabase.table("chat_topic_members").select("user_id").eq("topic_id", t['id']).execute()
            for m in res_m.data:
                # Find profile name if possible
                p_res = service_supabase.table("profiles").select("full_name").eq("id", m['user_id']).execute()
                name = p_res.data[0]['full_name'] if p_res.data else f"Unknown ({m['user_id']})"
                print(f"  - {name} ({m['user_id']})")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_channel1_topics()
