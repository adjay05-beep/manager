import asyncio
from typing import List, Dict, Any
from db import supabase

CURRENT_USER_ID = "00000000-0000-0000-0000-000000000001"

async def get_all_events(user_id: str) -> List[Dict[str, Any]]:
    """Fetch calendar events visible to the user."""
    # [ROBUSTNESS] Split into two simple queries to avoid fragile OR/JSON syntax in one call.
    
    # query 1: Events Created by Me
    # [FIX] Explicit relationship name to avoid ambiguity (created_by vs user_id)
    t1 = asyncio.to_thread(lambda: supabase.table("calendar_events").select("*, profiles!calendar_events_created_by_fkey(full_name)").eq("created_by", user_id).execute())
    
    # query 2: Events with Me as Participant (JSONB Containment)
    # Note: participant_ids.cs.[user_id]
    # If list is empty, this query might fail or return nothing.
    t2 = asyncio.to_thread(lambda: supabase.table("calendar_events").select("*, profiles!calendar_events_created_by_fkey(full_name)").contains("participant_ids", [user_id]).execute())
    
    # Run in parallel
    res1, res2 = await asyncio.gather(t1, t2)
    
    # Merge and Deduplicate by ID
    events_map = {}
    if res1.data:
        for e in res1.data: events_map[e['id']] = e
    if res2.data:
        for e in res2.data: events_map[e['id']] = e
        
    return list(events_map.values())

async def delete_event(event_id: str):
    """Delete an event by ID."""
    # TODO: Verify ownership? View handles it? 
    # Service should ideally check too.
    await asyncio.to_thread(lambda: supabase.table("calendar_events").delete().eq("id", event_id).execute())

async def load_profiles() -> List[Dict[str, Any]]:
    """Fetch all user profiles."""
    res = await asyncio.to_thread(lambda: supabase.table("profiles").select("id, full_name").execute())
    return res.data or []

async def create_event(event_data: Dict[str, Any]):
    """Create a new calendar event."""
    await asyncio.to_thread(lambda: supabase.table("calendar_events").insert(event_data).execute())
