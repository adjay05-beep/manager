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
    topics = resp.json()
    print("\n--- TOPICS ---")
    for t in topics:
        print(f"ID: {t['id']}, Name: {t['name']}")

    # Check last messages with topic info
    res = httpx.get(f"{url}/rest/v1/chat_messages?select=*,profiles(full_name)&order=created_at.desc&limit=5", headers=headers)
    if res.status_code == 200:
        msgs = res.json()
        print("\n--- LAST 5 MESSAGES ---")
        for m in msgs:
            print(f"ID: {m['id']}, TopicID: {m['topic_id']}, Content: {m['content']}, Image URL: {m.get('image_url')}")
    else:
        print(f"FAILED: {res.status_code} {res.text}")

if __name__ == "__main__":
    diag()
