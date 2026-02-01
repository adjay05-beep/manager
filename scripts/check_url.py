import httpx
import os
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
# Use the URL from the user's screenshot
test_url = "https://vtsttqtbewxkxxdoyhrj.supabase.co/storage/v1/object/public/uploads/chat_20260125020902_logo.png"

def check():
    print(f"Testing URL: {test_url}")
    try:
        resp = httpx.get(test_url)
        print(f"Status: {resp.status_code}")
        print(f"Headers: {resp.headers}")
        if resp.status_code != 200:
            print(f"Error Body: {resp.text}")
        else:
            print(f"Success! Content length: {len(resp.content)}")
    except Exception as e:
        print(f"Network Error: {e}")

if __name__ == "__main__":
    check()
