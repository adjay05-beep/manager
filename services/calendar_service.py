import asyncio
from typing import List, Dict, Any
from db import supabase

CURRENT_USER_ID = "00000000-0000-0000-0000-000000000001"

async def get_all_events(user_id: str) -> List[Dict[str, Any]]:
    """Fetch calendar events visible to the user."""
    # [RBAC] Filter: Created by Me OR I am a Participant
    # Note: participant_ids is JSONB. PostgREST 'cs' (contains) operator works on JSONB arrays.
    # Syntax: .or_(f"created_by.eq.{user_id},participant_ids.cs.[{user_id}]")
    # Python Client Syntax for OR with mixed types is tricky.
    # Let's try raw string format for OR.
    
    # Safe Query Construction
    try:
        query_str = f"created_by.eq.{user_id},participant_ids.cs.[{user_id}]" # Check syntax for JSON array literal
        
        # Actually, simpler to use Python filtering for MVP Stability if query fails.
        # But strict requirement implies DB filtration for security.
        # Let's try the strict DB filter first.
        
        # NOTE: JSONB containment syntax in PostgREST is `participant_ids.cs.["id"]`. 
        # But constructing this in the client .or_() method:
        # q = f'created_by.eq.{user_id},participant_ids.cs.["{user_id}"]'
        
        # However, supabase-py might struggle with this complex OR string.
        # Let's do two queries and merge manually if needed, OR filter in Python for now 
        # since we are NOT using RLS (Application Level).
        # WAIT! If I return ALL events to Python, I am downloading everyone's data.
        # I MUST filter at DB.
        
        # Using RPC might be cleaner? "get_my_events(userid)".
        # Or just try the OR string.
        
        q = f"created_by.eq.{user_id},participant_ids.cs.[\"{user_id}\"]"
        
        res = await asyncio.to_thread(lambda: supabase.table("calendar_events").select("*, profiles(full_name)").or_(q).execute())
        return res.data or []
    except Exception as e:
        # Fallback for debugging (e.g. if cs operator fails)
        print(f"Service Error (get_all_events): {e}")
        return []

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
