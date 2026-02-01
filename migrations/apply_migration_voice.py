import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from db import supabase, service_supabase
    from postgrest import SyncPostgrestClient
except ImportError:
    print("Error: Could not import 'db'. Make sure you are running this from the project root.")
    sys.exit(1)

def apply_sql(sql_path):
    print(f"Applying migration from: {sql_path}")
    try:
        with open(sql_path, "r", encoding="utf-8") as f:
            sql = f.read()
        
        # Use postgres RPC if available, or just execute via client if raw query supported?
        # Supabase-py client doesn't support raw SQL directly on client.
        # We generally use a stored procedure/RPC 'exec_sql' if we made one.
        # IF NOT, we might need direct connection or use a workaround.
        # Assuming 'exec_sql' exists from previous migrations or we just use RLS bypass if possible.
        # Check if we have an RPC for this.
        
        # ACTUALLY, previous migrations might have failed if they relied on non-existent RPC.
        # Let's try to use the `service_supabase` client which is admin.
        # Does it have an `rpc` method? Yes.
        
        # If 'exec_sql' function exists in DB:
        try:
            res = service_supabase.rpc("exec_sql", {"sql_query": sql}).execute()
            print("Migration applied via RPC 'exec_sql'.")
            return
        except Exception as rpc_err:
            print(f"RPC 'exec_sql' failed or not found: {rpc_err}")
            
        print("Fallback: Manual SQL execution required if no RPC.")
        print("However, since we are in a python environment with service key, we can try using it if library supports.")
        # But `supabase-py` doesn't do raw SQL without RPC.
        
    except Exception as e:
        print(f"Migration Failed: {e}")

if __name__ == "__main__":
    apply_sql("d:\\Project A\\migration_voice_memos.sql")
