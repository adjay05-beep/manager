from db import supabase
import uuid

def verify_chat_permissions():
    try:
        print("1. Checking for Demo User...")
        res = supabase.table("profiles").select("*").eq("id", "00000000-0000-0000-0000-000000000001").execute()
        if res.data:
            print("   ✅ Demo User 'The Manager' found!")
        else:
            print("   ❌ Demo User NOT found. The SQL script might not have inserted it.")
            return

        print("\n2. Trying to insert a test message...")
        topics = supabase.table("chat_topics").select("id").limit(1).execute()
        if not topics.data:
            print("   ❌ No topics found. Cannot test message.")
            return
        
        topic_id = topics.data[0]['id']
        
        # CORRECTED PAYLOAD (No user_name)
        payload = {
            "topic_id": topic_id,
            "content": "Server-side connection test message 🚀",
            "user_id": "00000000-0000-0000-0000-000000000001"
        }
        
        msg_res = supabase.table("chat_messages").insert(payload).execute()
        print(f"   ✅ Message inserted successfully! ID: {msg_res.data[0]['id']}")
        
        print("\n🎉 SYSTEM READY FOR CHAT!")

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        print("The SQL fix might not have applied correctly (RLS policy issue?).")

if __name__ == "__main__":
    verify_chat_permissions()
