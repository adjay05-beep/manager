
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") # Use Service Key for updates

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Missing Supabase credentials in .env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# THE NEW UUID (from User's Screenshot)
NEW_UUID = "2ae8b5e0-11e9-4ad5-bab6-5fc321a195a0"
EMAIL = "adjay@naver.com"

def relink():
    # LIST of legacy IDs found via audit
    OLD_IDS = [
        "7662acf7-89a4-49b7-97ed-ad94a4a548aa", # '정재훈2' account
        "0014c533-ad54-42a3-b2cf-b5eb49eae54e"  # '정재훈' (legacy) account
    ]
    
    print(f"--- Relinking all detected legacy data to {NEW_UUID} ---")
    
    # Check if target exists
    res = supabase.table("profiles").select("*").eq("id", NEW_UUID).execute()
    if not res.data:
        print(f" ! Error: Target profile {NEW_UUID} does not exist.")
        return

    for OLD_ID in OLD_IDS:
        print(f"\n>> Processing Legacy ID: {OLD_ID}")
        
        # 1. Update child tables
        tables_to_update = [
            ("channels", "owner_id"),
            ("channel_members", "user_id"),
            ("chat_messages", "user_id"),
            ("chat_topics", "created_by"),
            ("chat_topic_members", "user_id"),
            ("chat_user_reading", "user_id"),
            ("handovers", "user_id"),
            ("voice_prompts", "user_id"),
            ("invite_codes", "created_by"),
            ("attendance_logs", "user_id")
        ]

        for table, col in tables_to_update:
            try:
                res = supabase.table(table).update({col: NEW_UUID}).eq(col, OLD_ID).execute()
                if len(res.data) > 0:
                    print(f"   ✓ {table}.{col}: {len(res.data)} rows updated")
            except Exception as e:
                print(f"   ! Error on {table}: {e}")

        # 2. Cleanup: Delete OLD profile
        try:
            supabase.table("profiles").delete().eq("id", OLD_ID).execute()
            print(f"   ✓ Legacy profile {OLD_ID} deleted.")
        except Exception as e:
            print(f"   ! Warning: Could not delete old profile: {e}")

    print("\n--- ALL RELINKING COMPLETE ---")

if __name__ == "__main__":
    relink()
