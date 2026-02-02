import asyncio
from db import service_supabase, log_info
from datetime import datetime, timezone
from utils.logger import log_error

class HandoverService:
    async def _verify_channel_member(self, user_id: str, channel_id: int) -> bool:
        """[SECURITY] 사용자가 채널 멤버인지 확인."""
        try:
            check = await asyncio.to_thread(lambda: service_supabase.table("channel_members").select("user_id").eq("channel_id", channel_id).eq("user_id", user_id).execute())
            return len(check.data) > 0 if check.data else False
        except Exception:
            return False

    async def _verify_ownership(self, handover_id: str, user_id: str) -> bool:
        """[SECURITY] 인계사항 소유권 확인."""
        try:
            check = await asyncio.to_thread(lambda: service_supabase.table("handovers").select("user_id").eq("id", handover_id).execute())
            return check.data and check.data[0].get("user_id") == user_id
        except Exception:
            return False

    async def get_handovers(self, channel_id: int, user_id: str = None):
        """채널의 인계사항 조회 (채널 멤버만 가능)."""
        # [SECURITY] 채널 멤버 검증
        if user_id and not await self._verify_channel_member(user_id, channel_id):
            log_info(f"Handover access denied: user {user_id} not in channel {channel_id}")
            return []

        try:
            res = await asyncio.to_thread(lambda: service_supabase.table("handovers").select("*, profiles:user_id(full_name)").eq("channel_id", channel_id).order("created_at").execute())
            return res.data or []
        except Exception as e:
            log_error(f"Get handovers error: {e}")
            return []

    async def add_handover_entry(self, user_id: str, channel_id: int, category: str, content: str):
        """인계사항 추가 (채널 멤버만 가능)."""
        # [SECURITY] 채널 멤버 검증
        if not await self._verify_channel_member(user_id, channel_id):
            raise PermissionError("채널 멤버만 인계사항을 작성할 수 있습니다.")

        if not content or not content.strip():
            return False

        data = {
            "user_id": user_id,
            "channel_id": channel_id,
            "content": content.strip(),
            "category": category,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        try:
            await asyncio.to_thread(lambda: service_supabase.table("handovers").insert(data).execute())
            return True
        except Exception as e:
            log_error(f"Add handover error: {e}")
            return False

    async def update_handover(self, handover_id: str, content: str, user_id: str):
        """인계사항 수정 (채널 멤버 모두 가능)."""
        if not content or not content.strip():
            return False

        try:
            # [SECURITY] 1. 해당 인계사항의 채널 ID 조회
            check = await asyncio.to_thread(lambda: service_supabase.table("handovers").select("channel_id").eq("id", handover_id).execute())
            if not check.data:
                return False
            
            target_channel_id = check.data[0].get("channel_id")
            
            # [DEBUG]
            print(f"[DEBUG] update_handover: id={handover_id}, user={user_id}, target_ch={target_channel_id}")

            # [SECURITY] 2. 요청자가 해당 채널의 멤버인지 확인
            is_member = await self._verify_channel_member(user_id, target_channel_id)
            print(f"[DEBUG] is_member: {is_member}")

            if not is_member:
                 print(f"[DEBUG] Permission Denied: User {user_id} is not member of {target_channel_id}")
                 raise PermissionError("해당 채널의 멤버만 수정할 수 있습니다.")

            # 수정 실행
            print(f"[DEBUG] Executing update...")
            res = await asyncio.to_thread(lambda: service_supabase.table("handovers").update({
                "content": content.strip(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", handover_id).execute())
            return bool(res.data)
        except Exception as e:
            log_error(f"Update handover error: {e}")
            return False

    async def delete_handover(self, handover_id: str, user_id: str):
        """인계사항 삭제 (작성자만 가능)."""
        # [SECURITY] 소유권 검증
        if not await self._verify_ownership(handover_id, user_id):
            raise PermissionError("본인이 작성한 인계사항만 삭제할 수 있습니다.")

        try:
            await asyncio.to_thread(lambda: service_supabase.table("handovers").delete().eq("id", handover_id).execute())
            return True
        except Exception as e:
            log_error(f"Delete handover error: {e}")
            return False

handover_service = HandoverService()
