import asyncio
from typing import List, Dict, Any
from db import service_supabase
from utils.logger import log_error

async def get_memos(user_id: str) -> List[Dict[str, Any]]:
    """Fetch all order memos for the user."""
    try:
        res = await asyncio.to_thread(lambda: service_supabase.table("order_memos").select("*").eq("user_id", user_id).order("created_at", desc=True).execute())
        return res.data or []
    except Exception as e:
        log_error(f"Service Error (get_memos): {e}")
        return []

async def update_memo_content(memo_id: str, new_content: str, user_id: str):
    """Update the content of a memo with ownership verification."""
    # [SECURITY] 소유권 검증
    check = await asyncio.to_thread(lambda: service_supabase.table("order_memos").select("user_id").eq("id", memo_id).execute())
    if not check.data or check.data[0].get("user_id") != user_id:
        raise PermissionError("본인이 작성한 메모만 수정할 수 있습니다.")

    await asyncio.to_thread(lambda: service_supabase.table("order_memos").update({"content": new_content}).eq("id", memo_id).execute())

async def delete_memo(memo_id: str, user_id: str):
    """Delete a memo with ownership verification."""
    # [SECURITY] 소유권 검증
    check = await asyncio.to_thread(lambda: service_supabase.table("order_memos").select("user_id").eq("id", memo_id).execute())
    if not check.data or check.data[0].get("user_id") != user_id:
        raise PermissionError("본인이 작성한 메모만 삭제할 수 있습니다.")

    await asyncio.to_thread(lambda: service_supabase.table("order_memos").delete().eq("id", memo_id).execute())

async def delete_all_memos(user_id: str):
    """Delete all memos for a user."""
    await asyncio.to_thread(lambda: service_supabase.table("order_memos").delete().eq("user_id", user_id).execute())

async def save_transcription(text: str, user_id: str, channel_id: int = None):
    """Save transcribed text as a new memo."""
    if not text or not text.strip():
        return

    data = {"content": text.strip(), "user_id": user_id}
    if channel_id:
        data["channel_id"] = channel_id

    await asyncio.to_thread(lambda: service_supabase.table("order_memos").insert(data).execute())

async def get_voice_prompts() -> List[Dict[str, Any]]:
    """Fetch voice prompts dictionary."""
    try:
        res = await asyncio.to_thread(lambda: service_supabase.table("voice_prompts").select("*").order("created_at").execute())
        return res.data or []
    except Exception as e:
        log_error(f"Service Error (get_voice_prompts): {e}")
        return []

async def delete_voice_prompt(prompt_id: str):
    """Delete a voice prompt."""
    await asyncio.to_thread(lambda: service_supabase.table("voice_prompts").delete().eq("id", prompt_id).execute())

async def add_voice_prompt(keyword: str, user_id: str):
    """Add a new voice prompt keyword. user_id is required."""
    if not keyword or not keyword.strip():
        return
    if not user_id:
        raise ValueError("user_id is required")

    await asyncio.to_thread(lambda: service_supabase.table("voice_prompts").insert({
        "keyword": keyword.strip(),
        "user_id": user_id
    }).execute())
