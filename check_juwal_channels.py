from db import service_supabase

def check_channel_members():
    LEGACY_ID = "7662acf7-89a4-49b7-97ed-ad94a4a548aa" # 정재훈2
    CURRENT_ID = "020de13f-a84d-4441-8cd2-b03f4780dc19" # 정재훈24
    
    print(f"--- Channel Membership Check ---")
    
    for uid, label in [(LEGACY_ID, "Legacy (정재훈2)"), (CURRENT_ID, "Current (정재훈24)")]:
        try:
            res = service_supabase.table("channel_members").select("*").eq("user_id", uid).execute()
            print(f"\n{label} ({uid}): {len(res.data)} memberships")
            for m in res.data:
                 print(f" - Channel ID: {m['channel_id']} | Role: {m.get('role')}")
        except Exception as e:
            print(f"Error for {uid}: {e}")

if __name__ == "__main__":
    check_channel_members()
