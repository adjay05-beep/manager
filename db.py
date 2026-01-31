import os
import mimetypes
from datetime import datetime
from dotenv import load_dotenv
import httpx
from gotrue import SyncGoTrueClient
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
        # Shared client for efficiency (latency reduction)
        self._http_client = httpx.Client(headers=self.headers, timeout=60.0)
        
        # Initialize Auth
        self.auth = SyncGoTrueClient(
            url=f"{url}/auth/v1",
            headers=self.headers,
            storage_key="supabase.auth.token",
            http_client=self._http_client
        )
        
        # Initialize Database (PostgREST)
        self.rest = SyncPostgrestClient(
            f"{url}/rest/v1",
            headers=self.headers,
            schema="public",
            timeout=60
        )
        
        # Manual Storage Client using httpx (Stable in all environments)
        self.storage = ManualStorageManager(f"{url}/storage/v1", self.headers, self._http_client)

    def check_connection(self):
        """Verify and refresh the HTTP client if it's dead/disconnected."""
        try:
            # Simple health check call to Supabase Auth
            resp = self._http_client.get(f"{self.url}/auth/v1/health")
            if resp.status_code >= 500:
                raise httpx.HTTPError("Server side error")
        except (httpx.HTTPError, Exception) as e:
            log_info(f"Supabase Client: Connectivity issue detected ({e}). Re-initializing...")
            try:
                self._http_client.close()
            except Exception as close_err:
                log_info(f"Client close warning: {close_err}")
            self._http_client = httpx.Client(headers=self.headers, timeout=60.0)
            self.auth.http_client = self._http_client
            self.rest.session = self._http_client # SyncPostgrestClient uses .session
            self.storage.client = self._http_client
            log_info("Supabase Client: Re-initialized.")

    def __del__(self):
        """Cleanup HTTP client on garbage collection."""
        try:
            if hasattr(self, '_http_client') and self._http_client:
                self._http_client.close()
        except Exception:
            pass

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

class ManualStorageManager:
    def __init__(self, url, headers, client=None):
        self.url = url
        self.headers = headers
        self.client = client or httpx.Client(headers=headers)
    def from_(self, bucket):
        return ManualBucket(self.url, self.headers, bucket, self.client)

