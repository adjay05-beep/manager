from db import service_supabase

def find_orphan_memberships():
    print("--- Searching for Orphaned Channel Memberships ---")
    try:
        # Get all profiles
        res_p = service_supabase.table("profiles").select("id").execute()
        known_ids = set(p['id'] for p in res_p.data)
        
        # Get all channel members
        res_m = service_supabase.table("channel_members").select("*").execute()
        
        orphans = [m for m in res_m.data if m['user_id'] not in known_ids]
        
        print(f"Total memberships: {len(res_m.data)}")
        print(f"Orphaned memberships: {len(orphans)}")
        
        for o in orphans:
            print(f" - Orphan UID: {o['user_id']} | Channel ID: {o['channel_id']} | Role: {o.get('role')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_orphan_memberships()
