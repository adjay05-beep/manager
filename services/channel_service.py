from typing import List, Dict, Any
import os
from db import service_supabase, log_info, has_service_key, url

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

    def create_channel(self, user_id: str, name: str) -> Dict[str, Any]:
        """Create a new channel and make user the owner."""
        try:
            # 1. Create Channel
            # Generate a random code? Or let DB handle it? 
            # Our SQL didn't set default for channel_code. Let's gen one.
            import random, string
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            res = service_supabase.table("channels").insert({
                "name": name,
                "owner_id": user_id,
                "channel_code": code
            }).execute()
            
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
            from datetime import datetime
            
            # 1. Find valid invite code
            now = datetime.utcnow().isoformat()
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
        except:
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
            from datetime import datetime, timedelta
            import random, string
            
            # Generate unique code
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            # Calculate expiration
            expires_at = (datetime.utcnow() + timedelta(minutes=duration_minutes)).isoformat()
            
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
            from datetime import datetime
            now = datetime.utcnow().isoformat()
            
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

# Singleton
channel_service = ChannelService()