class ManualBucket:
    def __init__(self, url, headers, bucket, client=None):
        self.url = f"{url}/object/{bucket}"
        self.headers = headers
        self.client = client or httpx.Client(headers=headers)
    def upload(self, path, content, file_options=None, **kwargs):
        # [CRITICAL FIX] Avoid sending 'Content-Type: application/json' for binary files
        upload_headers = self.headers.copy()
        
        # Handle Options (Support file_options from SDK style calls)
        if file_options and isinstance(file_options, dict):
            # Key can be 'content-type' or 'contentType'
            ctype = file_options.get("content-type") or file_options.get("contentType")
            if ctype:
                upload_headers["Content-Type"] = ctype
        
        # Determine MIME Type if not set
        if "Content-Type" not in upload_headers:
            mime_type, _ = mimetypes.guess_type(path)
            if mime_type:
                upload_headers["Content-Type"] = mime_type
            elif "Content-Type" in upload_headers:
                # Drop if we can't guess but it's binary
                del upload_headers["Content-Type"]
            
        resp = self.client.post(f"{self.url}/{path}", headers=upload_headers, content=content)
        if resp.status_code not in [200, 201]:
            print(f"STORAGE ERROR: {resp.status_code} {resp.text}")
        resp.raise_for_status()
        return resp.json()

    def create_upload_url(self, path):
        # Fallback for simple POST (Often fails with auth)
        return f"{self.url}/{path}"

    def create_signed_upload_url(self, path, expires_in=120):
        import urllib.parse
        safe_path = urllib.parse.quote(path)
        
        parts = self.url.split("/object/")
        base_storage_url = parts[0]
        # Current bucket from instance
        bucket = self.url.split("/")[-1]
        
        headers = self.headers.copy()
        headers["Content-Type"] = "application/json"
        
        # [LATENCY OPTIMIZATION] Most direct path first
        # Endpoints: 1. standard, 2. legacy
        endpoints = [
            f"{base_storage_url}/object/upload/sign/{bucket}/{safe_path}",
            f"{base_storage_url}/object/{bucket}/{safe_path}/sign"
        ]
        
        last_error = ""
        for endpoint in endpoints:
            try:
                resp = self.client.post(endpoint, headers=headers, json={"expiresIn": expires_in})
                if resp.status_code == 200:
                    data = resp.json()
                    # [FIX] Handle all key variations
                    s_url = data.get("signedURL") or data.get("signedUrl") or data.get("url")
                    
                    if s_url and s_url.startswith("/"):
                        s_url = f"{base_storage_url}{s_url}"
                    return s_url
                last_error = f"{resp.status_code}: {resp.text}"
            except Exception as e:
                last_error = str(e)
                continue
        
        msg = f"SIGNED URL ERROR: Failed for path '{path}'. Last Error: {last_error}"
        print(msg)
        raise Exception(msg)

    def list(self, path=None):
        # Construct List Endpoint: .../object/list/{bucket}
        # self.url is .../object/{bucket}
        parts = self.url.split("/object/")
        base_storage_url = parts[0]
        bucket = self.url.split("/")[-1]
        
        list_url = f"{base_storage_url}/object/list/{bucket}"
        
        headers = self.headers.copy()
        headers["Content-Type"] = "application/json"
        
        body = {
            "prefix": path if path else "",
            "limit": 10,
            "offset": 0,
            "sortBy": {"column": "name", "order": "asc"}
        }
        
        try:
            resp = self.client.post(list_url, headers=headers, json=body)
            # Supabase returns 200 for list even if empty
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"List Bucket Error: {e}")
            raise e

    def create_signed_url(self, path, expires_in=60):
        # [FIX] Implement missing method matching supabase-py interface
        parts = self.url.split("/object/")
        base_storage_url = parts[0]
        bucket = self.url.split("/")[-1]
        
        # Endpoint: POST /object/sign/{bucket}/{path}
        # Path should be part of the URL path
        sign_url = f"{base_storage_url}/object/sign/{bucket}/{path}"
        
        headers = self.headers.copy()
        headers["Content-Type"] = "application/json"
        
        try:
            resp = self.client.post(sign_url, headers=headers, json={"expiresIn": expires_in})
            resp.raise_for_status()
            data = resp.json()
            
            # [FIX] Check all possible keys (API variations)
            s_url = data.get("signedURL") or data.get("signedUrl") or data.get("url")
            
            if s_url and s_url.startswith("/"):
                 s_url = f"{base_storage_url}{s_url}"
            
            if not s_url:
                 print(f"Signed URL Warning: No URL in response: {data}")
                 
            return {"signedURL": s_url}
        except Exception as e:
            print(f"Manual Signed URL Error: {e}")
            raise e

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
service_key = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("WARNING: SUPABASE_URL or SUPABASE_KEY not found in .env")
    supabase = None
else:
    supabase = SupabaseClient(url, key)

# [DIAGNOSTIC] Global log buffer for UI debugging
app_logs = []
def log_info(msg):
    time_str = datetime.now().strftime("%H:%M:%S")
    formatted = f"[{time_str}] {msg}"
    app_logs.append(formatted)
    if len(app_logs) > 50: app_logs.pop(0)
    print(formatted)

# Service role client for admin operations (bypasses RLS)
try:
    if service_key:
        service_supabase = SupabaseClient(url, service_key)
        has_service_key = True
        log_info("Service Supabase Connection: Established")
    else:
        print("INFO: SUPABASE_SERVICE_KEY not set. Using anon key for all operations.")
        service_supabase = supabase
        has_service_key = False
        log_info("Service Supabase Connection: FAILED (No Key)")
except Exception as e:
    log_info(f"Service Supabase Connection: CRITICAL ERROR - {e}")
    service_supabase = supabase
    has_service_key = False


