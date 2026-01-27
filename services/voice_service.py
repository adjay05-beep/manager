import asyncio
from typing import List, Dict, Any
from db import service_supabase, log_info
from datetime import datetime, timedelta

class VoiceService:
    async def get_memos(self, user_id: str, channel_id: int = None) -> List[Dict[str, Any]]:
        """
        Fetch memos for a user in a specific channel context.
        """
        try:
            query = service_supabase.table("voice_memos").select("*, profiles:user_id(full_name)")
            
            if channel_id:
                # Syntax: (user_id=me & is_private=true) OR (channel_id=curr & is_private=false)
                or_filter = f"and(user_id.eq.{user_id},is_private.eq.true),and(channel_id.eq.{channel_id},is_private.eq.false)"
                res = await asyncio.to_thread(lambda: query.or_(or_filter).order("created_at", desc=True).execute())
            else:
                # No channel context? Just show my private ones?
                res = await asyncio.to_thread(lambda: query.eq("user_id", user_id).eq("is_private", True).order("created_at", desc=True).execute())
                
            return res.data or []
        except Exception as e:
            log_info(f"Voice Service Error: {e}")
            return []

    async def create_memo(self, user_id: str, channel_id: int, content: str = "", is_private: bool = True, audio_url: str = None) -> dict:
        """Create a new voice memo with dynamic retention based on channel tier."""
        try:
            # 1. Fetch Channel Tier
            tier = "free"
            if channel_id:
                try:
                    ch_res = await asyncio.to_thread(lambda: service_supabase.table("channels").select("subscription_tier").eq("id", channel_id).single().execute())
                    if ch_res.data:
                        tier = ch_res.data.get("subscription_tier", "free")
                except Exception as e:
                    print(f"Error fetching tier: {e}")
            
            # 2. Calculate Expiration based on Tier
            now = datetime.now()
            
            if tier == "free":
                audio_days = 3
                text_days = 30
                
                audio_exp = (now + timedelta(days=audio_days)).isoformat()
                text_exp = (now + timedelta(days=text_days)).isoformat()
                
            elif tier == "standard":
                audio_days = 30
                # Text unlimited (None)
                audio_exp = (now + timedelta(days=audio_days)).isoformat()
                text_exp = None
            else: # premium
                # Configurable? For now defaults.
                audio_exp = (now + timedelta(days=365)).isoformat()
                text_exp = None

            # 3. Insert
            data = {
                "user_id": user_id,
                "channel_id": channel_id,
                "content": content,
                "is_private": is_private, 
                "audio_url": audio_url,
                "audio_expires_at": audio_exp,
                "text_expires_at": text_exp
            }
            res = await asyncio.to_thread(lambda: service_supabase.table("voice_memos").insert(data).execute())
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            log_info(f"Create Memo Error: {e}")
            return None

    async def delete_memo(self, memo_id: str):
        """Delete memo."""
        await asyncio.to_thread(lambda: service_supabase.table("voice_memos").delete().eq("id", memo_id).execute())

    async def share_memo(self, memo_id: str, target: str):
        """Share (Publish) a private memo to Channel Public."""
        await asyncio.to_thread(lambda: service_supabase.table("voice_memos").update({"is_private": False}).eq("id", memo_id).execute())

    async def update_audio_url(self, memo_id: str, url: str):
         await asyncio.to_thread(lambda: service_supabase.table("voice_memos").update({"audio_url": url}).eq("id", memo_id).execute())

    async def cleanup_expired_memos(self):
        """
        Routine Maintenance:
        1. Delete Audio Files where audio_expires_at < NOW and audio_url IS NOT NULL
        2. Delete Records where text_expires_at < NOW
        """
        try:
            today_iso = datetime.now().isoformat()
            
            # 1. Expired Audio Cleanup
            # Fetch expired audio memos
            exp_audios = await asyncio.to_thread(lambda: service_supabase.table("voice_memos").select("id, audio_url").neq("audio_url", "null").lt("audio_expires_at", today_iso).execute())
            
            if exp_audios.data:
                paths_to_remove = []
                ids_to_update = []
                
                for item in exp_audios.data:
                    url = item.get("audio_url", "")
                    if "voice/" in url:
                        try:
                            if "chat-uploads/" in url:
                                path = url.split("chat-uploads/")[-1]
                                paths_to_remove.append(path)
                                ids_to_update.append(item['id'])
                        except: pass
                
                if paths_to_remove:
                    from services.chat_service import service_supabase as storage_client # Reuse admin client for storage
                    try:
                        # storage.remove expects list of paths
                        await asyncio.to_thread(lambda: storage_client.storage.from_("chat-uploads").remove(paths_to_remove))
                        print(f"Cleaned up {len(paths_to_remove)} expired audio files.")
                        
                        # Update DB to null
                        await asyncio.to_thread(lambda: service_supabase.table("voice_memos").update({"audio_url": None}).in_("id", ids_to_update).execute())
                    except Exception as stor_err:
                         print(f"Storage Cleanup Error: {stor_err}")

            # 2. Expired Record Cleanup
            # Delete rows where text_expires_at < NOW
            await asyncio.to_thread(lambda: service_supabase.table("voice_memos").delete().lt("text_expires_at", today_iso).execute())
            
        except Exception as e:
            log_info(f"Cleanup Error: {e}")

voice_service = VoiceService()
