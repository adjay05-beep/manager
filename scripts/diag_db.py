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
    # Check topics
    resp = httpx.get(f"{url}/rest/v1/chat_topics?select=id,name", headers=headers)
    if resp.status_code == 200:
        topics = resp.json()
        print(f"\n--- TOPICS ({len(topics)}) ---")
        for t in topics:
            print(f"- {t['name']}")
    else:
        print(f"FAILED TO FETCH TOPICS: {resp.status_code}")

if __name__ == "__main__":
    diag()
