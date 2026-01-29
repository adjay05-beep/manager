from services.channel_service import channel_service
from services.channel_service import channel_service
from db import service_supabase

def check_topics():
    print("Fetching active channels...")
    ch_res = service_supabase.table("channels").select("*").limit(1).execute()
    if not ch_res.data:
        print("No channels found.")
        return
        
    for ch in ch_res.data:
        channel_id = ch['id']
        print(f"Checking topics for channel {channel_id} ({ch.get('name')})...")
        
        # Check Invite Candidates
        import services.chat_service as chat_service
        topics = service_supabase.table("chat_topics").select("*").eq("channel_id", channel_id).execute()
        for t in topics.data:
             print(f"Topic: {t['name']} (ID: {t['id']})")
             candidates = chat_service.get_channel_members_not_in_topic(channel_id, t['id'])
             print(f"  - Candidates to invite: {len(candidates)}")
             for c in candidates:
                 print(f"    - {c}")

check_topics()
