# [REF] All methods converted to SYNC for Threading compatibility (Fixing Freeze)
"""
Chat Service for The Manager
Handles chat topics, categories, and messages using Supabase.
"""
import os
from typing import List, Dict, Any, Optional
from db import supabase, service_supabase
from utils.network import retry_operation
from utils.logger import log_error, log_info

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

def _verify_topic_permission(topic_id: str, user_id: str) -> bool:
    """Verify user has permission to modify topic (owner or channel admin)."""
    try:
        # Check if user is topic creator or has owner/manager role in channel
        topic_res = service_supabase.table("chat_topics").select("id, created_by, channel_id").eq("id", topic_id).single().execute()
        if not topic_res.data:
            return False

        topic = topic_res.data
        # Creator can always modify
        if topic.get("created_by") == user_id:
            return True

        # Check if user is owner/manager in the channel
        channel_id = topic.get("channel_id")
        if channel_id:
            member_res = service_supabase.table("channel_members").select("role").eq("channel_id", channel_id).eq("user_id", user_id).single().execute()
            if member_res.data and member_res.data.get("role") in ["owner", "manager"]:
                return True

        return False
    except Exception as e:
        log_error(f"Permission check error: {e}")
        return False

def update_topic_order(topic_id: str, new_order: int, user_id: str = None):
    """Update display order of a topic."""
    if user_id and not _verify_topic_permission(topic_id, user_id):
        raise PermissionError("토픽 수정 권한이 없습니다.")
    service_supabase.table("chat_topics").update({"display_order": new_order}).eq("id", topic_id).execute()

def delete_topic(topic_id: str, user_id: str = None):
    """Delete a topic and its messages (Application-side Cascade)."""
    # [SECURITY] 권한 검증
    if user_id and not _verify_topic_permission(topic_id, user_id):
        raise PermissionError("토픽 삭제 권한이 없습니다.")

    # 1. Delete Messages first (Constraint Fix)
    service_supabase.table("chat_messages").delete().eq("topic_id", topic_id).execute()
    # 2. Delete Topic Members
    service_supabase.table("chat_topic_members").delete().eq("topic_id", topic_id).execute()
    # 3. Delete Reading Status
    service_supabase.table("chat_user_reading").delete().eq("topic_id", topic_id).execute()
    # 4. Delete Topic
    service_supabase.table("chat_topics").delete().eq("id", topic_id).execute()
    log_info(f"Topic deleted: {topic_id} by user {user_id}")

def toggle_topic_priority(topic_id: str, current_val: bool, user_id: str = None):
    """Toggle priority status."""
    if user_id and not _verify_topic_permission(topic_id, user_id):
        raise PermissionError("토픽 수정 권한이 없습니다.")
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
    import datetime
    try:
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        service_supabase.table("chat_user_reading").upsert({
            "topic_id": topic_id, 
            "user_id": user_id, 
            "last_read_at": now_utc
        }).execute()
    except Exception as e:
        log_error(f"Update Read Error: {e}")

def send_message(topic_id: str, content: str = None, image_url: str = None, user_id: str = None):
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

@retry_operation(max_retries=3, delay=1.0)
def upload_file_server_side(filename: str, file_content: bytes, bucket: str = "uploads", content_type: str = None):
    """Upload file directly from server side (Desktop mode)."""
    options = {"content-type": content_type} if content_type else None
    service_supabase.storage.from_(bucket).upload(filename, file_content, file_options=options)

