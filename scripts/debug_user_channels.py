import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
service_key = os.environ.get("SUPABASE_SERVICE_KEY")

def main():
    print(f"URL: {url}")
    print(f"Service Key Present: {bool(service_key)}")
    
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json"
    }
    
    # 1. Find User via Admin API
    print("\n[1] Finding User adjay@naver.com...")
    try:
        # Supabase Auth Admin API: /auth/v1/admin/users
        # Note: This might be paginated, but let's try fetching page 1
        resp = requests.get(f"{url}/auth/v1/admin/users", headers=headers)
        if resp.status_code != 200:
            print(f"Auth Error: {resp.status_code} {resp.text}")
            return
            
        users = resp.json().get("users", [])
        target_user = None
        for u in users:
            if u.get("email") == "adjay@naver.com":
                target_user = u
                break
        
        if not target_user:
            print("User NOT found in Auth list!")
            return
            
        uid = target_user['id']
        print(f"User Found: {uid} ({target_user.get('email')})")
        
        # 2. Check Channel Members via PostgREST
        print("\n[2] Checking Channel Members (Admin View)...")
        # GET /rest/v1/channel_members?user_id=eq.{uid}&select=*,channels(*)
        cm_url = f"{url}/rest/v1/channel_members?user_id=eq.{uid}&select=*,channels(*)"
        cm_resp = requests.get(cm_url, headers=headers)
        
        if cm_resp.status_code != 200:
            print(f"DB Error: {cm_resp.status_code} {cm_resp.text}")
            return
            
        rows = cm_resp.json()
        print(f"Rows found: {len(rows)}")
        for row in rows:
            print(f"- Role: {row.get('role')}, Channel: {row.get('channels', {}).get('name')}")
            
        if len(rows) > 0:
            print("-> Data CONFIRMED. Issue is likely RLS/Client-side.")
        else:
            print("-> Data MISSING in DB.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
