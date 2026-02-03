from datetime import datetime
import os

def sys_log(m):
    try:
        with open("system_logs.txt", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {m}\n")
    except Exception as e:
        print(f"CRITICAL: Failed to write system log: {e}")
