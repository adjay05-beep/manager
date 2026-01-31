from typing import List, Dict, Any, Optional
from db import service_supabase
from utils.logger import log_error

class ChatRepository:
    """
    Data Access Layer for Chat features.
    Handles all direct interactions with Supabase tables:
    - chat_categories
    - chat_topics
    - chat_topic_members
    - chat_messages
    - chat_user_reading
    """

    @staticmethod
    def get_categories(channel_id: int) -> List[Dict[str, Any]]:
        res = service_supabase.table("chat_categories").select("*")\
            .eq("channel_id", channel_id)\
            .order("display_order", desc=True).execute()
        return res.data or []

    @staticmethod
    def create_category(name: str, channel_id: int):
        service_supabase.table("chat_categories").insert({
            "name": name, 
            "channel_id": channel_id
        }).execute()

    @staticmethod
    def update_category(cat_id: str, new_name: str):
        service_supabase.table("chat_categories").update({"name": new_name}).eq("id", cat_id).execute()

    @staticmethod
    def delete_category(cat_id: str):
        service_supabase.table("chat_categories").delete().eq("id", cat_id).execute()

    @staticmethod
    def get_topic_member_ids(user_id: str) -> List[str]:
        res = service_supabase.table("chat_topic_members").select("topic_id").eq("user_id", user_id).execute()
        return [m['topic_id'] for m in res.data] if res.data else []

    @staticmethod
    def get_topics_by_ids(topic_ids: List[str], channel_id: int) -> List[Dict[str, Any]]:
        if not topic_ids: return []
        res = service_supabase.table("chat_topics").select("*")\
            .in_("id", topic_ids)\
            .eq("channel_id", channel_id)\
            .execute()
        return res.data or []

    @staticmethod
    def get_all_topics(channel_id: int) -> List[Dict[str, Any]]:
        res = service_supabase.table("chat_topics").select("*").eq("channel_id", channel_id).execute()
        return res.data or []

    @staticmethod
    def get_topic_by_id(topic_id: str) -> Optional[Dict[str, Any]]:
        res = service_supabase.table("chat_topics").select("id, created_by, channel_id").eq("id", topic_id).single().execute()
        return res.data

    @staticmethod
    def create_topic(topic_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        res = service_supabase.table("chat_topics").insert(topic_data).execute()
        return res.data

    @staticmethod
    def update_topic(topic_id: str, data: Dict[str, Any]):
        service_supabase.table("chat_topics").update(data).eq("id", topic_id).execute()

    @staticmethod
    def delete_topic(topic_id: str):
        service_supabase.table("chat_topics").delete().eq("id", topic_id).execute()

    @staticmethod
    def update_topics_category(old_category_name: str, new_category_name: str):
        service_supabase.table("chat_topics").update({"category": new_category_name}).eq("category", old_category_name).execute()

    @staticmethod
    def get_user_read_status(user_id: str) -> List[Dict[str, Any]]:
        res = service_supabase.table("chat_user_reading").select("topic_id, last_read_at").eq("user_id", user_id).execute()
        return res.data or []

    @staticmethod
    def get_unread_counts_from_view(user_id: str) -> List[Dict[str, Any]]:
        """Queries the server-side optimized view for unread counts."""
        res = service_supabase.table("unread_counts_view").select("topic_id, unread_count").eq("user_id", user_id).execute()
        return res.data or []

    @staticmethod
    def upsert_read_status(data: Dict[str, Any]):
        service_supabase.table("chat_user_reading").upsert(data).execute()

    @staticmethod
    def delete_read_status_by_topic(topic_id: str):
        service_supabase.table("chat_user_reading").delete().eq("topic_id", topic_id).execute()

    @staticmethod
    def get_messages(topic_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        res = service_supabase.table("chat_messages").select(
            "id, topic_id, user_id, content, image_url, created_at, profiles(username, full_name)"
        ).eq("topic_id", topic_id).order("created_at", desc=True).limit(limit).execute()
        return res.data or []

    @staticmethod
    def get_recent_messages(since_time: str) -> List[Dict[str, Any]]:
        res = service_supabase.table("chat_messages").select("topic_id, created_at, user_id").gt("created_at", since_time).execute()
        return res.data or []
    
    @staticmethod
    def get_messages_for_counts(topic_ids: List[str], since_time: str, exclude_user_id: str) -> List[Dict[str, Any]]:
        res = service_supabase.table("chat_messages")\
            .select("topic_id, created_at")\
            .in_("topic_id", topic_ids)\
            .gt("created_at", since_time)\
            .neq("user_id", exclude_user_id)\
            .order("created_at", desc=True)\
            .limit(3000)\
            .execute()
        return res.data or []

    @staticmethod
    def get_message_count_for_topic(topic_id: str, exclude_user_id: str) -> int:
        res = service_supabase.table("chat_messages")\
            .select("id", count="exact")\
            .eq("topic_id", topic_id)\
            .neq("user_id", exclude_user_id)\
            .execute()
        return res.count if res.count else 0

    @staticmethod
    def insert_message(data: Dict[str, Any]):
        service_supabase.table("chat_messages").insert(data).execute()

    @staticmethod
    def delete_messages_by_topic(topic_id: str):
        service_supabase.table("chat_messages").delete().eq("topic_id", topic_id).execute()

    @staticmethod
    def search_messages(query: str, channel_id: int, limit: int = 30) -> List[Dict[str, Any]]:
        res = service_supabase.table("chat_messages")\
            .select("*, chat_topics!inner(id, name, channel_id), profiles(full_name)")\
            .eq("chat_topics.channel_id", channel_id)\
            .ilike("content", f"%{query}%")\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return res.data or []

    @staticmethod
    def check_new_message(topic_id: str, last_msg_id: str = None) -> bool:
        query = service_supabase.table("chat_messages").select("id").eq("topic_id", topic_id)
        if last_msg_id:
            query = query.order("id", desc=True)
        
        res = query.limit(1).execute()
        
        if not res.data:
            return False
            
        latest_id = res.data[0]['id']
        # If last_msg_id is None, any message means "new" (or logic depends on usage)
        # But based on original code, if last_msg_id is None, it returns True if ANY data exists.
        if not last_msg_id:
            return True
            
        return str(latest_id) != str(last_msg_id)

    @staticmethod
    def add_topic_member(topic_id: str, user_id: str, permission_level: str):
        # Unique check usually handled by DB constraint, but for safety:
        check = service_supabase.table("chat_topic_members").select("user_id").eq("topic_id", topic_id).eq("user_id", user_id).execute()
        if not check.data:
            service_supabase.table("chat_topic_members").insert({
                "topic_id": topic_id,
                "user_id": user_id,
                "permission_level": permission_level
            }).execute()

    @staticmethod
    def remove_topic_member(topic_id: str, user_id: str):
        service_supabase.table("chat_topic_members").delete().eq("topic_id", topic_id).eq("user_id", user_id).execute()

    @staticmethod
    def delete_topic_members_by_topic(topic_id: str):
        service_supabase.table("chat_topic_members").delete().eq("topic_id", topic_id).execute()

    @staticmethod
    def get_topic_members(topic_id: str) -> List[Dict[str, Any]]:
        res = service_supabase.table("chat_topic_members")\
            .select("user_id, permission_level, profiles(full_name, username)")\
            .eq("topic_id", topic_id).execute()
        return res.data or []

    @staticmethod
    def get_channel_member_role(channel_id: int, user_id: str) -> Optional[str]:
        member_res = service_supabase.table("channel_members").select("role").eq("channel_id", channel_id).eq("user_id", user_id).single().execute()
        return member_res.data.get("role") if member_res.data else None

    @staticmethod
    def get_channel_members(channel_id: int) -> List[Dict[str, Any]]:
        res = service_supabase.table("channel_members").select("user_id, profiles(full_name, username)")\
            .eq("channel_id", channel_id).execute()
        return res.data or []
