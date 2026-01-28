# [REF] All methods converted to SYNC for Threading compatibility (Fixing Freeze)
"""
Chat Service for The Manager
Handles chat topics, categories, and messages using Supabase.
"""
from typing import List, Dict, Any
from db import supabase, service_supabase

# Constants
CURRENT_USER_ID = "00000000-0000-0000-0000-000000000001"

def get_categories(channel_id: int) -> List[Dict[str, Any]]:
    """Fetch all chat categories for a specific channel."""
    try:
        res = service_supabase.table("chat_categories").select("*")\
            .eq("channel_id", channel_id)\
            .order("display_order", desc=True).execute()
        return res.data or []
    except Exception as e:
        print(f"Service Error (get_categories): {e}")
        return []

def get_topics(user_id: str, channel_id: int) -> List[Dict[str, Any]]:
    """Fetch chat topics visible to the user within a specific channel."""
    try:
        # [RBAC] Filter topics joined by user in this channel
        # We need to filter topics by their channel_id as well
        
        # Method 1: Get topics the user is a member of
        # But we need to check if those topics belong to channel_id
        
        member_res = service_supabase.table("chat_topic_members").select("topic_id").eq("user_id", user_id).execute()
        member_topic_ids = [m['topic_id'] for m in member_res.data] if member_res.data else []
        
        topics = []
        if member_topic_ids:
            # Query topics that are in list AND belong to channel
            topics_res = service_supabase.table("chat_topics").select("*")\
                .in_("id", member_topic_ids)\
                .eq("channel_id", channel_id)\
                .execute()
            topics = topics_res.data or []
            
        return topics
    except Exception as e:
        print(f"Service Error (get_topics): {e}")
        import traceback
        traceback.print_exc()
        raise e

def get_all_topics(channel_id: int) -> List[Dict[str, Any]]:
    """Fetch ALL topics for a channel (Diagnostic/Admin Only)."""
    try:
        res = service_supabase.table("chat_topics").select("*").eq("channel_id", channel_id).execute()
        return res.data or []
    except Exception as e:
        print(f"Service Error (get_all_topics): {e}")
        return []

def get_user_read_status(user_id: str) -> Dict[str, str]:
    """Fetch read status map for a user."""
    try:
        res = service_supabase.table("chat_user_reading").select("topic_id, last_read_at").eq("user_id", user_id).execute()
        return {r['topic_id']: r['last_read_at'] for r in res.data} if res.data else {}
    except Exception as e:
        print(f"Service Error (get_user_read_status): {e}")
        return {}

def get_recent_messages(since_time: str) -> List[Dict[str, Any]]:
    """Fetch messages newer than a timestamp (for unread counts)."""
    try:
        res = service_supabase.table("chat_messages").select("topic_id, created_at, user_id").gt("created_at", since_time).execute()
        return res.data or []
    except Exception as e:
        print(f"Service Error (get_recent_messages): {e}")
        return []

def update_topic_order(topic_id: str, new_order: int):
    """Update display order of a topic."""
    service_supabase.table("chat_topics").update({"display_order": new_order}).eq("id", topic_id).execute()

def delete_topic(topic_id: str):
    """Delete a topic and its messages (Application-side Cascade)."""
    # 1. Delete Messages first (Constraint Fix)
    service_supabase.table("chat_messages").delete().eq("topic_id", topic_id).execute()
    # 2. Delete Topic
    service_supabase.table("chat_topics").delete().eq("id", topic_id).execute()

def toggle_topic_priority(topic_id: str, current_val: bool):
    """Toggle priority status."""
    service_supabase.table("chat_topics").update({"is_priority": not current_val}).eq("id", topic_id).execute()

def create_category(name: str, channel_id: int):
    """Create a new category in a channel."""
    service_supabase.table("chat_categories").insert({
        "name": name, 
        "channel_id": channel_id
    }).execute()

def delete_category(cat_id: str):
    """Delete a category."""
    service_supabase.table("chat_categories").delete().eq("id", cat_id).execute()

