from db import supabase
import json

try:
    print(f"Fetching specific columns to debug...")
    
    # Fetch all columns
    response = supabase.table("chat_topics").select("*").execute()
    
    if response.data:
        first_item = response.data[0]
        print(f"First Item Keys: {list(first_item.keys())}")
        print(f"First Item Data: {json.dumps(first_item, indent=2, ensure_ascii=False)}")
    else:
        print("No data found in 'chat_topics'.")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
