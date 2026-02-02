import asyncio
from typing import List, Dict, Any, Optional
from db import service_supabase
from utils.logger import log_error, log_info

async def get_all_events(user_id: str, channel_id: int) -> List[Dict[str, Any]]:
    """Fetch calendar events visible to the user in specific channel."""
    # [ROBUSTNESS] Use Authenticated Client if possible to bypass RLS
    from services.auth_service import auth_service
    from postgrest import SyncPostgrestClient
    import os
    
    headers = auth_service.get_auth_headers()
    client = service_supabase
    
    if headers:
        url = os.environ.get("SUPABASE_URL")
        # Creating a temporary client for this request
        # Note: SyncPostgrestClient is lightweight
        client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public", timeout=20)
    
    # query 1: Fetch ALL filtered events for this channel (Shared Calendar Model)
    # [FIX] Simplified policy: If you are in the channel, you see all channel events.
    # This removes the need for complex 'participant_ids' JSONB filtering on the server/client.
    t1 = asyncio.to_thread(lambda: client.from_("calendar_events")
                           .select("*, profiles!calendar_events_created_by_fkey(full_name)")
                           .eq("channel_id", channel_id) # Filter by Channel
                           .order("start_date", desc=True)
                           .limit(500) # Safety limit
                           .execute())
    
    # query 2: Deprecated (Merged into t1)
    t2 = None 
    
    # Run
    res1 = None
    try:
        res1 = await t1
    except Exception as e:
        log_error(f"Calendar Fetch Error: {e}")
        return []
    
    events = res1.data if res1 and res1.data else []
    
    # [OPTIONAL] Client-side filter if strict privacy needed (e.g. is_private column)
    # For now, we return all channel events.
    return events

async def delete_event(event_id: str, user_id: str) -> bool:
    """Delete an event by ID with ownership verification."""
    try:
        # [SECURITY] 소유권 검증 - 본인이 생성한 이벤트만 삭제 가능
        event_res = await asyncio.to_thread(
            lambda: service_supabase.table("calendar_events")
                .select("id, created_by")
                .eq("id", event_id)
                .execute()
        )

        if not event_res.data:
            log_error(f"Event not found: {event_id}")
            raise PermissionError("이벤트를 찾을 수 없습니다.")

        if event_res.data[0].get("created_by") != user_id:
            log_error(f"Unauthorized delete attempt: user={user_id}, event={event_id}")
            raise PermissionError("본인이 생성한 이벤트만 삭제할 수 있습니다.")

        await asyncio.to_thread(
            lambda: service_supabase.table("calendar_events")
                .delete()
                .eq("id", event_id)
                .execute()
        )
        log_info(f"Event deleted: {event_id} by user {user_id}")
        return True
    except PermissionError:
        raise
    except Exception as e:
        log_error(f"Delete event error: {e}")
        raise

async def load_profiles(channel_id: int) -> List[Dict[str, Any]]:
    """Fetch all user profiles in the current channel."""
    # We need to join channel_members to get only relevant users
    # Supabase doesn't support implicit join on M2M easily without foreign key setup on view
    # So we do: Get user_ids from channel_members -> Get profiles
    
    try:
        # 1. Get Member IDs (Async)
        m_res = await asyncio.to_thread(lambda: service_supabase.table("channel_members").select("user_id").eq("channel_id", channel_id).execute())
        uids = [m['user_id'] for m in m_res.data] if m_res.data else []
        
        if not uids: return []
        
        # 2. Get Profiles (Async)
        res = await asyncio.to_thread(lambda: service_supabase.table("profiles")
            .select("id, full_name")
            .in_("id", uids)
            .execute())
            
        return res.data or []
    except Exception as e:
        print(f"Error loading profiles: {e}")
        return []

async def create_event(event_data: Dict[str, Any]):
    """Create a new calendar event."""
    await asyncio.to_thread(lambda: service_supabase.table("calendar_events").insert(event_data).execute())

async def update_event(event_id: str, event_data: Dict[str, Any], user_id: str):
    """Update an event by ID with ownership verification."""
    # [SECURITY] Ownership check
    event_res = await asyncio.to_thread(
        lambda: service_supabase.table("calendar_events")
            .select("id, created_by")
            .eq("id", event_id)
            .execute()
    )

    if not event_res.data:
        raise PermissionError("이벤트를 찾을 수 없습니다.")

    if event_res.data[0].get("created_by") != user_id:
        raise PermissionError("본인이 생성한 이벤트만 수정할 수 있습니다.")

    # Remove fields that shouldn't be updated manually or might cause error
    clean_data = {k: v for k, v in event_data.items() if k not in ["id", "created_at", "created_by"]}
    
    await asyncio.to_thread(
        lambda: service_supabase.table("calendar_events")
            .update(clean_data)
            .eq("id", event_id)
            .execute()
    )
    log_info(f"Event updated: {event_id} by user {user_id}")
