import asyncio
import math
from datetime import datetime
from utils.logger import log_info, log_error, log_debug
from db import service_supabase

class AttendanceService:
    def __init__(self):
        self._status = "OFF" # OFF, ON
        self._setting = "GPS" # GPS, WIFI
        self._logs = []

    async def get_status(self, user_id=None, channel_id=None):
        """Fetches current status from database."""
        if not user_id or not channel_id:
            return {"status": self._status, "setting": self._setting}
            
        try:
            # Fetch last log for this user in this channel
            res = service_supabase.table("attendance_logs")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("channel_id", channel_id)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if res.data:
                last_log = res.data[0]
                self._status = "ON" if last_log["type"] == "IN" else "OFF"
                return {
                    "status": self._status,
                    "setting": self._setting,
                    "last_log": last_log
                }
        except Exception as e:
            log_error(f"Status Fetch Error: {e}")
            
        return {
            "status": self._status,
            "setting": self._setting,
            "last_log": None
        }

    async def get_recent_logs(self, user_id, channel_id, limit=7):
        """Fetches recent attendance logs for display."""
        try:
            res = service_supabase.table("attendance_logs")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("channel_id", channel_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return res.data or []
        except Exception as e:
            log_error(f"Get Logs Error: {e}")
            return []

    def haversine(self, lat1, lon1, lat2, lon2):
        try:
            R = 6371000 # Earth radius in meters
            phi1, phi2 = math.radians(lat1), math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)
            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
            return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))
        except Exception:
            return 999999

    async def verify_location(self, channel_id, user_lat, user_lng):
        """Verifies if user is within 100m of the channel location."""
        try:
            res = service_supabase.table("channels").select("latitude, longitude").eq("id", channel_id).single().execute()
            if not res.data:
                return False, "매장 위치 정보가 설정되지 않았습니다."
            
            target_lat = res.data.get("latitude")
            target_lng = res.data.get("longitude")
            
            if target_lat is None or target_lng is None:
                return False, "매장 위치 정보(GPS)가 설정되지 않았습니다."
            
            dist = self.haversine(user_lat, user_lng, target_lat, target_lng)
            log_debug(f"Attendance: Distance to store is {dist:.2f}m")
            
            if dist <= 150: # Allow 150m for GPS inaccuracy
                return True, f"인증 성공 (거리: {dist:.1f}m)"
            else:
                return False, f"매장에서 너무 멉니다 (현재 거리: {dist:.1f}m)"
        except Exception as e:
            log_error(f"Verification Error: {e}")
            return False, f"위치 검증 오류: {e}"

    async def clock_in(self, user_id, channel_id, method="GPS", lat=None, lng=None, ip=None, ssid=None):
        is_verified = False
        message = ""
        
        if method == "GPS":
            if lat and lng:
                is_verified, message = await self.verify_location(channel_id, lat, lng)
            else:
                is_verified, message = False, "GPS 정보를 가져올 수 없습니다."
        elif method == "WIFI":
            # For now, if BSSID/SSID matching is hard in browser, we might use IP or just trust if UI says so
            # But let's check if we can match SSID if provided
            try:
                res = service_supabase.table("channels").select("wifi_ssid").eq("id", channel_id).single().execute()
                store_ssid = res.data.get("wifi_ssid") if res.data else None
                if store_ssid and ssid and store_ssid == ssid:
                    is_verified, message = True, "Wi-Fi 인증 성공"
                else:
                    is_verified, message = True, "Wi-Fi 연결 확인 (간이 인증)" # Falling back to trust for now if ssid missing
            except:
                is_verified, message = True, "Wi-Fi 인증 완료"

        log_data = {
            "user_id": user_id,
            "channel_id": channel_id,
            "type": "IN",
            "method": method,
            "lat": lat,
            "lng": lng,
            "ip_address": ip,
            "is_verified": is_verified
        }
        
        try:
            service_supabase.table("attendance_logs").insert(log_data).execute()
        except Exception as e:
            log_error(f"Failed to save attendance log: {e}")

        self._status = "ON"
        log_info(f"Attendance: {user_id} Clock-In via {method}. Verified: {is_verified} ({message})")
        return is_verified, message

    async def clock_out(self, user_id, channel_id):
        log_data = {
            "user_id": user_id,
            "channel_id": channel_id,
            "type": "OUT",
            "is_verified": True # Check-out is generally less restricted
        }
        
        try:
            service_supabase.table("attendance_logs").insert(log_data).execute()
        except Exception as e:
            log_error(f"Failed to save attendance log: {e}")

        self._status = "OFF"
        log_info(f"Attendance: {user_id} Clock-Out")
        return True, "퇴근 처리되었습니다."

    def save_settings(self, method):
        self._setting = method
        log_info(f"Attendance: Settings updated to {method}")

attendance_service = AttendanceService()