def update_category(cat_id: str, old_name: str, new_name: str):
    """Update category name in both categories table and dependent topics."""
    # 1. Update the category record
    service_supabase.table("chat_categories").update({"name": new_name}).eq("id", cat_id).execute()
    # 2. Update all topics using this category string
    service_supabase.table("chat_topics").update({"category": new_name}).eq("category", old_name).execute()

def rename_topic(topic_id: str, new_name: str):
    """Rename a specific topic."""
    service_supabase.table("chat_topics").update({"name": new_name}).eq("id", topic_id).execute()

def update_topic(topic_id: str, name: str, category: str):
    """Update topic name and category."""
    data = {"name": name}
    if category: data["category"] = category
    else: data["category"] = None # Handle Uncategorized
    
    service_supabase.table("chat_topics").update(data).eq("id", topic_id).execute()

def create_topic(name: str, category: str, creator_id: str, channel_id: int):
    """Create a new topic in a channel and add creator as owner."""
    # 1. Create Topic (use service_supabase to bypass RLS)
    t_res = service_supabase.table("chat_topics").insert({
        "name": name, 
        "category": category, 
        "display_order": 0,
        "created_by": creator_id,
        "channel_id": channel_id
    }).execute()
    
    if t_res.data:
        tid = t_res.data[0]['id']
        # 2. Add Member as Owner (use service_supabase to bypass RLS)
        service_supabase.table("chat_topic_members").insert({
            "topic_id": tid,
            "user_id": creator_id,
            "permission_level": "owner"
        }).execute()
        return t_res.data

def get_messages(topic_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch messages for a topic."""
    try:
        res = service_supabase.table("chat_messages").select("id, topic_id, user_id, content, image_url, created_at, profiles(username, full_name)").eq("topic_id", topic_id).order("created_at", desc=True).limit(limit).execute()
        messages = res.data or []
        messages.reverse()
        return messages
    except Exception as e:
        print(f"Service Error (get_messages): {e}")
        raise e

def update_last_read(topic_id: str, user_id: str):
    """Update last read timestamp for a user on a topic."""
    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc).isoformat()
    service_supabase.table("chat_user_reading").upsert({"topic_id": topic_id, "user_id": user_id, "last_read_at": now_utc}).execute()

def send_message(topic_id: str, content: str = None, image_url: str = None, user_id: str = CURRENT_USER_ID):
    """Send a message to a topic."""
    if not content and not image_url: return
    
    final_content = content
    # If we have an image but no content, use default label
    # If we have an image but no content, use default label
    if image_url and not final_content:
        clean_url = image_url.split("?")[0].lower()
        if any(clean_url.endswith(ext) for ext in [".mp4", ".mov", ".avi", ".wmv", ".mkv", ".webm"]):
             final_content = "[동영상]"
        elif any(clean_url.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
             final_content = "[이미지]"
        else:
             final_content = "[파일 첨부]"

    service_supabase.table("chat_messages").insert({
        "topic_id": topic_id,
        "content": final_content,
        "image_url": image_url,
        "user_id": user_id
    }).execute()

def get_storage_signed_url(filename: str, bucket: str = "uploads") -> str:
    """Get a signed upload URL."""
    try:
        return service_supabase.storage.from_(bucket).create_signed_upload_url(filename)
    except Exception as e:
        print(f"Service Error (get_storage_signed_url): {e}")
        raise e

def upload_file_server_side(filename: str, file_content: bytes, bucket: str = "uploads", content_type: str = None):
    """Upload file directly from server side (Desktop mode)."""
    options = {"content-type": content_type} if content_type else None
    service_supabase.storage.from_(bucket).upload(filename, file_content, file_options=options)

def get_public_url(filename: str, bucket: str = "uploads") -> str:
    """Construct public URL."""
    try:
        # Use SDK method if available
        return service_supabase.storage.from_(bucket).get_public_url(filename)
    except:
        # Fallback to manual construction
        base_url = supabase.supabase_url if hasattr(supabase, "supabase_url") else "https://adjay05-beep.supabase.co"
        return f"{base_url}/storage/v1/object/public/{bucket}/{filename}"
