from db import service_supabase

def final_check():
    TARGET_ID = "2ae8b5e0-11e9-4ad5-bab6-5fc321a195a0" # Current 정재훈
    print(f"--- Final Data Verification for {TARGET_ID} ---")
    
    tables = [
        ("chat_messages", "user_id"), 
        ("handovers", "user_id"), 
        ("chat_topics", "created_by"),
        ("chat_topic_members", "user_id")
    ]
    
    for t, col in tables:
        try:
            res = service_supabase.table(t).select(col, count="exact").eq(col, TARGET_ID).execute()
            print(f" - {t}: {res.count} rows")
        except Exception:
            print(f" - {t}: Error")

if __name__ == "__main__":
    final_check()