def get_public_url(filename: str, bucket: str = "uploads") -> str:
    """Construct public URL."""
    try:
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

    [OPTIMIZATION] Batch query instead of N+1 queries:
    - Fetch all read statuses in one query
    - Fetch all recent messages in one query
    - Process counts in memory
    """
    if not topics:
        return {}

    from db import service_supabase
    
    # [FIX] Heartbeat Trigger: ensures client is active
    if hasattr(service_supabase, "check_connection"):
        service_supabase.check_connection()

    for attempt in range(2): # Simple retry for transient disconnects
        try:
            # 1. Get user's read status map
            read_map = get_user_read_status(user_id)
            
            # 2. Get topic IDs
            topic_ids = [t['id'] for t in topics]

            # 3. Find the oldest read timestamp to minimize data fetch
            oldest_read = None
            never_read_topics = []
            for tid in topic_ids:
                last_read = read_map.get(tid)
                if not last_read:
                    never_read_topics.append(tid)
                elif oldest_read is None or last_read < oldest_read:
                    oldest_read = last_read

            counts = {}

            # 4. For never-read topics, check if they have any messages
            if never_read_topics:
                # Query counts for never-read topics
                for tid in never_read_topics:
                    res = service_supabase.table("chat_messages")\
                        .select("id", count="exact")\
                        .eq("topic_id", tid)\
                        .neq("user_id", user_id)\
                        .execute()
                    if res.count and res.count > 0:
                        counts[tid] = res.count

            # 5. For read topics, fetch messages newer than oldest_read (single query)
            read_topic_ids = [tid for tid in topic_ids if tid not in never_read_topics]
            if read_topic_ids and oldest_read:
                res = service_supabase.table("chat_messages")\
                    .select("topic_id, created_at")\
                    .in_("topic_id", read_topic_ids)\
                    .gt("created_at", oldest_read)\
                    .neq("user_id", user_id)\
                    .order("created_at", desc=True)\
                    .limit(3000)\
                    .execute()

                if res.data:
                    # Count messages per topic that are newer than user's last read
                    from collections import defaultdict
                    topic_messages = defaultdict(list)
                    for m in res.data:
                        topic_messages[m['topic_id']].append(m['created_at'])

                    for tid in read_topic_ids:
                        last_read = read_map.get(tid)
                        if last_read and tid in topic_messages:
                            try:
                                # Robust Comparison using datetime objects
                                from datetime import datetime
                                # Standardize to +00:00 for fromisoformat
                                lr_dt = datetime.fromisoformat(last_read.replace('Z', '+00:00'))
                                
                                unread = 0
                                for msg_time in topic_messages[tid]:
                                    m_dt = datetime.fromisoformat(msg_time.replace('Z', '+00:00'))
                                    if m_dt > lr_dt:
                                        unread += 1
                                
                                if unread > 0:
                                    counts[tid] = unread
                            except Exception as parse_ex:
                                log_error(f"Unread Parse Error for {tid}: {parse_ex}")
                                # Fallback to string comparison if parse fails
                                unread = sum(1 for msg_time in topic_messages[tid] if msg_time > last_read)
                                if unread > 0: counts[tid] = unread

            # [Iteration 21] Return string keys for best compatibility
            return {str(k): v for k, v in counts.items()}
        except Exception as e:
            if attempt == 0:
                log_info(f"Retrying unread counts after error: {e}")
                if hasattr(service_supabase, "check_connection"):
                    service_supabase.check_connection()
                continue
            log_error(f"Service Error (get_unread_counts): {e}")
            return {}
    return {}

def search_messages_global(query: str, channel_id: int) -> List[Dict[str, Any]]:
    """
    Search messages across all topics in a channel.
    """
    try:
        # Join with topics to ensure channel context
        # We need to filter by channel via the relationship
        res = service_supabase.table("chat_messages")\
            .select("*, chat_topics!inner(id, name, channel_id), profiles(full_name)")\
            .eq("chat_topics.channel_id", channel_id)\
            .ilike("content", f"%{query}%")\
            .order("created_at", desc=True)\
            .limit(30)\
            .execute()
            
        return res.data or []
    except Exception as e:
        print(f"Service Error (search_messages_global): {e}")
        return []

def add_topic_member(topic_id: str, user_id: str, permission_level: str = "member"):
    """Add a user to a chat topic."""
    # Check if already exists to avoid error
    check = service_supabase.table("chat_topic_members").select("user_id").eq("topic_id", topic_id).eq("user_id", user_id).execute()
    if not check.data:
        service_supabase.table("chat_topic_members").insert({
            "topic_id": topic_id,
            "user_id": user_id,
            "permission_level": permission_level
        }).execute()

def remove_topic_member(topic_id: str, user_id: str):
    """Remove a user from a chat topic."""
    service_supabase.table("chat_topic_members").delete()\
        .eq("topic_id", topic_id).eq("user_id", user_id).execute()

def get_topic_members(topic_id: str) -> List[Dict[str, Any]]:
    """Get all members of a topic with profile info."""
    # [FIX] Remove 'joined_at' as it might not exist in some DB versions
    res = service_supabase.table("chat_topic_members")\
        .select("user_id, permission_level, profiles(full_name, username)")\
        .eq("topic_id", topic_id).execute()
    
    members = []
    if res.data:
        for m in res.data:
            p = m.get("profiles") or {}
            members.append({
                "user_id": m["user_id"],
                "permission_level": m["permission_level"],
                "full_name": p.get("full_name") or p.get("username") or "Unknown",
                "email": p.get("username") or "" # Use username as fallback if email not in profiles
            })
    return members

def get_channel_members_not_in_topic(channel_id: int, topic_id: str, ignore_user_id: str = None) -> List[Dict[str, Any]]:
    """Get channel members who are NOT in the specific topic."""
    if not channel_id or not topic_id: return []
    
    # 1. Get all channel members
    c_res = service_supabase.table("channel_members").select("user_id, profiles(full_name, username)")\
        .eq("channel_id", channel_id).execute()
    channel_users = c_res.data or []
    
    # 2. Get current topic members
    t_res = service_supabase.table("chat_topic_members").select("user_id").eq("topic_id", topic_id).execute()
    topic_user_ids = set(m["user_id"] for m in (t_res.data or []))
    
    # 3. Filter
    available = []
    
    # [Targeted Debug] Check Ignore ID
    # ign_debug = str(ignore_user_id).strip() if ignore_user_id else "None"
    # log_info(f"DEBUG_SERVICE: Filtering with IgnoreID='{ign_debug}'")

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
        if not last_msg_id:
            res = service_supabase.table("chat_messages").select("id").eq("topic_id", topic_id).limit(1).execute()
            return len(res.data) > 0
        
        res = service_supabase.table("chat_messages").select("id").eq("topic_id", topic_id).order("id", desc=True).limit(1).execute()
        if res.data:
            latest_id = res.data[0]['id']
            return str(latest_id) != str(last_msg_id)
        return False
    except Exception as e:
        print(f"Check Update Error: {e}")
        return False
