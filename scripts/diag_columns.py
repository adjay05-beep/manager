import os
import httpx
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}"
}

tables = ["chat_messages", "voice_memos", "order_memos", "calendars", "calendar_members", "orders", "channel_members", "channels", "calendar_events"]

def diag():
    for t in tables:
        print(f"\n--- TABLE: {t} ---")
        try:
            res = httpx.get(f"{url}/rest/v1/{t}?limit=1", headers=headers)
            if res.status_code == 200:
                data = res.json()
                if data:
                    print(f"Columns: {list(data[0].keys())}")
                else:
                    print("Empty table (Columns unknown via REST)")
            else:
                print(f"Error: {res.status_code} {res.text}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    diag()
