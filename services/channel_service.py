from typing import List, Dict, Any
import os
from repositories.channel_repository import ChannelRepository
from utils.logger import log_error, log_info

# [PROFESSIONAL] Refactored to use Repository Pattern

class ChannelService:
    def get_user_channels(self, user_id: str, access_token: str = None) -> List[Dict[str, Any]]:
        """Fetch all channels a user belongs to."""
        try:
            return ChannelRepository.get_user_channels(user_id)
        except Exception as e:
            log_error(f"Error fetching user channels: {e}")
            return []

    def create_channel(self, user_id: str, name: str, business_number: str = None, business_owner: str = None) -> Dict[str, Any]:
        """Create a new channel and make user the owner."""
        try:
            import secrets
            from db import service_supabase
            code = secrets.token_urlsafe(8)[:8].upper()
            
            payload = {
                "name": name,
                "owner_id": user_id,
                "channel_code": code
            }
            if business_number:
                payload.update({"business_number": business_number, "business_owner_name": business_owner, "is_verified": True})

            res = service_supabase.table("channels").insert(payload).execute()
            if not res.data: raise Exception("Failed to create channel record")
            
            new_channel = res.data[0]
            ChannelRepository.create_membership(new_channel['id'], user_id, "owner")
            new_channel["role"] = "owner"
            return new_channel
        except Exception as e:
            log_error(f"Error creating channel: {e}")
            raise e

    def join_channel(self, user_id: str, channel_code: str) -> Dict[str, Any]:
        """Join a channel via invite code."""
        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()

            res = ChannelRepository.get_invite_by_code(channel_code, now)
            if not res.data:
                raise Exception("유효하지 않거나 만료된 초대 코드입니다.")

            invite = res.data[0]
            channel = invite.get("channels")

            # [FIX] channel이 리스트인 경우 처리
            if isinstance(channel, list):
                channel = channel[0] if channel else None

            # [FIX] channel이 None이거나 비어있는 경우 처리
            if not channel or not isinstance(channel, dict):
                raise Exception("채널 정보를 찾을 수 없습니다.")

            cid = channel.get('id')
            if not cid:
                raise Exception("채널 ID를 찾을 수 없습니다.")

            # Check if already member
            existing_role = ChannelRepository.get_member_role(cid, user_id)
            if existing_role:
                raise Exception("이미 가입된 매장입니다.")

            ChannelRepository.create_membership(cid, user_id, "staff")
            ChannelRepository.increment_invite_usage(invite["id"], invite.get("used_count", 0))

            channel["role"] = "staff"
            return channel
        except Exception as e:
            log_error(f"Error joining channel: {e}")
            raise e

    def get_channel_role(self, channel_id: int, user_id: str) -> str:
        """Fetch user's role in a specific channel."""
        role = ChannelRepository.get_member_role(channel_id, user_id)
        return role or "staff"

    def update_channel(self, channel_id: int, name: str):
        """Update channel name."""
        try:
             ChannelRepository.update_channel_name(channel_id, name)
        except Exception as e:
            log_error(f"Update channel error: {e}")
            raise e

    def generate_invite_code(self, channel_id: int, user_id: str, duration_minutes: int = 10) -> str:
        """Generate a time-limited invite code."""
        # [PERMISSION CHECK] Only owners and managers can generate new codes
        role = self.get_channel_role(channel_id, user_id)
        if role not in ["owner", "manager"]:
            raise PermissionError("초대 코드 생성 권한이 없습니다.")

        try:
            from datetime import datetime, timedelta, timezone
            import secrets
            code = secrets.token_urlsafe(8)[:8].upper()
            expires_at = (datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)).isoformat()
            
            res = ChannelRepository.create_invite_code(channel_id, code, user_id, expires_at)
            if res.data: return code
            raise Exception("Failed to generate code")
        except Exception as e:
            if not isinstance(e, PermissionError):
                log_error(f"Error generating invite code: {e}")
            raise e

    def get_active_invite_codes(self, channel_id: int):
        """Get all active invite codes."""
        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            res = ChannelRepository.get_active_invites(channel_id, now)
            return res.data or []
        except Exception as e:
            log_error(f"Error fetching invite codes: {e}")
            return []

    def get_channel_members_with_profiles(self, channel_id: int, access_token: str = None) -> List[Dict[str, Any]]:
        """Fetch members with their profile details."""
        try:
             return ChannelRepository.get_channel_members_with_profiles(channel_id)
        except Exception as e:
            log_error(f"Error fetching members: {e}")
            return []

    def transfer_channel_ownership(self, channel_id: int, new_owner_id: str, token: str = None):
        """Transfer ownership."""
        try:
            ChannelRepository.transfer_channel_ownership(channel_id, new_owner_id)
            return True
        except Exception as e:
            log_error(f"Transfer Ownership Failed: {e}")
            raise e

    def update_member_role(self, channel_id: int, target_user_id: str, new_role: str, requesting_user_id: str = None, token: str = None):
        """Update member role with permission check."""
        if requesting_user_id:
            req_role = self.get_channel_role(channel_id, requesting_user_id)
            if req_role not in ["owner", "manager"]: raise PermissionError("권한이 없습니다.")
            if new_role == "owner" and req_role != "owner": raise PermissionError("권한이 없습니다.")

        try:
            ChannelRepository.update_member_role(channel_id, target_user_id, new_role)
        except Exception as e:
            log_error(f"Role Update Failed: {e}")
            raise e

    def remove_member(self, channel_id: int, target_user_id: str, requesting_user_id: str = None, token: str = None):
        """Remove member from channel."""
        # Check target role first
        target_role = self.get_channel_role(channel_id, target_user_id)
        if target_role == "owner":
            raise PermissionError("매장 대표는 탈퇴하거나 내보낼 수 없습니다. 먼저 권한을 양도해주세요.")

        if requesting_user_id:
            # Allow verification if it's self-removal
            if requesting_user_id != target_user_id:
                # If removing someone else, must be owner or manager
                req_role = self.get_channel_role(channel_id, requesting_user_id)
                if req_role not in ["owner", "manager"]: 
                    raise PermissionError("권한이 없습니다.")

        try:
            ChannelRepository.remove_member(channel_id, target_user_id)
        except Exception as e:
            log_error(f"Member Removal Failed: {e}")
            raise e

    def update_location(self, channel_id: int, lat: float, lng: float, address: str = None):
        """Update store GPS position and address."""
        return ChannelRepository.update_channel_location(channel_id, lat, lng, address)

    def update_wifi(self, channel_id: int, ssid: str, bssid: str = None):
        """Update store Wi-Fi info."""
        return ChannelRepository.update_channel_wifi(channel_id, ssid, bssid)

    def get_channel_info(self, channel_id: int):
        """Get full channel details."""
        return ChannelRepository.get_channel_info(channel_id)

# Singleton
channel_service = ChannelService()

