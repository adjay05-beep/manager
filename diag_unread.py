
import os
import sys
import datetime
from db import service_supabase

def diag_unread():
    print("--- Diagnostic: Unread Counts ---")
    
    # Hardcoded from logs
    user_id = "ce89c5a4-7f97-4900-a89e-18a713c7968f"
    print(f"Targeting User ID: {user_id}")
    
    # 2. Get topics for this user
    # topic_id = "237"
    topic_ids = ["237"]
    print(f"Targeting Topic ID: 237")
    
    if not topic_ids:
        print("User has no topics.")
        return

    # Pick the first topic
    topic_id = topic_ids[0]
    print(f"Checking Topic ID: {topic_id}")
    
    # 3. Get latest message in this topic
    msgs = service_supabase.table("chat_messages").select("id, created_at, content").eq("topic_id", topic_id).order("created_at", desc=True).limit(1).execute()
    if msgs.data:
        print(f"Latest Message: {msgs.data[0]['created_at']} - {msgs.data[0]['content'][:20]}...")
        last_msg_at = msgs.data[0]['created_at']
    else:
        print("No messages in topic.")
        return

    # 4. Get current Read Status
    read_res = service_supabase.table("chat_user_reading").select("*").eq("user_id", user_id).eq("topic_id", topic_id).execute()
    if read_res.data:
        print(f"Current Read Status: {read_res.data[0]['last_read_at']}")
        last_read_at = read_res.data[0]['last_read_at']
    else:
        print("No Read Status record found (Never read).")
        last_read_at = None
        
    # 5. Check View Output
    view_res = service_supabase.table("unread_counts_view").select("*").eq("user_id", user_id).eq("topic_id", topic_id).execute()
    print(f"View Result: {view_res.data}")
    
    # 6. Simulate Read
    print("--- Simulating Read (Updating Timestamp) ---")
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"Setting last_read_at to: {now_utc}")
    
    upsert_res = service_supabase.table("chat_user_reading").upsert({
        "user_id": user_id,
        "topic_id": topic_id,
        "last_read_at": now_utc
    }).execute()
    
    print("Upsert executed.")
    
    # 7. Check View Output Again
    view_res_after = service_supabase.table("unread_counts_view").select("*").eq("user_id", user_id).eq("topic_id", topic_id).execute()
    print(f"View Result After: {view_res_after.data}")
    
if __name__ == "__main__":
    diag_unread()
