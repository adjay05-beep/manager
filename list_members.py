import asyncio
from db import service_supabase

async def check_members():
    print("🔍 Checking Channel Memberships...\n")
    
    # 1. Get Channels
    channels = service_supabase.table("channels").select("*").execute().data
    if not channels:
        print("❌ No channels found!")
        return

    for ch in channels:
        cid = ch['id']
        cname = ch['name']
        print(f"🏠 Channel: {cname} (ID: {cid})")
        
        # 2. Get Members
        # Join with profiles to get names
        res = service_supabase.table("channel_members").select("role, user_id, profiles(full_name, id)").eq("channel_id", cid).execute()
        
        members = res.data
        if not members:
            print("   (No members found)")
        else:
            for m in members:
                prof = m.get('profiles') or {}
                # Handle case where profiles might be a list or dict depending on API
                if isinstance(prof, list) and prof: prof = prof[0]
                
                name = prof.get('full_name', 'Unknown')
                uid = m['user_id']
                role = m['role']
                
                print(f"   👤 User: {name} | Role: {role} | ID: {uid}")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(check_members())
