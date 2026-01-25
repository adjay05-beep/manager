import os
import httpx
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def test_upload():
    print(f"Project URL: {url}")
    test_file = "test_upload.txt"
    with open(test_file, "w") as f:
        f.write("test content")
    
    try:
        with open(test_file, "rb") as f:
            content = f.read()
            print("Attempting upload to 'uploads' bucket...")
            # Try both ways: supabase-py and direct httpx
            res = supabase.storage.from_("uploads").upload("test_diag.txt", content, {"upsert": "true"})
            print(f"SDK Upload Success: {res}")
            
            public_url = supabase.storage.from_("uploads").get_public_url("test_diag.txt")
            print(f"Public URL: {public_url}")
            
            # Check if public URL is actually reachable
            r = httpx.get(public_url)
            print(f"Public Access Status: {r.status_code}")
            if r.status_code != 200:
                print(f"Error accessing public URL: {r.text}")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_upload()
