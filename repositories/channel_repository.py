from db import service_supabase
from utils.logger import log_error

class ChannelRepository:
    """
    Handles all direct interactions with channels, members, and roles.
    """
    @staticmethod
    def get_user_channels(user_id, token=None):
        """Fetch all channels the user is a member of."""
        try:
            res = service_supabase.table("channel_members")\
                .select("role, channels(id, name, channel_code, latitude, longitude, wifi_ssid, wifi_bssid, address)")\
                .eq("user_id", user_id)\
                .execute()

            channels = []
            # [FIX] NoneType 접근 방지
            for item in (res.data or []):
                ch = item.get("channels")
                if not ch:
                    continue  # channels가 None이면 건너뜀
                # channels가 리스트인 경우 처리
                if isinstance(ch, list):
                    ch = ch[0] if ch else None
                if not ch:
                    continue
                ch["role"] = item.get("role", "staff")
                channels.append(ch)
            return channels
        except Exception as e:
            log_error(f"ChannelRepository.get_user_channels error: {e}")
            return []

    @staticmethod
    def get_channel_members(channel_id):
        """Fetch all members of a specific channel."""
        res = service_supabase.table("channel_members")\
            .select("role, profiles(id, full_name, role)")\
            .eq("channel_id", channel_id)\
            .execute()
        return res.data or []

    @staticmethod
    def update_member_role(channel_id, user_id, new_role):
        """Update a member's role within a channel."""
        return service_supabase.table("channel_members")\
            .update({"role": new_role})\
            .eq("channel_id", channel_id)\
            .eq("user_id", user_id)\
            .execute()

    @staticmethod
    def remove_member(channel_id, user_id):
        """Remove a member from a channel."""
        return service_supabase.table("channel_members")\
            .delete()\
            .eq("channel_id", channel_id)\
            .eq("user_id", user_id)\
            .execute()

    @staticmethod
    def get_member_role(channel_id, user_id):
        """Fetch specific member's role."""
        try:
            res = service_supabase.table("channel_members")\
                .select("role")\
                .eq("channel_id", channel_id)\
                .eq("user_id", user_id)\
                .single().execute()
            return res.data["role"] if res.data else None
        except Exception:
            return None

    @staticmethod
    def update_channel_name(channel_id, name):
        """Update channel name."""
        return service_supabase.table("channels").update({"name": name}).eq("id", channel_id).execute()

    @staticmethod
    def get_channel_members_with_profiles(channel_id, token=None):
        """Fetch members with profile details."""
        # Professional: use token if provided, but for consistency using service_role
        res = service_supabase.table("channel_members")\
            .select("role, user_id, joined_at, profiles(full_name, avatar_url)")\
            .eq("channel_id", channel_id)\
            .execute()
        
        members = []
        for m in res.data:
            p = m.get("profiles") or {}
            members.append({
                "user_id": m["user_id"],
                "role": m["role"],
                "joined_at": m["joined_at"],
                "full_name": p.get("full_name", "Unknown"),
                "avatar_url": p.get("avatar_url")
            })
        return members

    @staticmethod
    def transfer_channel_ownership(channel_id, new_owner_id, token=None):
        """Atomic-like ownership transfer."""
        # 1. Update Channel
        service_supabase.table("channels").update({"owner_id": new_owner_id}).eq("id", channel_id).execute()
        # 2. Promote New
        service_supabase.table("channel_members").update({"role": "owner"}).eq("channel_id", channel_id).eq("user_id", new_owner_id).execute()
        # 3. Demote Old (simplified)
        service_supabase.table("channel_members").update({"role": "manager"}).eq("channel_id", channel_id).eq("role", "owner").neq("user_id", new_owner_id).execute()

    @staticmethod
    def get_invite_by_code(code, current_time_iso):
        """Find active invite code."""
        return service_supabase.table("invite_codes")\
            .select("*, channels(*)")\
            .eq("code", code)\
            .gt("expires_at", current_time_iso)\
            .execute()

    @staticmethod
    def increment_invite_usage(invite_id, current_count):
        """Increment usage count."""
        return service_supabase.table("invite_codes")\
            .update({"used_count": current_count + 1})\
            .eq("id", invite_id).execute()

    @staticmethod
    def create_invite_code(channel_id, code, user_id, expires_at_iso):
        """Insert new invite code."""
        return service_supabase.table("invite_codes").insert({
            "channel_id": channel_id,
            "code": code,
            "created_by": user_id,
            "expires_at": expires_at_iso
        }).execute()

    @staticmethod
    def get_active_invites(channel_id, current_time_iso):
        """Fetch active codes."""
        return service_supabase.table("invite_codes")\
            .select("*")\
            .eq("channel_id", channel_id)\
            .gt("expires_at", current_time_iso)\
            .order("created_at", desc=True)\
            .execute()

    @staticmethod
    def create_membership(channel_id, user_id, role="staff"):
        """Add member to channel."""
        return service_supabase.table("channel_members").insert({
            "channel_id": channel_id,
            "user_id": user_id,
            "role": role
        }).execute()

    @staticmethod
    def update_channel_location(channel_id, lat, lng, address=None):
        """Update GPS coordinates and address for a channel."""
        data = {"latitude": lat, "longitude": lng}
        if address:
            data["address"] = address
        return service_supabase.table("channels")\
            .update(data)\
            .eq("id", channel_id).execute()

    @staticmethod
    def update_channel_wifi(channel_id, ssid, bssid):
        """Update Wi-Fi info for a channel."""
        return service_supabase.table("channels")\
            .update({"wifi_ssid": ssid, "wifi_bssid": bssid})\
            .eq("id", channel_id).execute()

    @staticmethod
    def get_channel_info(channel_id):
        """Fetch full channel info including location."""
        res = service_supabase.table("channels").select("*").eq("id", channel_id).single().execute()
        return res.data
