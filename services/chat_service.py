# [REF] All methods converted to SYNC for Threading compatibility (Fixing Freeze)
"""
Chat Service for The Manager
Handles chat topics, categories, and messages using Supabase.
Refactored to use Repository Pattern.
"""
import os
from typing import List, Dict, Any, Optional
from repositories.chat_repository import ChatRepository
from db import supabase
from utils.network import retry_operation
from utils.logger import log_error, log_info

def get_categories(channel_id: int) -> List[Dict[str, Any]]:
    """Fetch all chat categories for a specific channel."""
    try:
        return ChatRepository.get_categories(channel_id)
    except Exception as e:
        print(f"Service Error (get_categories): {e}")
        return []

def get_topics(user_id: str, channel_id: int) -> List[Dict[str, Any]]:
    """Fetch chat topics visible to the user within a specific channel."""
    try:
        # [RBAC] Filter topics joined by user in this channel
        member_topic_ids = ChatRepository.get_topic_member_ids(user_id)
        
        if member_topic_ids:
            # Query topics that are in list AND belong to channel
            return ChatRepository.get_topics_by_ids(member_topic_ids, channel_id)
            
        return []
    except Exception as e:
        print(f"Service Error (get_topics): {e}")
        import traceback
        traceback.print_exc()
        raise e

def get_all_topics(channel_id: int) -> List[Dict[str, Any]]:
    """Fetch ALL topics for a channel (Diagnostic/Admin Only)."""
    try:
        return ChatRepository.get_all_topics(channel_id)
    except Exception as e:
        print(f"Service Error (get_all_topics): {e}")
        return []

def get_user_read_status(user_id: str) -> Dict[str, str]:
    """Fetch read status map for a user."""
    try:
        data = ChatRepository.get_user_read_status(user_id)
        return {r['topic_id']: r['last_read_at'] for r in data}
    except Exception as e:
        print(f"Service Error (get_user_read_status): {e}")
        return {}

def get_recent_messages(since_time: str) -> List[Dict[str, Any]]:
    """Fetch messages newer than a timestamp (for unread counts)."""
    try:
        return ChatRepository.get_recent_messages(since_time)
    except Exception as e:
        print(f"Service Error (get_recent_messages): {e}")
        return []

def _verify_topic_permission(topic_id: str, user_id: str) -> bool:
    """Verify user has permission to modify topic (owner or channel admin)."""
    try:
        # Check if user is topic creator or has owner/manager role in channel
        topic = ChatRepository.get_topic_by_id(topic_id)
        if not topic:
            return False

        # Creator can always modify
        if topic.get("created_by") == user_id:
            return True

        # Check if user is owner/manager in the channel
        channel_id = topic.get("channel_id")
        if channel_id:
            role = ChatRepository.get_channel_member_role(channel_id, user_id)
            if role in ["owner", "manager"]:
                return True

        return False
    except Exception as e:
        log_error(f"Permission check error: {e}")
        return False

def update_topic_order(topic_id: str, new_order: int, user_id: str = None):
    """Update display order of a topic."""
    if user_id and not _verify_topic_permission(topic_id, user_id):
        raise PermissionError("토픽 수정 권한이 없습니다.")
    ChatRepository.update_topic(topic_id, {"display_order": new_order})

def delete_topic(topic_id: str, user_id: str = None):
    """Delete a topic and its messages (Application-side Cascade)."""
    # [SECURITY] 권한 검증
    if user_id and not _verify_topic_permission(topic_id, user_id):
        raise PermissionError("토픽 삭제 권한이 없습니다.")

    # 1. Delete Messages first (Constraint Fix)
    ChatRepository.delete_messages_by_topic(topic_id)
    # 2. Delete Topic Members
    ChatRepository.delete_topic_members_by_topic(topic_id)
    # 3. Delete Reading Status
    ChatRepository.delete_read_status_by_topic(topic_id)
    # 4. Delete Topic
    ChatRepository.delete_topic(topic_id)
    log_info(f"Topic deleted: {topic_id} by user {user_id}")

