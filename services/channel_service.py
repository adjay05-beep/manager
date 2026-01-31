from typing import List, Dict, Any
import os
from db import service_supabase, log_info, has_service_key, url
from utils.logger import log_error

class ChannelService:
    def get_user_channels(self, user_id: str, access_token: str = None) -> List[Dict[str, Any]]:
        """
        Fetch all channels a user belongs to.
        Returns list of dicts: {id, name, role, channel_code, ...}
        """
        try:
            # [FIX] Render/Mobile RLS Issue
            # If we don't have a Service Key (Admin), we MUST use the User's Auth Token
            # otherwise the Anon client will be blocked by RLS policies on 'channel_members'.
            
            client = service_supabase
            if not has_service_key:
                headers = {}
                if access_token:
                     headers = {
                        "Authorization": f"Bearer {access_token}",
                        "apikey": os.environ.get("SUPABASE_KEY"),
                        "Content-Type": "application/json"
                     }
                else:
                    from services.auth_service import auth_service
                    headers = auth_service.get_auth_headers()
                
                # Ensure we have a token
                if "Authorization" in headers:
                    from postgrest import SyncPostgrestClient
                    client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public")
            
            res = client.table("channel_members")\
                .select("role, joined_at, channel:channels(*)")\
                .eq("user_id", user_id)\
                .execute()
            
            channels = []
            if res.data:
                for item in res.data:
                    ch = item.get("channel")
                    if ch:
                        # flatten structure for easier consumption
                        ch["role"] = item.get("role")
                        ch["joined_at"] = item.get("joined_at")
                        channels.append(ch)
            return channels
        except Exception as e:
            log_info(f"Error fetching user channels: {e}")
            return []

    def create_channel(self, user_id: str, name: str, business_number: str = None, business_owner: str = None) -> Dict[str, Any]:
        """Create a new channel and make user the owner. Optionally store business verification info."""
        try:
            # 1. Create Channel
            # [SECURITY] 암호학적으로 안전한 코드 생성
            import secrets
            code = secrets.token_urlsafe(8)[:8].upper()
            
            payload = {
                "name": name,
                "owner_id": user_id,
                "channel_code": code
            }
            if business_number:
                payload["business_number"] = business_number
                payload["business_owner_name"] = business_owner
                payload["is_verified"] = True

            res = service_supabase.table("channels").insert(payload).execute()
            
            if not res.data:
                raise Exception("Failed to create channel record")
            
            new_channel = res.data[0]
            cid = new_channel['id']
            
            # 2. Add as Owner (Role='owner')
            service_supabase.table("channel_members").insert({
                "channel_id": cid,
                "user_id": user_id,
                "role": "owner"
            }).execute()
            
            # Return full object with role
            new_channel["role"] = "owner"
            return new_channel
            
        except Exception as e:
            log_info(f"Error creating channel: {e}")
            raise e

    def join_channel(self, user_id: str, channel_code: str) -> Dict[str, Any]:
        """Join a channel via expiring invite code."""
        try:
            from datetime import datetime, timezone
            
            # 1. Find valid invite code
            now = datetime.now(timezone.utc).isoformat()
            res = service_supabase.table("invite_codes")\
                .select("*, channels(*)")\
                .eq("code", channel_code)\
                .gt("expires_at", now)\
                .execute()
            
            if not res.data:
                raise Exception("유효하지 않거나 만료된 초대 코드입니다.")
            
            invite = res.data[0]
            channel = invite.get("channels")
            if isinstance(channel, list): channel = channel[0]
            cid = channel['id']
            
            # 2. Check if already member
            check = service_supabase.table("channel_members").select("*")\
                .eq("channel_id", cid).eq("user_id", user_id).execute()
            
            if check.data:
                raise Exception("이미 가입된 매장입니다.")
            
            # 3. Add Member
            service_supabase.table("channel_members").insert({
                "channel_id": cid,
                "user_id": user_id,
                "role": "staff"
            }).execute()
            
            # 4. Update usage count
            service_supabase.table("invite_codes")\
                .update({"used_count": invite.get("used_count", 0) + 1})\
                .eq("id", invite["id"]).execute()
            
            channel["role"] = "staff"
            return channel
            
        except Exception as e:
            log_info(f"Error joining channel: {e}")
            raise e

    def get_channel_role(self, channel_id: int, user_id: str) -> str:
        """Fetch user's role in a specific channel."""
        try:
            res = service_supabase.table("channel_members").select("role")\
                .eq("channel_id", channel_id).eq("user_id", user_id).single().execute()
            if res.data:
                return res.data.get("role", "staff")
            return "staff"
        except Exception as e:
            log_info(f"Failed to get channel role: channel={channel_id}, user={user_id}, error={e}")
            return "staff"

    def update_channel(self, channel_id: int, name: str):
        """Update channel info (e.g. name)."""
        try:
             service_supabase.table("channels").update({"name": name}).eq("id", channel_id).execute()
        except Exception as e:
            raise e

    def generate_invite_code(self, channel_id: int, user_id: str, duration_minutes: int = 10) -> str:
        """Generate a time-limited invite code."""
        try:
            from datetime import datetime, timedelta, timezone
            import secrets

            # [SECURITY] 암호학적으로 안전한 초대 코드 생성
            code = secrets.token_urlsafe(8)[:8].upper()
            
            # Calculate expiration
            expires_at = (datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)).isoformat()
            
            # Insert
            res = service_supabase.table("invite_codes").insert({
                "channel_id": channel_id,
                "code": code,
                "created_by": user_id,
                "expires_at": expires_at
            }).execute()
            
            if res.data:
                return code
            raise Exception("Failed to generate code")
            
        except Exception as e:
            log_info(f"Error generating invite code: {e}")
            raise e

    def get_active_invite_codes(self, channel_id: int):
        """Get all active (non-expired) invite codes for a channel."""
        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            
            res = service_supabase.table("invite_codes")\
                .select("*")\
                .eq("channel_id", channel_id)\
                .gt("expires_at", now)\
                .order("created_at", desc=True)\
                .execute()
            
            return res.data or []
        except Exception as e:
            log_info(f"Error fetching invite codes: {e}")
            return []

    def get_channel_members_with_profiles(self, channel_id: int, access_token: str = None) -> List[Dict[str, Any]]:
        """Fetch members with their profile details."""
        try:
             # [FIX] RLS Support
             client = service_supabase
             if not has_service_key:
                 if access_token:
                     from services.auth_service import auth_service
                     headers = {
                        "Authorization": f"Bearer {access_token}",
                        "apikey": os.environ.get("SUPABASE_KEY"),
                        "Content-Type": "application/json"
                     }
                     from postgrest import SyncPostgrestClient
                     client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public")
                     log_info(f"DEBUG_MEMBER: Using User Token for Channel {channel_id}")
                 else:
                     log_info("Warning: No access_token provided for get_channel_members_with_profiles, RLS may block results.")

             res = client.table("channel_members").select("role, user_id, joined_at, profiles(full_name, username)")\
                .eq("channel_id", channel_id).execute()
             
             log_info(f"DEBUG_MEMBER: Query Result Count = {len(res.data) if res.data else 0}")
             
             members = []
             if res.data:
                 for m in res.data:
                     profile = m.get("profiles") or {}
                     members.append({
                         "user_id": m["user_id"],
                         "role": m["role"],
                         "joined_at": m["joined_at"],
                         "full_name": profile.get("full_name") or "Unknown",
                         "username": profile.get("username")
                     })
             return members
        except Exception as e:
            log_info(f"Error fetching members: {e}")
            return []

    def transfer_channel_ownership(self, channel_id: int, new_owner_id: str, token: str = None):
        """Transfer ownership of a channel to another member."""
        try:
            client = service_supabase
            if token and not has_service_key:
                from postgrest import SyncPostgrestClient
                headers = {
                   "Authorization": f"Bearer {token}",
                   "apikey": os.environ.get("SUPABASE_KEY"),
                   "Content-Type": "application/json"
                }
                client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public")

            # 1. Update Channel Metadata
            client.table("channels").update({"owner_id": new_owner_id}).eq("id", channel_id).execute()
            
            # 2. Update Memberships 
            # Promote new owner
            client.table("channel_members").update({"role": "owner"}).eq("channel_id", channel_id).eq("user_id", new_owner_id).execute()
            
            # 3. Demote current owner(s) who are NOT the new owner
            client.table("channel_members").update({"role": "manager"})\
                .eq("channel_id", channel_id)\
                .eq("role", "owner")\
                .neq("user_id", new_owner_id)\
                .execute()
                
            return True
        except Exception as e:
            log_error(f"Transfer Ownership Failed: {e}")
            raise e

    def _verify_admin_permission(self, channel_id: int, user_id: str) -> bool:
        """Verify user has admin (owner/manager) permission in channel."""
        try:
            res = service_supabase.table("channel_members").select("role")\
                .eq("channel_id", channel_id).eq("user_id", user_id).single().execute()
            if res.data and res.data.get("role") in ["owner", "manager"]:
                return True
            return False
        except Exception as e:
            log_info(f"Permission check error: {e}")
            return False

    def update_member_role(self, channel_id: int, target_user_id: str, new_role: str, requesting_user_id: str = None, token: str = None):
        """Update a member's role with permission check."""
        # [SECURITY] 권한 검증 - owner/manager만 역할 변경 가능
        if requesting_user_id:
            if not self._verify_admin_permission(channel_id, requesting_user_id):
                raise PermissionError("멤버 역할을 변경할 권한이 없습니다.")

            # Owner role은 owner만 부여 가능
            if new_role == "owner":
                current_role = self.get_channel_role(channel_id, requesting_user_id)
                if current_role != "owner":
                    raise PermissionError("Owner 역할은 현재 Owner만 부여할 수 있습니다.")

        try:
            client = service_supabase
            if token and not has_service_key:
                from postgrest import SyncPostgrestClient
                headers = {
                   "Authorization": f"Bearer {token}",
                   "apikey": os.environ.get("SUPABASE_KEY"),
                   "Content-Type": "application/json"
                }
                client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public")

            client.table("channel_members").update({"role": new_role})\
                .eq("channel_id", channel_id).eq("user_id", target_user_id).execute()
            log_info(f"Role updated: channel={channel_id}, user={target_user_id}, new_role={new_role}")
        except Exception as e:
            log_error(f"Role Update Failed: {e}")
            raise e

    def remove_member(self, channel_id: int, target_user_id: str, requesting_user_id: str = None, token: str = None):
        """Remove a member from the channel with permission check."""
        # [SECURITY] 권한 검증
        if requesting_user_id:
            if not self._verify_admin_permission(channel_id, requesting_user_id):
                raise PermissionError("멤버를 내보낼 권한이 없습니다.")

            # Owner는 삭제 불가 (ownership transfer 필요)
            target_role = self.get_channel_role(channel_id, target_user_id)
            if target_role == "owner":
                raise PermissionError("Owner는 직접 나가거나 다른 사람에게 소유권을 이전해야 합니다.")

        try:
            client = service_supabase
            if token and not has_service_key:
                from postgrest import SyncPostgrestClient
                headers = {
                   "Authorization": f"Bearer {token}",
                   "apikey": os.environ.get("SUPABASE_KEY"),
                   "Content-Type": "application/json"
                }
                client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public")

            client.table("channel_members").delete()\
                .eq("channel_id", channel_id).eq("user_id", target_user_id).execute()
            log_info(f"Member removed: channel={channel_id}, user={target_user_id}")
        except Exception as e:
            log_error(f"Member Removal Failed: {e}")
            raise e

# Singleton
channel_service = ChannelService()
