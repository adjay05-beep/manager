from db import service_supabase

def list_all_channels():
    print("--- List of All Channels ---")
    try:
        res = service_supabase.table("channels").select("*").execute()
        for c in res.data:
             print(f" - [{c['id']}] {c['name']} | Owner: {c['owner_id']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_all_channels()
