from db import service_supabase

def check_counts():
    uid = "2ae8b5e0-11e9-4ad5-bab6-5fc321a195a0"
    print(f"--- Checking Unread Counts for {uid} ---")
    
    try:
        res = service_supabase.table("unread_counts_view").select("*").eq("user_id", uid).execute()
        print(f"Unread topics found: {len(res.data)}")
        for row in res.data:
            print(f" - Topic {row['topic_id']}: {row['unread_count']} unread")
            
        if len(res.data) == 0:
            print("✓ No unread messages found for this user. Fix verified!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_counts()
