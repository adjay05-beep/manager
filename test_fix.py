from services import chat_service
from db import service_supabase

def test_service_logic():
    uid = "2ae8b5e0-11e9-4ad5-bab6-5fc321a195a0"
    print(f"--- Testing Service Logic for {uid} ---")
    
    # 1. Get topics for this user
    # We'll just mock a few topic objects for the service call
    topics = [
        {"id": 245, "name": "Topic 245"},
        {"id": 237, "name": "Topic 237"},
        {"id": 178, "name": "Topic 178"}
    ]
    
    # 2. Call the service
    counts = chat_service.get_unread_counts(uid, topics)
    print(f"Counts returned by service: {counts}")
    
    total = sum(counts.values())
    if total == 0:
        print("✓ Success: Total unread is 0. Fallback avoided!")
    else:
        print(f" ! Failure: Still seeing {total} unread messages.")

if __name__ == "__main__":
    test_service_logic()
