import asyncio
import os
from services.payroll_service import payroll_service

async def main():
    print("🧪 Testing PayrollService...")
    
    # We need a valid channel ID. Let's try to fetch one or use 1.
    channel_id = 1
    user_id = "00000000-0000-0000-0000-000000000001" # Test user
    year = 2026
    month = 1
    
    try:
        print(f"   Calculating for Channel {channel_id}, {year}-{month}...")
        res = await payroll_service.calculate_payroll(user_id, channel_id, year, month)
        
        print(f"✅ Calculation Success!")
        print(f"   Summary: {res['summary']}")
        print(f"   Policies Count: {len(res['employees'])}")
        if res['employees']:
            print(f"   Sample Employee: {res['employees'][0]['name']}")
            
    except Exception as e:
        print(f"❌ Verification Failed: {e}")
        # It's possible channel 1 doesn't exist or RLS issues, but we want to see if code crashes.

if __name__ == "__main__":
    asyncio.run(main())
