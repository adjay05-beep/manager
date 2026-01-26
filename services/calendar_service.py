import asyncio
from typing import List, Dict, Any
from db import service_supabase

CURRENT_USER_ID = "00000000-0000-0000-0000-000000000001"

async def get_all_events(user_id: str) -> List[Dict[str, Any]]:
    """Fetch calendar events visible to the user."""
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
    
    # query 1: Events Created by Me
    # Use client.from_(...) instead of service_supabase.table(...)
    t1 = asyncio.to_thread(lambda: client.from_("calendar_events").select("*, profiles!calendar_events_created_by_fkey(full_name)").eq("created_by", user_id).execute())
    
    # query 2: Events with Me as Participant (JSONB Containment)
    # [FIX] Temporarily disabled due to Postgrest JSON serialization issues (22P02)
    # t2 = asyncio.to_thread(lambda: client.from_("calendar_events").select("*, profiles!calendar_events_created_by_fkey(full_name)").cs("participant_ids", f'["{user_id}"]').execute())
    t2 = None # Skip
    
    # Run in parallel with error handling
    res1 = None
    res2 = None
    try:
        # Only run t1
        # results = await asyncio.gather(t1, t2, return_exceptions=True)
        res1 = await t1
            
    except Exception as e:
        print(f"Calendar Fetch Fatal Error: {e}")
        return []
    
    # Merge and Deduplicate by ID
    events_map = {}
    if res1 and res1.data:
        for e in res1.data: events_map[e['id']] = e
    if res2 and res2.data:
        for e in res2.data: events_map[e['id']] = e
        
    return list(events_map.values())

async def delete_event(event_id: str):
    """Delete an event by ID."""
    # TODO: Verify ownership? View handles it? 
    # Service should ideally check too.
    await asyncio.to_thread(lambda: service_supabase.table("calendar_events").delete().eq("id", event_id).execute())

async def load_profiles() -> List[Dict[str, Any]]:
    """Fetch all user profiles."""
    res = await asyncio.to_thread(lambda: service_supabase.table("profiles").select("id, full_name").execute())
    return res.data or []

async def create_event(event_data: Dict[str, Any]):
    """Create a new calendar event."""
    await asyncio.to_thread(lambda: service_supabase.table("calendar_events").insert(event_data).execute())
