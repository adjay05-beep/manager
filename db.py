import os
from dotenv import load_dotenv
from supabase_auth import SyncGoTrueClient
from postgrest import SyncPostgrestClient
# from realtime import SyncRealtimeClient # Realtime setup can be complex, adding if needed later

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

    # Mimic the standard supabase-py interface
    def table(self, table_name: str):
        return self.rest.from_(table_name)
    
    def from_(self, table_name: str):
        return self.rest.from_(table_name)

    def rpc(self, fn: str, params: dict = None):
        return self.rest.rpc(fn, params)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("WARNING: SUPABASE_URL or SUPABASE_KEY not found in .env")
    supabase = None
else:
    supabase = SupabaseClient(url, key)
