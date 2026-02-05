from db import service_supabase

def find_orphans():
    print("--- Searching for Orphaned Data (IDs not in Profiles) ---")
    
    # 1. Get all known profile IDs
    try:
        res_p = service_supabase.table("profiles").select("id").execute()
        known_ids = set(p['id'] for p in res_p.data)
        print(f"Known Profile IDs: {len(known_ids)}")
    except Exception as e:
        print(f"Error fetching profiles: {e}")
        return

    # 2. Check child tables for foreign keys not in known_ids
    tables_to_check = [
        ("channels", "owner_id"),
        ("channel_members", "user_id"),
        ("chat_messages", "user_id"),
        ("chat_topics", "created_by")
    ]

    orphan_candidates = {}

    for table, col in tables_to_check:
        try:
            res = service_supabase.table(table).select(col).execute()
            for row in res.data:
                uid = row.get(col)
                if uid and uid not in known_ids:
                    if uid not in orphan_candidates:
                        orphan_candidates[uid] = []
                    orphan_candidates[uid].append(table)
        except Exception as e:
            print(f"Error checking {table}: {e}")

    if not orphan_candidates:
        print("No orphaned data found. Checking if legacy data is under a name other than '정재훈'...")
        # Check profiles again
        res_all = service_supabase.table("profiles").select("*").execute()
        for p in res_all.data:
             print(f" - {p['id']} | {p.get('full_name')} | {p.get('username')}")
    else:
        print(f"\nFound {len(orphan_candidates)} Orphan IDs with existing data:")
        for uid, tables in orphan_candidates.items():
            print(f" - ID: {uid} | tables: {set(tables)}")

if __name__ == "__main__":
    find_orphans()
