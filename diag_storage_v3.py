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
    # 1. Check Bucket Public Status
    resp = httpx.get(f"{url}/storage/v1/bucket/uploads", headers=headers)
    if resp.status_code == 200:
        b = resp.json()
        print(f"\nBucket 'uploads' -> Public: {b.get('public')}, ID: {b.get('id')}")
    else:
        print(f"FAILED TO GET BUCKET INFO: {resp.status_code} {resp.text}")

    # 2. List last 5 files in 'uploads'
    # Storage API for listing: POST /storage/v1/object/list/{bucket}
    list_url = f"{url}/storage/v1/object/list/uploads"
    res = httpx.post(list_url, headers=headers, json={"limit": 10, "sortBy": {"column": "created_at", "order": "desc"}})
    if res.status_code == 200:
        files = res.json()
        print("\n--- LAST 10 FILES IN 'uploads' ---")
        for f in files:
            print(f"- Name: {f['name']}, Size: {f.get('metadata', {}).get('size')}, Created: {f['created_at']}")
            # 3. Test Public Access to the last file
            test_url = f"{url}/storage/v1/object/public/uploads/{f['name']}"
            t_res = httpx.get(test_url)
            print(f"  Public Access Test: {t_res.status_code} ({'OK' if t_res.status_code == 200 else 'FAIL'})")
    else:
        print(f"FAILED TO LIST FILES: {res.status_code} {res.text}")

if __name__ == "__main__":
    diag()
