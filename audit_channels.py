from db import service_supabase

def audit_all_members():
    print("--- Audit of All Channel Memberships ---")
    try:
        res = service_supabase.table("channel_members").select("user_id, channel_id, role").execute()
        print(f"Total memberships: {len(res.data)}")
        for m in res.data:
             print(f" - UID: {m['user_id']} | PID: {m['channel_id']} | Role: {m.get('role')}")
             
        print("\n--- Audit of All Channels (Owners) ---")
        res_c = service_supabase.table("channels").select("id, name, owner_id").execute()
        for c in res_c.data:
             print(f" - Chan: {c['name']} ({c['id']}) | Owner: {c['owner_id']}")
             
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    audit_all_members()
