import asyncio
from typing import List, Dict, Any
from db import supabase

CURRENT_USER_ID = "00000000-0000-0000-0000-000000000001"

async def get_memos() -> List[Dict[str, Any]]:
    """Fetch all order memos."""
    try:
        res = await asyncio.to_thread(lambda: supabase.table("order_memos").select("*").order("created_at", desc=True).execute())
        return res.data or []
    except Exception as e:
        print(f"Service Error (get_memos): {e}")
        return []

async def update_memo_content(memo_id: str, new_content: str):
    """Update the content of a memo."""
    await asyncio.to_thread(lambda: supabase.table("order_memos").update({"content": new_content}).eq("id", memo_id).execute())

async def delete_memo(memo_id: str):
    """Delete a memo."""
    await asyncio.to_thread(lambda: supabase.table("order_memos").delete().eq("id", memo_id).execute())

async def delete_all_memos(user_id: str = CURRENT_USER_ID):
    """Delete all memos for a user."""
    await asyncio.to_thread(lambda: supabase.table("order_memos").delete().eq("user_id", user_id).execute())

async def save_transcription(text: str, user_id: str = CURRENT_USER_ID):
    """Save transcribed text as a new memo."""
    await asyncio.to_thread(lambda: supabase.table("order_memos").insert({"content": text, "user_id": user_id}).execute())

async def get_voice_prompts() -> List[Dict[str, Any]]:
    """Fetch voice prompts dictionary."""
    try:
        res = await asyncio.to_thread(lambda: supabase.table("voice_prompts").select("*").order("created_at").execute())
        return res.data or []
    except Exception as e:
        print(f"Service Error (get_voice_prompts): {e}")
        return []

async def delete_voice_prompt(prompt_id: str):
    """Delete a voice prompt."""
    await asyncio.to_thread(lambda: supabase.table("voice_prompts").delete().eq("id", prompt_id).execute())

async def add_voice_prompt(keyword: str, user_id: str = CURRENT_USER_ID):
    """Add a new voice prompt keyword."""
    await asyncio.to_thread(lambda: supabase.table("voice_prompts").insert({
        "keyword": keyword, 
        "user_id": user_id
    }).execute())
