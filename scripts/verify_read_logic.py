import os
import time
from dotenv import load_dotenv
from db import service_supabase
from pprint import pprint
from datetime import datetime

# Load env
load_dotenv()

# User ID from logs
USER_ID = "ce89c5a4-7f97-4900-a89e-18a713c7968f" # adjay@naver.com

def verify_logic():
    print(f"--- Verifying Unread Logic for User {USER_ID} ---")
    
    # 1. Get Topics
    print("1. Fetching Topics...")
    # Fetch topics for user (simulating get_topics logic simplified)
    # We need channel_id, let's just fetch all topics user is member of
    res = service_supabase.table("chat_topic_members").select("topic_id").eq("user_id", USER_ID).execute()
    tids = [r['topic_id'] for r in res.data]
    print(f"   Found {len(tids)} joined topics.")
    
    # 2. Get Read Status
    print("2. Fetching Read Status...")
    read_res = service_supabase.table("chat_user_reading").select("topic_id, last_read_at").eq("user_id", USER_ID).execute()
    read_map = {r['topic_id']: r['last_read_at'] for r in read_res.data}
    print(f"   Read Status Map: {len(read_map)} entries")
    # pprint(read_map)

    # 3. Check specific topics
    total_unread = 0
    
    for tid in tids:
        print(f"\n--- Checking Topic {tid} ---")
        last_read = read_map.get(tid)
        print(f"   Last Read: {last_read}")
        
        # Fetch latest messages
        msg_res = service_supabase.table("chat_messages")\
            .select("created_at, content")\
            .eq("topic_id", tid)\
            .neq("user_id", USER_ID)\
            .order("created_at", desc=True)\
            .limit(5)\
            .execute()
            
        msgs = msg_res.data
        if not msgs:
            print("   No messages from others.")
            continue
            
        print(f"   Latest Message: {msgs[0]['created_at']} | {msgs[0]['content'][:20]}")
        
        if not last_read:
            print("   => NEVER READ. Should be unread.")
            unreads = len(msgs) # simplified
        else:
            # Compare
            lr_dt = datetime.fromisoformat(last_read.replace('Z', '+00:00'))
            m_dt = datetime.fromisoformat(msgs[0]['created_at'].replace('Z', '+00:00'))
            
            if m_dt > lr_dt:
                print(f"   => UNREAD! ({m_dt} > {lr_dt})")
                total_unread += 1
            else:
                print(f"   => Read. ({m_dt} <= {lr_dt})")

    print(f"\n--- Summary ---")
    print(f"Total Detected Unread Topics: {total_unread}")

if __name__ == "__main__":
    verify_logic()
