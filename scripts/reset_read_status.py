import os
from dotenv import load_dotenv
from db import service_supabase

load_dotenv()

USER_ID = "ce89c5a4-7f97-4900-a89e-18a713c7968f" # adjay@naver.com
TOPIC_ID = "237" # Target topic from verification logs

def reset_read():
    print(f"--- Resetting Read Status for Topic {TOPIC_ID} ---")
    
    # Set last_read to yesterday
    yesterday = "2026-01-29T10:00:00+00:00"
    
    res = service_supabase.table("chat_user_reading").upsert({
        "topic_id": TOPIC_ID, 
        "user_id": USER_ID, 
        "last_read_at": yesterday
    }).execute()
    
    print(f"Reset Complete. New Last Read: {yesterday}")
    print("Please refresh the UI to see the badge.")

if __name__ == "__main__":
    reset_read()
