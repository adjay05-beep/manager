import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

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
        
        try:
            # Try splitting by statement if big, but RPC often handles blocks.
            res = service_supabase.rpc("exec_sql", {"sql_query": sql}).execute()
            print("Migration applied via RPC 'exec_sql'.")
            return
        except Exception as rpc_err:
            print(f"RPC 'exec_sql' failed: {rpc_err}")
            
    except Exception as e:
        print(f"Migration Failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python apply_migration_generic.py <path_to_sql>")
        sys.exit(1)
    
    apply_sql(sys.argv[1])
