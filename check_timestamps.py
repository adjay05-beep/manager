from db import service_supabase
import datetime

def check_timestamp_sync():
    uid = "2ae8b5e0-11e9-4ad5-bab6-5fc321a195a0"
    print(f"--- Timestamp Sync Report for {uid} ---")
    
    # 1. Get User Reading Status
    res_read = service_supabase.table("chat_user_reading").select("*").eq("user_id", uid).execute()
    reading_status = {r['topic_id']: r['last_read_at'] for r in res_read.data}
    
    # 2. For each topic, find the latest message NOT sent by user
    for tid, last_read in reading_status.items():
        print(f"\nTopic {tid}:")
        print(f" - Last Read At: {last_read}")
        
        res_msg = service_supabase.table("chat_messages")\
            .select("id, created_at, user_id")\
            .eq("topic_id", tid)\
            .neq("user_id", uid)\
            .order("created_at", desc=True)\
            .limit(1).execute()
            
        if res_msg.data:
            latest_msg_at = res_msg.data[0]['created_at']
            print(f" - Latest Other Msg: {latest_msg_at}")
            
            # Compare
            try:
                # Basic string comparison usually works for ISO if formats are identical
                if latest_msg_at > last_read:
                    print(" ! Problem: Message is NEWER than last_read.")
                else:
                    print(" ✓ Success: Message is OLDER than or equal to last_read.")
            except Exception as e:
                print(f" ! Comparison Error: {e}")
        else:
            print(" - No other messages in this topic.")

    # 3. Check what unread_counts_view sees
    res_v = service_supabase.table("unread_counts_view").select("*").eq("user_id", uid).execute()
    print(f"\nView Report: {len(res_v.data)} unread items reported.")
    for row in res_v.data:
        print(f" - Topic {row['topic_id']}: {row['unread_count']}")

if __name__ == "__main__":
    check_timestamp_sync()
