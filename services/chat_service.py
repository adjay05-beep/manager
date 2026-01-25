import asyncio
from typing import List, Dict, Any
from db import supabase

# Constants
CURRENT_USER_ID = "00000000-0000-0000-0000-000000000001"

async def get_categories() -> List[Dict[str, Any]]:
    """Fetch all chat categories."""
    try:
        res = await asyncio.to_thread(lambda: supabase.table("chat_categories").select("*").order("display_order", desc=True).execute())
        return res.data or []
    except Exception as e:
        print(f"Service Error (get_categories): {e}")
        return []

async def get_topics(user_id: str) -> List[Dict[str, Any]]:
    """Fetch chat topics visible to the user."""
    try:
        # [RBAC] Filter topics joined by user
        # Supabase-py join syntax: chat_topics!inner(chat_topic_members!inner(user_id))
        # But SyncPostgrestClient join syntax is tricky.
        # Simpler approach: Select from members, expanding topic.
        res = await asyncio.to_thread(lambda: supabase.table("chat_topic_members").select("topic:chat_topics(*)").eq("user_id", user_id).execute())
        
        # Unpack result
        topics = []
        if res.data:
            for item in res.data:
                topic = item.get('topic')
                if topic:
                    topics.append(topic)
        return topics
    except Exception as e:
        print(f"Service Error (get_topics): {e}")
        return []

async def create_topic(name: str, category: str, creator_id: str):
    """Create a new topic and add creator as owner."""
    def _transaction():
        # 1. Create Topic
        t_res = supabase.table("chat_topics").insert({
            "name": name, 
            "category": category, 
            "display_order": 0,
            "created_by": creator_id
        }).execute()
        
        if t_res.data:
            tid = t_res.data[0]['id']
            # 2. Add Member as Owner
            supabase.table("chat_topic_members").insert({
                "topic_id": tid,
                "user_id": creator_id,
                "permission_level": "owner"
            }).execute()
            return t_res.data
    
    await asyncio.to_thread(_transaction)

async def get_messages(topic_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch messages for a topic."""
    try:
        res = await asyncio.to_thread(lambda: supabase.table("chat_messages").select("id, topic_id, user_id, content, image_url, created_at, profiles(username, full_name)").eq("topic_id", topic_id).order("created_at", desc=True).limit(limit).execute())
        messages = res.data or []
        messages.reverse()
        return messages
    except Exception as e:
        print(f"Service Error (get_messages): {e}")
        raise e

async def update_last_read(topic_id: str, user_id: str):
    """Update last read timestamp for a user on a topic."""
    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc).isoformat()
    await asyncio.to_thread(lambda: supabase.table("chat_user_reading").upsert({"topic_id": topic_id, "user_id": user_id, "last_read_at": now_utc}).execute())

async def send_message(topic_id: str, content: str = None, image_url: str = None, user_id: str = CURRENT_USER_ID):
    """Send a message to a topic."""
    if not content and not image_url: return
    
    final_content = content
    # If we have an image but no content, use default label
    if image_url and not final_content:
        final_content = "[이미지 파일]"

    await asyncio.to_thread(lambda: supabase.table("chat_messages").insert({
        "topic_id": topic_id,
        "content": final_content,
        "image_url": image_url,
        "user_id": user_id
    }).execute())

def get_storage_signed_url(filename: str, bucket: str = "uploads") -> str:
    """Get a signed upload URL."""
    try:
        return supabase.storage.from_(bucket).create_signed_upload_url(filename)
    except Exception as e:
        print(f"Service Error (get_storage_signed_url): {e}")
        raise e

def upload_file_server_side(filename: str, file_content: bytes, bucket: str = "uploads"):
    """Upload file directly from server side (Desktop mode)."""
    supabase.storage.from_(bucket).upload(filename, file_content)

def get_public_url(filename: str, bucket: str = "uploads") -> str:
    """Construct public URL."""
    return f"{supabase.url}/storage/v1/object/public/{bucket}/{filename}"
