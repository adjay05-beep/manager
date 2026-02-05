from db import service_supabase

def grant_juwal_access():
    JUWAL_ID = "020de13f-a84d-4441-8cd2-b03f4780dc19" # 정재훈24
    CHANNEL_ID = 1 # 주월 (사당점)
    
    print(f"--- Granting Channel Access to {JUWAL_ID} ---")
    
    try:
        # Add to Channel 1
        res = service_supabase.table("channel_members").upsert({
            "channel_id": CHANNEL_ID,
            "user_id": JUWAL_ID,
            "role": "member"
        }).execute()
        print(f" ✓ Granted 'member' role in Channel {CHANNEL_ID}")
        
        # Verify
        res_v = service_supabase.table("channel_members").select("*").eq("user_id", JUWAL_ID).execute()
        print(f" Verification: {len(res_v.data)} memberships found for this user.")
        
    except Exception as e:
        print(f" Error: {e}")

if __name__ == "__main__":
    grant_juwal_access()
