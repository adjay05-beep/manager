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
    # Check last messages
    res = httpx.get(f"{url}/rest/v1/chat_messages?select=*&order=created_at.desc&limit=5", headers=headers)
    if res.status_code == 200:
        msgs = res.json()
        print("\n--- LAST 5 MESSAGES ---")
        for m in msgs:
            print(f"ID: {m['id']}, Content: {m['content']}, Image URL: {m.get('image_url')}")
    else:
        print(f"FAILED TO FETCH MESSAGES: {res.status_code} {res.text}")

if __name__ == "__main__":
    diag()
