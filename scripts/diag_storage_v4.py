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
    # 1. List files with correct prefix
    list_url = f"{url}/storage/v1/object/list/uploads"
    print(f"Listing files in 'uploads' via: {list_url}")
    try:
        res = httpx.post(list_url, headers=headers, json={"prefix": ""})
        if res.status_code == 200:
            files = res.json()
            print(f"Found {len(files)} files.")
            for f in files:
                print(f"- {f['name']} ({f.get('metadata', {}).get('size')} bytes)")
        else:
            print(f"LIST FAILED: {res.status_code} {res.text}")
    except Exception as e:
        print(f"LIST ERROR: {e}")

    # 2. Try an upload with NO Content-Type header to see if it makes a difference
    try:
        print("\nTesting manual upload without Content-Type...")
        test_fname = "diag_test_manual.txt"
        test_content = b"hello supabase"
        up_url = f"{url}/storage/v1/object/uploads/{test_fname}"
        up_res = httpx.post(up_url, headers=headers, content=test_content)
        print(f"Upload Status: {up_res.status_code}")
        print(f"Upload Response: {up_res.text}")
    except Exception as e:
        print(f"UPLOAD ERROR: {e}")

if __name__ == "__main__":
    diag()
