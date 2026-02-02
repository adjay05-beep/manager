import asyncio
from datetime import datetime
from utils.logger import log_info

class AttendanceService:
    def __init__(self):
        self._status = "OFF" # OFF, ON
        self._setting = "GPS" # GPS, WIFI
        self._logs = []

    def get_status(self):
        return {
            "status": self._status,
            "setting": self._setting,
            "last_log": self._logs[-1] if self._logs else None
        }

    async def clock_in(self, method="GPS"):
        self._status = "ON"
        log = {
            "type": "IN",
            "time": datetime.now().strftime("%H:%M:%S"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "method": method
        }
        self._logs.append(log)
        log_info(f"Attendance: Clock-In at {log['time']} via {method}")
        return log

    async def clock_out(self):
        self._status = "OFF"
        log = {
            "type": "OUT",
            "time": datetime.now().strftime("%H:%M:%S"),
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        self._logs.append(log)
        log_info(f"Attendance: Clock-Out at {log['time']}")
        return log

    def save_settings(self, method):
        self._setting = method
        log_info(f"Attendance: Settings updated to {method}")

attendance_service = AttendanceService()