def toggle_topic_priority(topic_id: str, current_val: bool, user_id: str = None):
    """Toggle priority status."""
    if user_id and not _verify_topic_permission(topic_id, user_id):
        raise PermissionError("토픽 수정 권한이 없습니다.")
    ChatRepository.update_topic(topic_id, {"is_priority": not current_val})

def create_category(name: str, channel_id: int):
    """Create a new category in a channel."""
    ChatRepository.create_category(name, channel_id)

def delete_category(cat_id: str):
    """Delete a category."""
    ChatRepository.delete_category(cat_id)

def update_category(cat_id: str, old_name: str, new_name: str):
    """Update category name in both categories table and dependent topics."""
    # 1. Update the category record
    ChatRepository.update_category(cat_id, new_name)
    # 2. Update all topics using this category string
    ChatRepository.update_topics_category(old_name, new_name)

def rename_topic(topic_id: str, new_name: str):
    """Rename a specific topic."""
    ChatRepository.update_topic(topic_id, {"name": new_name})

def update_topic(topic_id: str, name: str, category: str):
    """Update topic name and category."""
    data = {"name": name, "category": category if category else None}
    ChatRepository.update_topic(topic_id, data)

def create_topic(name: str, category: str, creator_id: str, channel_id: int):
    """Create a new topic in a channel and add creator as owner."""
    # 1. Create Topic
    t_data = ChatRepository.create_topic({
        "name": name, 
        "category": category, 
        "display_order": 0,
        "created_by": creator_id,
        "channel_id": channel_id
    })
    
    if t_data:
        tid = t_data[0]['id']
        # 2. Add Member as Owner
        ChatRepository.add_topic_member(tid, creator_id, "owner")
        return t_data

