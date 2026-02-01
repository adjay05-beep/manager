import os
import time
from dotenv import load_dotenv
from db import service_supabase
from services import chat_service
from pprint import pprint

load_dotenv()

# User B (Receiver - adjay)
USER_B_ID = "ce89c5a4-7f97-4900-a89e-18a713c7968f"

# Target Topic
TOPIC_ID = "237" 

def verify_receiver():
    print(f"--- Simulating Message from A -> B (Topic {TOPIC_ID}) ---")

    # 0. Get a valid sender (anyone who is NOT B)
    p_res = service_supabase.table("profiles").select("id").neq("id", USER_B_ID).limit(1).execute()
    if not p_res.data:
        print("ERROR: No other users found to simulate sender.")
        return
    USER_A_ID = p_res.data[0]['id']
    print(f"[0] Simulation Sender: {USER_A_ID}")
    
    # 1. Check B's current status
    print("[1] Checking B's initial state...")
    read_map = chat_service.get_user_read_status(USER_B_ID)
    last_read = read_map.get(TOPIC_ID)
    print(f"    B's Last Read: {last_read}")
    
    # 2. Simulate A sending a message
    print("\n[2] A is sending a message...")
    msg_content = f"Test Message at {time.time()}"
    res = service_supabase.table("chat_messages").insert({
        "topic_id": TOPIC_ID,
        "content": msg_content,
        "user_id": USER_A_ID
    }).execute()
    new_msg = res.data[0]
    print(f"    Sent: {new_msg['created_at']} | id={new_msg['id']}")
    
    # 3. Check Unread Count for B
    print("\n[3] Calculating Unread Count for B...")
    # Fetch topics struct strictly for the function
    topics = [{"id": TOPIC_ID}] 
    
    counts = chat_service.get_unread_counts(USER_B_ID, topics)
    print(f"    Unread Counts Result: {counts}")
    
    val = counts.get(TOPIC_ID) or counts.get(str(TOPIC_ID))
    
    if val and val > 0:
        print("\n✅ SUCCESS: Unread count detected!")
    else:
        print("\n❌ FAILURE: Unread count is ZERO.")
        
        # Diagnostics if fail
        print("    DIAGNOSTICS:")
        print(f"    Message Time: {new_msg['created_at']}")
        print(f"    Last Read:    {last_read}")
        if last_read and new_msg['created_at'] > last_read:
             print("    Logic Error: Msg is clearly newer than Read, but not counted.")
        else:
             print("    Data Error: Read timestamp weirdly updated?")

if __name__ == "__main__":
    verify_receiver()
