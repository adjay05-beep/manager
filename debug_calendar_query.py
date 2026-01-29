
import asyncio
from db import service_supabase

async def test():
    # Arbitrary UUID for testing syntax
    test_uid = "00000000-0000-0000-0000-000000000000"
    
    print("--- Testing Python List Object ---")
    try:
        # Pass list directly, see if SDK handles it
        res = service_supabase.table("calendar_events").select("id").cs("participant_ids", [test_uid]).execute()
        print(f"List Object Success. Data: {res.data}")
    except Exception as e:
        print(f"List Object Failed: {e}")

    print("\n--- Testing ILIKE (Fallback) ---")
    try:
        # Cast to text using implicit casting if possible, or just fail
        # Note: ilike on jsonb is usually invalid in postgres unless cast
        res = service_supabase.table("calendar_events").select("id").ilike("participant_ids", f"%{test_uid}%").execute()
        print(f"Ilike Success. Data: {res.data}")
    except Exception as e:
        print(f"Ilike Failed: {e}")


if __name__ == "__main__":
    asyncio.run(test())
