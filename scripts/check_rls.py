import os
import asyncio
from db import service_supabase

async def check_rls():
    print("Checking Row Level Security (RLS) Status...")
    
    # Query pg_class and pg_policy (requires admin/rpc usually, but let's try direct inspection if possible or infer)
    # Actually, we can just try to access tables with a non-service key (anon/authenticated) vs service key.
    # But checking metadata is better.
    
    sql = """
    SELECT relname, relrowsecurity 
    FROM pg_class 
    WHERE relnamespace = 'public'::regnamespace 
    AND relkind = 'r';
    """
    
    try:
        # Use RPC if available
        res = service_supabase.rpc("exec_sql", {"sql_query": sql}).execute()
        if res.data:
            print(f"{'Table':<30} | {'RLS Enabled':<10}")
            print("-" * 45)
            for row in res.data:
                print(f"{row['relname']:<30} | {row['relrowsecurity']}")
        else:
            print("No data returned from RLS check.")
            
    except Exception as e:
        print(f"Failed to check RLS via RPC: {e}")
        # Fallback: Try to query tables directly? No, that doesn't tell us about RLS config.
        print("Please ensure 'exec_sql' RPC is available or check console.")

if __name__ == "__main__":
    asyncio.run(check_rls())
