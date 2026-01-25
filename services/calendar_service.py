import asyncio
from typing import List, Dict, Any
from db import supabase

CURRENT_USER_ID = "00000000-0000-0000-0000-000000000001"

async def get_all_events() -> List[Dict[str, Any]]:
    """Fetch all calendar events."""
    try:
        res = await asyncio.to_thread(lambda: supabase.table("calendar_events").select("*, profiles(full_name)").execute())
        return res.data or []
    except Exception as e:
        print(f"Service Error (get_all_events): {e}")
        return []

async def delete_event(event_id: str):
    """Delete an event by ID."""
    await asyncio.to_thread(lambda: supabase.table("calendar_events").delete().eq("id", event_id).execute())

async def load_profiles() -> List[Dict[str, Any]]:
    """Fetch all user profiles."""
    try:
        res = await asyncio.to_thread(lambda: supabase.table("profiles").select("id, full_name").execute())
        return res.data or []
    except Exception as e:
        print(f"Service Error (load_profiles): {e}")
        return []

async def create_event(event_data: Dict[str, Any]):
    """Create a new calendar event."""
    # event_data should utilize keys matching the DB schema
    await asyncio.to_thread(lambda: supabase.table("calendar_events").insert(event_data).execute())
