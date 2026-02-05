from db import service_supabase
import os

def diagnose():
    print("--- Diagnostic Report ---")
    
    # 1. Check Auth Users
    try:
        # We can't use auth.admin.list_users() easily without certain permissions, 
        # but we can try to find the user by email if we can join it or something.
        # Actually, let's just look at profiles again with more detail.
        res = service_supabase.table("profiles").select("*").execute()
        print(f"Profiles found: {len(res.data)}")
        for p in res.data:
             print(f" - {p['id']} | {p['full_name']} | {p['username']}")
    except Exception as e:
        print(f"Error fetching profiles: {e}")

    # 2. Check a few child tables for the 'ce89...' ID
    OLD_ID = "ce89c5a4-7f97-4900-a89e-18a713c7968f"
    NEW_ID = "2ae8b5e0-11e9-4ad5-bab6-5fc321a195a0" # The one I thought was new
    
    for uid in [OLD_ID, NEW_ID]:
        print(f"\nChecking data for {uid}:")
        for table in ["chat_topic_members", "chat_user_reading", "chat_messages"]:
            try:
                # Use count if possible
                res = service_supabase.table(table).select("id", count="exact").eq("user_id", uid).execute()
                print(f" - {table}: {res.count} rows")
            except Exception:
                # Try without count if it fails
                res = service_supabase.table(table).select("*").eq("user_id", uid).execute()
                print(f" - {table}: {len(res.data)} rows")

if __name__ == "__main__":
    diagnose()
