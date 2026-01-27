import asyncio
import os
from db import service_supabase

async def test_null_constraint():
    print("--- Verifying 'labor_contracts' NULL user_id Constraint ---")
    if not service_supabase:
        print("ERROR: Service Supabase Client not available (check .env SERVICE_KEY)")
        return

    try:
        # Attempt to insert a minimal record with NULL user_id
        # We need valid channel_id. Let's assume 1 or fetch one.
        # Fetch a channel
        c_res = service_supabase.table("channels").select("id").limit(1).execute()
        if not c_res.data:
            print("No channels found to test.")
            return
        
        cid = c_res.data[0]['id']
        print(f"Testing with Channel ID: {cid}")

        # Data for Offline Employee (Ghost)
        data = {
            "channel_id": cid,
            "user_id": None, # EXPLICIT NULL
            "employee_name": "_TEST_GHOST_EMPLOYEE_",
            "contract_start_date": "2026-01-01",
            "employee_type": "part",
            "wage_type": "hourly",
            "hourly_wage": 10000
        }

        print(f"Attempting Insert: {data}")
        res = service_supabase.table("labor_contracts").insert(data).execute()
        print("✅ INSERT SUCCESS! (Table allows NULL user_id)")
        print("Result:", res.data)

        # Cleanup
        new_id = res.data[0]['id']
        print(f"Cleaning up ID: {new_id}")
        service_supabase.table("labor_contracts").delete().eq("id", new_id).execute()
        print("Cleanup Complete.")

    except Exception as e:
        print("❌ INSERT FAILED!")
        print(f"Error: {e}")
        if "null value in column" in str(e) or "violates not-null constraint" in str(e):
             print("DIAGNOSIS: 'user_id' column has NOT NULL constraint. Schema change required.")
        elif "recursion" in str(e):
             print("DIAGNOSIS: Infinite Recursion STILL persists even for Admin? (Unlikely for Service Role)")
        else:
             print("DIAGNOSIS: Other error.")

if __name__ == "__main__":
    asyncio.run(test_null_constraint())
