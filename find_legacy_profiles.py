from db import service_supabase

def find_profiles():
    EMAIL = "adjay@naver.com"
    print(f"--- Searching for Profiles associated with {EMAIL} ---")
    
    try:
        # 1. Search by email directly
        res = service_supabase.table("profiles").select("*").eq("email", EMAIL).execute()
        print(f"Profiles found for email '{EMAIL}': {len(res.data)}")
        for p in res.data:
            print(f" - ID: {p['id']} | Name: {p.get('full_name')} | Username: {p.get('username')}")
            
        # 2. Search for common names if email search yields only one
        if len(res.data) < 2:
            print("\nSearching by name variants (정재훈)...")
            res_name = service_supabase.table("profiles").select("*").or_("full_name.eq.정재훈,username.eq.정재훈").execute()
            for p in res_name.data:
                print(f" - ID: {p['id']} | Name: {p.get('full_name')} | Email: {p.get('email')}")

        # 3. Check Auth users (indirectly)
        # We know one NEW ID is likely '2ae8b5e0-11e9-4ad5-bab6-5fc321a195a0'
        # Let's see if there's ANOTHER one.
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_profiles()
