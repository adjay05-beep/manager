from db import supabase

try:
    res = supabase.table("chat_topics").select("id, name").execute()
    print(f"Count: {len(res.data)}")
    for r in res.data:
        print(f"- {r['name']} ({r['id']})")
except Exception as e:
    print(f"Error: {e}")
