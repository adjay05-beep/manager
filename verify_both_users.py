from db import service_supabase

def verify_both():
    # Identity A: adjay@naver.com / 정재훈
    ADJAY_TARGET = "2ae8b5e0-11e9-4ad5-bab6-5fc321a195a0"
    
    # Identity B: juwal24@naver.com / 정재훈24
    JUWAL_TARGET = "020de13f-a84d-4441-8cd2-b03f4780dc19"

    targets = [
        (ADJAY_TARGET, "adjay@naver.com (정재훈)"),
        (JUWAL_TARGET, "juwal24@naver.com (정재훈24)")
    ]
    
    tables = ["chat_messages", "handovers", "chat_topic_members"]
    
    print("--- Final Email-Based Verification ---")
    for uid, email in targets:
        print(f"\nAccount: {email} ({uid})")
        for t in tables:
            col = "user_id"
            try:
                res = service_supabase.table(t).select(col, count="exact").eq(col, uid).execute()
                print(f" - {t}: {res.count} rows")
            except:
                print(f" - {t}: 0 rows")

if __name__ == "__main__":
    verify_both()
