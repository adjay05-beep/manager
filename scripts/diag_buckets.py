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
    # List ALL Buckets
    resp = httpx.get(f"{url}/storage/v1/bucket", headers=headers)
    if resp.status_code == 200:
        buckets = resp.json()
        print("\n--- ALL BUCKETS ---")
        for b in buckets:
            print(f"- ID: {b['id']}, Name: {b['name']}, Public: {b['public']}")
    else:
        print(f"FAILED: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    diag()
