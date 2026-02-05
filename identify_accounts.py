from db import service_supabase

def identify_juwal():
    print("--- Identifying Accounts for juwal24@naver.com ---")
    
    # We suspect '정재훈24' (020de13f-a84d-4441-8cd2-b03f4780dc19) is the target.
    # Let's check its data.
    TARGET_JUWAL = "020de13f-a84d-4441-8cd2-b03f4780dc19"
    LEGACY_JUWAL = "7662acf7-89a4-49b7-97ed-ad94a4a548aa" # '정재훈2'
    
    ADJAY_CURRENT = "2ae8b5e0-11e9-4ad5-bab6-5fc321a195a0"
    
    tables = ["chat_messages", "handovers", "chat_topic_members"]
    
    results = {}
    for uid in [TARGET_JUWAL, LEGACY_JUWAL, ADJAY_CURRENT]:
        results[uid] = {}
        for t in tables:
            col = "user_id"
            try:
                res = service_supabase.table(t).select(col, count="exact").eq(col, uid).execute()
                results[uid][t] = res.count
            except:
                results[uid][t] = 0
                
    print("\nCurrent Data State:")
    print(f" - 정재훈24 (Potential Target): {results[TARGET_JUWAL]}")
    print(f" - 정재훈2 (Legacy source): {results[LEGACY_JUWAL]}")
    print(f" - 정재훈 (Current adjay): {results[ADJAY_CURRENT]}")

if __name__ == "__main__":
    identify_juwal()
