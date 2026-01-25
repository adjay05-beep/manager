import os
import mimetypes
from dotenv import load_dotenv
from supabase_auth import SyncGoTrueClient
from postgrest import SyncPostgrestClient
try:
    from realtime import AsyncRealtimeClient
except ImportError:
    AsyncRealtimeClient = None

load_dotenv()

class SupabaseClient:
    def __init__(self, url: str, key: str):
        self.url = url
        self.key = key
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        
        # Initialize Auth
        self.auth = SyncGoTrueClient(
            url=f"{url}/auth/v1",
            headers=self.headers,
            storage_key="supabase.auth.token"
        )
        
        # Initialize Database (PostgREST)
        self.rest = SyncPostgrestClient(
            f"{url}/rest/v1", 
            headers=self.headers, 
            schema="public"
        )
        
        # Manual Storage Client using httpx (Stable in all environments)
        self.storage = ManualStorageManager(f"{url}/storage/v1", self.headers)

    def get_realtime_client(self):
        if not AsyncRealtimeClient:
            print("ERROR: AsyncRealtimeClient not available. Please check dependencies.")
            return None
        socket_url = f"{self.url.replace('https', 'wss')}/realtime/v1"
        return AsyncRealtimeClient(socket_url, self.key)

    # Mimic the standard supabase-py interface
    def table(self, table_name: str):
        return self.rest.from_(table_name)
    
    def from_(self, table_name: str):
        return self.rest.from_(table_name)

    def rpc(self, fn: str, params: dict = None):
        return self.rest.rpc(fn, params)

    def get_upload_headers(self):
        # Essential headers for Supabase Storage without Content-Type
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}"
        }

import httpx
class ManualStorageManager:
    def __init__(self, url, headers):
        self.url = url
        self.headers = headers
    def from_(self, bucket):
        return ManualBucket(self.url, self.headers, bucket)

class ManualBucket:
    def __init__(self, url, headers, bucket):
        self.url = f"{url}/object/{bucket}"
        self.headers = headers
    def upload(self, path, content):
        # [CRITICAL FIX] Avoid sending 'Content-Type: application/json' for binary files
        upload_headers = self.headers.copy()
        
        # Determine MIME Type
        mime_type, _ = mimetypes.guess_type(path)
        if mime_type:
            upload_headers["Content-Type"] = mime_type
        elif "Content-Type" in upload_headers:
            # Drop if we can't guess but it's binary
            del upload_headers["Content-Type"]
            
        resp = httpx.post(f"{self.url}/{path}", headers=upload_headers, content=content)
        if resp.status_code not in [200, 201]:
            print(f"STORAGE ERROR: {resp.status_code} {resp.text}")
        resp.raise_for_status()
        return resp.json()

    def create_upload_url(self, path):
        # Fallback for simple POST (Often fails with auth)
        return f"{self.url}/{path}"

    def create_signed_upload_url(self, path, expires_in=120):
        # [OPTIMIZED] Prioritize 'uploads' bucket to avoid unnecessary requests.
        import urllib.parse
        safe_path = urllib.parse.quote(path)
        
        parts = self.url.split("/object/")
        base_storage_url = parts[0]
        # Default fallback if parsing fails
        original_bucket = parts[1] if len(parts) > 1 else "uploads"
        
        headers = self.headers.copy()
        headers["Content-Type"] = "application/json"
        
        # [CHANGE] Strict priority: Check 'uploads' first, then others only if needed.
        # This drastically reduces latency for the happy path.
        buckets_to_try = ["uploads", original_bucket]
        buckets_to_try = list(dict.fromkeys(buckets_to_try)) # Dedup
        
        last_error = ""
        for bucket in buckets_to_try:
            # 1. Primary Syntax (Standard Supabase)
            endpoint = f"{base_storage_url}/object/upload/sign/{bucket}/{safe_path}"
            try:
                resp = httpx.post(endpoint, headers=headers, json={"expiresIn": expires_in})
                if resp.status_code == 200:
                    data = resp.json()
                    s_url = data.get("url") or data.get("signedUrl")
                    if s_url and s_url.startswith("/"):
                        s_url = f"{base_storage_url}{s_url}"
                    return s_url
                
                # 2. Fallback Syntax (Older Supabase)
                fb_endpoint = f"{base_storage_url}/object/{bucket}/{safe_path}/sign"
                resp = httpx.post(fb_endpoint, headers=headers, json={"expiresIn": expires_in})
                if resp.status_code == 200:
                    data = resp.json()
                    s_url = data.get("url") or data.get("signedUrl")
                    if s_url and s_url.startswith("/"):
                        s_url = f"{base_storage_url}{s_url}"
                    return s_url
                
                last_error = f"Bucket '{bucket}': {resp.status_code} {resp.text}"
            except Exception as e:
                last_error = str(e)
                continue
        
        msg = f"SIGNED URL ERROR: Failed for path '{path}'. Tried {buckets_to_try}. Last Error: {last_error}"
        print(msg)
        raise Exception(msg)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("WARNING: SUPABASE_URL or SUPABASE_KEY not found in .env")
    supabase = None
else:
    supabase = SupabaseClient(url, key)
