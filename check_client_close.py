from postgrest import SyncPostgrestClient
import os

try:
    url = os.environ.get("SUPABASE_URL", "http://localhost:3000") # Dummy
    client = SyncPostgrestClient(f"{url}/rest/v1", headers={}, schema="public")
    
    print("Methods:", dir(client))
    if hasattr(client, "close"):
        print("✅ Client has 'close' method.")
    else:
        print("⚠️ Client DOES NOT have 'close' method.")
        
    # Check internal client
    if hasattr(client, "session"):
        print("Internal session found.")
        if hasattr(client.session, "close"):
             print("✅ Internal session has 'close'.")

except Exception as e:
    print(f"Error: {e}")
