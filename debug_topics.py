from services.chat_service import chat_service
from services.channel_service import channel_service
from db import service_supabase

def check_topics(channel_id):
    print(f"Checking topics for channel {channel_id}...")
    topics = service_supabase.table("chat_topics").select("*").eq("channel_id", channel_id).execute()
    for t in topics.data:
        print(f"Topic: {t['name']} (ID: {t['id']})")
        members = service_supabase.table("chat_topic_members").select("user_id").eq("topic_id", t['id']).execute()
        print(f"  - Members: {len(members.data)}")

# Usage: Update channel_id manually
# check_topics(14)
