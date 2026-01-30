import asyncio
from db import service_supabase, log_info
from datetime import datetime

class HandoverService:
    async def get_handovers(self, channel_id: int):
        res = await asyncio.to_thread(lambda: service_supabase.table("handovers").select("*, profiles:user_id(full_name)").eq("channel_id", channel_id).order("created_at").execute())
        return res.data or []

    async def add_handover_entry(self, user_id, channel_id, category, content):
        data = {"user_id": user_id, "channel_id": channel_id, "content": content, "category": category, "created_at": datetime.now().isoformat()}
        await asyncio.to_thread(lambda: service_supabase.table("handovers").insert(data).execute())
        return True

    async def update_handover(self, handover_id, content):
        res = await asyncio.to_thread(lambda: service_supabase.table("handovers").update({"content": content, "updated_at": datetime.now().isoformat()}).eq("id", handover_id).execute())
        return bool(res.data)

    async def delete_handover(self, handover_id):
        await asyncio.to_thread(lambda: service_supabase.table("handovers").delete().eq("id", handover_id).execute())

handover_service = HandoverService()
