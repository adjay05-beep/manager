from db import service_supabase

def analyze_messages():
    uid = "2ae8b5e0-11e9-4ad5-bab6-5fc321a195a0"
    print(f"--- Message History Analysis for {uid} ---")
    
    try:
        res = service_supabase.table("chat_messages").select("id, created_at, content").eq("user_id", uid).order("created_at").execute()
        msgs = res.data
        print(f"Total messages: {len(msgs)}")
        
        if not msgs: return

        # Show blocks
        print("\nEarliest 5 messages:")
        for m in msgs[:5]:
             print(f" - [{m['created_at']}] {m['id']} : {m['content'][:20]}...")
             
        print("\nLatest 5 messages:")
        for m in msgs[-5:]:
             print(f" - [{m['created_at']}] {m['id']} : {m['content'][:20]}...")
             
        # Find potential break points (large time gaps?)
        # Or just use the counts we know.
        # Mumbai (0014...) : 4 messages
        # Seoul-old (7662...) : 73 messages
        # Current (2ae8...) : 64 messages
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_messages()
