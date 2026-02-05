from db import service_supabase

def trace_channels():
    # Topics juwal was in
    topic_ids = [237, 244, 245, 80, 81]
    print(f"--- Tracing Channels for Topics {topic_ids} ---")
    
    try:
        res = service_supabase.table("chat_topics")\
            .select("id, name, channel_id")\
            .in_("id", topic_ids).execute()
        
        found_channels = set()
        for t in res.data:
            print(f" - Topic {t['id']} ({t['name']}) -> Channel: {t['channel_id']}")
            found_channels.add(t['channel_id'])
            
        print(f"\nUnique Channels identified: {found_channels}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    trace_channels()
