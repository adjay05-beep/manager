from db import service_supabase
import os

def check_members():
    print("--- Channel 1 Members ---")
    res = service_supabase.table("channel_members").select("user_id, role, profiles(full_name)").eq("channel_id", 1).execute()
    for m in res.data:
        p = m.get('profiles') or {}
        print(f"User: {m['user_id']} | Role: {m['role']} | Name: {p.get('full_name')}")

if __name__ == "__main__":
    check_members()