def get_messages(topic_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch messages for a topic."""
    try:
        messages = ChatRepository.get_messages(topic_id, limit)
        messages.reverse()
        return messages
    except Exception as e:
        print(f"Service Error (get_messages): {e}")
        raise e

def update_last_read(topic_id: str, user_id: str):
    """Update last read timestamp for a user on a topic."""
    import datetime
    try:
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        ChatRepository.upsert_read_status({
            "topic_id": topic_id, 
            "user_id": user_id, 
            "last_read_at": now_utc
        })
    except Exception as e:
        log_error(f"Update Read Error: {e}")

def send_message(topic_id: str, content: str = None, image_url: str = None, user_id: str = None):
    """Send a message to a topic."""
    if not content and not image_url: return
    
    final_content = content
    # If we have an image but no content, use default label
    if image_url and not final_content:
        clean_url = image_url.split("?")[0].lower()
        if any(clean_url.endswith(ext) for ext in [".mp4", ".mov", ".avi", ".wmv", ".mkv", ".webm"]):
             final_content = "[동영상]"
        elif any(clean_url.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
             final_content = "[이미지]"
        else:
             final_content = "[파일 첨부]"

    ChatRepository.insert_message({
        "topic_id": topic_id,
        "content": final_content,
        "image_url": image_url,
        "user_id": user_id
    })

def get_storage_signed_url(filename: str, bucket: str = "uploads") -> str:
    """Get a signed upload URL."""
    try:
        from db import service_supabase
        return service_supabase.storage.from_(bucket).create_signed_upload_url(filename)
    except Exception as e:
        print(f"Service Error (get_storage_signed_url): {e}")
        raise e

@retry_operation(max_retries=3, delay=1.0)
def upload_file_server_side(filename: str, file_content: bytes, bucket: str = "uploads", content_type: str = None):
    """Upload file directly from server side (Desktop mode)."""
    from db import service_supabase
    options = {"content-type": content_type} if content_type else None
    service_supabase.storage.from_(bucket).upload(filename, file_content, file_options=options)

def get_public_url(filename: str, bucket: str = "uploads") -> str:
    """Construct public URL."""
    try:
        from db import service_supabase
        # Use SDK method if available
        return service_supabase.storage.from_(bucket).get_public_url(filename)
    except Exception as e:
        # Fallback to manual construction
        log_info(f"SDK get_public_url failed, using fallback: {e}")
        base_url = supabase.url if hasattr(supabase, "url") else os.environ.get("SUPABASE_URL", "")
        return f"{base_url}/storage/v1/object/public/{bucket}/{filename}"

def get_unread_counts(user_id: str, topics: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Calculate unread messages for a list of topics.
    Returns: {topic_id: count}

    [OPTIMIZATION] Uses server-side SQL View 'unread_counts_view'
    """
    if not topics:
        return {}
    
    try:
        # 1. Fetch unread counts from View
        view_data = ChatRepository.get_unread_counts_from_view(user_id)
        # [FIX] Do NOT filter out 0 counts. If we filter them, they fall into 'missing_topic_ids'
        # and get recounted as "Never Read" (Total Messages), causing the bug.
        counts = {str(item['topic_id']): int(item['unread_count']) for item in view_data}

        # 2. Handle 'Never Read' topics (Fallback for topics not in chat_user_reading)
        topic_ids = [str(t['id']) for t in topics]
        read_topic_ids = set(counts.keys())
        missing_topic_ids = [tid for tid in topic_ids if tid not in read_topic_ids]

        if missing_topic_ids:
            # For topics not yet in user_reading, we still need to check if they have messages
            # But the view only joins on chat_user_reading.
            # Potential Improvement: Use a better View, but for now, we use a single query for missing ones.
            for tid in missing_topic_ids:
                # Check if a reading record exists but count is 0? 
                # (The view counts correctly if record exists, so if it's missing, it's a never-read topic)
                msg_count = ChatRepository.get_message_count_for_topic(tid, user_id)
                if msg_count > 0:
                    counts[tid] = msg_count

        return counts
    except Exception as e:
        log_error(f"Service Error (get_unread_counts_optimized): {e}")
        return {}


def search_messages_global(query: str, channel_id: int) -> List[Dict[str, Any]]:
    """
    Search messages across all topics in a channel.
    """
    try:
        return ChatRepository.search_messages(query, channel_id)
    except Exception as e:
        print(f"Service Error (search_messages_global): {e}")
        return []

def add_topic_member(topic_id: str, user_id: str, permission_level: str = "member"):
    """Add a user to a chat topic."""
    ChatRepository.add_topic_member(topic_id, user_id, permission_level)

def remove_topic_member(topic_id: str, user_id: str):
    """Remove a user from a chat topic."""
    ChatRepository.remove_topic_member(topic_id, user_id)

def get_topic_members(topic_id: str) -> List[Dict[str, Any]]:
    """Get all members of a topic with profile info."""
    data = ChatRepository.get_topic_members(topic_id)
    members = []
    if data:
        for m in data:
            p = m.get("profiles") or {}
            members.append({
                "user_id": m["user_id"],
                "permission_level": m["permission_level"],
                "full_name": p.get("full_name") or p.get("username") or "Unknown",
                "email": p.get("username") or "" 
            })
    return members

def get_channel_members_not_in_topic(channel_id: int, topic_id: str, ignore_user_id: str = None) -> List[Dict[str, Any]]:
    """Get channel members who are NOT in the specific topic."""
    if not channel_id or not topic_id: return []
    
    # 1. Get all channel members
    channel_users = ChatRepository.get_channel_members(channel_id)
    
    # 2. Get current topic members
    t_members = ChatRepository.get_topic_members(topic_id)
    topic_user_ids = set(m["user_id"] for m in t_members)
    
    # 3. Filter
    available = []
    
    for u in channel_users:
        u_id = u["user_id"]
        
        # Ensure exact match
        if u_id not in topic_user_ids:
            # Explicit Ignore
            current_candidate_id = str(u_id).strip()
            
            if ignore_user_id and current_candidate_id == str(ignore_user_id).strip():
                continue
                
            p = u.get("profiles") or {}
            available.append({
                "user_id": u_id,
                "full_name": p.get("full_name") or "Unknown",
                "username": p.get("username")
            })
    return available


def check_new_messages(topic_id, last_msg_id=None):
    """Check if there are any messages newer than last_msg_id."""
    try:
        return ChatRepository.check_new_message(topic_id, last_msg_id)
    except Exception as e:
        print(f"Check Update Error: {e}")
        return False
