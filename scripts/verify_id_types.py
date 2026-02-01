import os
from dotenv import load_dotenv
from db import service_supabase
from services import chat_service
import uuid

load_dotenv()

# User ID from Logs: 7662acf7-89a4-49b7-97ed-ad94a4a548aa (The user testing)
TEST_USER_ID = "7662acf7-89a4-49b7-97ed-ad94a4a548aa"
TEST_CHANNEL_ID = 1 # Assuming channel 1 for test
# We need a valid topic ID to pass to the function
# Let's just pick one or create a dummy structure if needed, but the service needs real DB access.
# I'll just call the service if I can find a topic.

def verify_types():
    print("--- Verifying ID Types ---")
    
    # 1. Fetch a topic
    res = service_supabase.table("chat_topics").select("id").limit(1).execute()
    if not res.data:
        print("No topics found.")
        return
    topic_id = res.data[0]['id']
    print(f"Topic ID: {topic_id} is {type(topic_id)}")
    
    # 2. Call the function
    print("Calling get_channel_members_not_in_topic...")
    candidates = chat_service.get_channel_members_not_in_topic(TEST_CHANNEL_ID, topic_id)
    
    if not candidates:
        print("No candidates found.")
    
    for c in candidates:
        uid = c['user_id']
        print(f"Candidate ID: {uid} | Type: {type(uid)}")
        
        # Simulation Check
        is_match = (uid == TEST_USER_ID)
        print(f"Direct Match with String '{TEST_USER_ID}': {is_match}")
        
        is_match_str = (str(uid).strip() == str(TEST_USER_ID).strip())
        print(f"Robust Match: {is_match_str}")
        
        # Exact Logic from chat_view.py
        can_id = str(uid).strip()
        current_uid = str(TEST_USER_ID).strip()
        
        log_msg = f"DEBUG_INVITE: Checking '{can_id}' vs '{current_uid}'"
        print(log_msg)
        
        if can_id == current_uid:
            print(">>> FILTER WOULD SUCCEED (MATCH) <<<")
        else:
            print(">>> FILTER WOULD FAIL (NO MATCH) <<<")

if __name__ == "__main__":
    verify_types()
