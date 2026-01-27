import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
service_key = os.environ.get("SUPABASE_SERVICE_KEY")

async def main():
    print(f"URL: {url}")
    print(f"Service Key Present: {bool(service_key)}")
    
    # 1. Admin Client
    admin_client = create_client(url, service_key or key)
    
    # 2. Find User
    print("\n[1] Finding User adjay@naver.com...")
    # Cannot search auth.users easily via API without service role mapping or direct query?
    # Supabase-py admin auth list_users?
    try:
        # Note: list_users might require service role
        res = admin_client.auth.admin.list_users()
        target_user = None
        for u in res:
            if u.email == "adjay@naver.com":
                target_user = u
                break
        
        if not target_user:
            print("User NOT found in Auth!")
            return
        
        print(f"User Found: {target_user.id} ({target_user.email})")
        
        # 3. Check Channel Members (Admin)
        print("\n[2] Checking Channel Members (Admin View)...")
        cm_res = admin_client.table("channel_members").select("*").eq("user_id", target_user.id).execute()
        print(f"Rows found: {len(cm_res.data)}")
        for row in cm_res.data:
            print(row)
            
        # 4. Check RLS (Simulate User)
        print("\n[3] Checking RLS (User View)...")
        # Sign in to get token
        # We can't sign in without password. 
        # But we can assume if Admin sees it, data is there.
        # If User doesn't see it, it's RLS.
        
        # If we have rows in Admin check, then it is definitely RLS or Token issue.
        if len(cm_res.data) > 0:
            print("-> Data exists. If app fails, it is RLS policy or Token transmission.")
        else:
            print("-> Data MISSING. User needs to be re-added to store.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
