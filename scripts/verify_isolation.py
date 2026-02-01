import asyncio
from db import service_supabase
import uuid

# Configuration
TEST_USER_A = "11111111-1111-1111-1111-111111111111"
TEST_USER_B = "22222222-2222-2222-2222-222222222222"
CHANNEL_A = 1001
CHANNEL_B = 1002

async def verify_isolation():
    print("Starting Data Isolation Verification...")
    
    # 1. Setup Test Channels & Users
    # Note: We use service_role to setup, then simulate restricted access if possible.
    # Supabase-py client is initialized with SERVICE_KEY, so it sees everything by default.
    # To test RLS, we need to create a client with an AUTH token for User A/B.
    # OR, we define policies that block even Service Key? No, Service Key bypasses RLS.
    
    # LIMITATION: We cannot easily spawn a client with fake user token without signing a JWT.
    # However, we can use `auth.uid()` in policies.
    # We can try to use `rpc('set_claim', ...)` or just inspect the policies text.
    
    # For this verification, we will:
    # A. Check if Policies exist on tables.
    # B. trusting the schema scan.
    
    tables = [
        "channels", "channel_members", "chat_categories", "chat_topics", "chat_messages", 
        "calendar_events", "labor_contracts", "voice_memos"
    ]
    
    print(f"\nScanning RLS Policies on {len(tables)} critical tables:")
    print("-" * 60)
    print(f"{'Table':<20} | {'RLS':<6} | {'Policies'}")
    print("-" * 60)
    
    rls_active_count = 0
    
    for tbl in tables:
        # Check if RLS is enabled
        
        sql = f"""
        SELECT 
            c.relrowsecurity,
            count(p.polname) as policy_count
        FROM pg_class c
        LEFT JOIN pg_policy p ON p.polrelid = c.oid
        WHERE c.relname = '{tbl}'
        GROUP BY c.relrowsecurity;
        """
        try:
            r = service_supabase.rpc("exec_sql", {"sql_query": sql}).execute()
            if r.data:
                row = r.data[0]
                is_enabled = row['relrowsecurity']
                count = row['policy_count']
                status = "ON" if is_enabled else "OFF"
                
                print(f"{tbl:<20} | {status:<6} | {count} policies")
                if is_enabled: rls_active_count += 1
            else:
                 print(f"{tbl:<20} | ???    | Could not read metadata")
        except Exception as e:
            print(f"{tbl:<20} | ERROR  | {e}")

    print("-" * 60)
    if rls_active_count == len(tables):
        print("SUCCESS: All critical tables have RLS enabled.")
    else:
        print(f"WARNING: Only {rls_active_count}/{len(tables)} tables have RLS enabled.")

if __name__ == "__main__":
    asyncio.run(verify_isolation())
