from db import service_supabase
import os

def check_roles():
    print("--- Checking Channel Roles ---")
    # 1. List Channels and their Owners
    channels = service_supabase.table("channels").select("*").execute()
    for c in channels.data:
        print(f"Channel: {c['name']} (ID: {c['id']}), Owner: {c.get('owner_id')}")
        
    # 2. Check Memberships for 'ce89c5a4-7f97-4900-a89e-18a713c7968f'
    uid = "ce89c5a4-7f97-4900-a89e-18a713c7968f"
    mems = service_supabase.table("channel_members").select("*").eq("user_id", uid).execute()
    print(f"\nUser {uid} Memberships:")
    for m in mems.data:
        print(f"- Channel {m['channel_id']}: Role='{m['role']}'")

if __name__ == "__main__":
    check_roles()
