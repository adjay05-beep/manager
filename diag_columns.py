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

def diag():
    # Fetch 1 message and print all keys
    res = httpx.get(f"{url}/rest/v1/chat_messages?limit=1", headers=headers)
    if res.status_code == 200:
        data = res.json()
        if data:
            print("\n--- ACTUAL COLUMN NAMES ---")
            for k in data[0].keys():
                print(f"- {k}")
            print(f"\nFull Row: {data[0]}")
    else:
        print(f"FAILED: {res.status_code} {res.text}")

if __name__ == "__main__":
    diag()
