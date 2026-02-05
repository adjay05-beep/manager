from db import service_supabase

def audit_ids():
    CANDIDATES = [
        ("0014c533-ad54-42a3-b2cf-b5eb49eae54e", "정재훈"),
        ("7662acf7-89a4-49b7-97ed-ad94a4a548aa", "정재훈2"),
        ("020de13f-a84d-4441-8cd2-b03f4780dc19", "정재훈24")
    ]
    
    TARGET_ID = "2ae8b5e0-11e9-4ad5-bab6-5fc321a195a0" # Current 정재훈
    
    tables = ["channels", "chat_topic_members", "chat_messages", "handovers", "attendance_logs"]
    
    print(f"--- Data Audit for Candidate IDs ---")
    
    for uid, name in CANDIDATES:
        print(f"\nAudit for {name} ({uid}):")
        for t in tables:
            try:
                col = "owner_id" if t == "channels" else "user_id"
                res = service_supabase.table(t).select(col, count="exact").eq(col, uid).execute()
                print(f" - {t}: {res.count} rows")
            except Exception:
                print(f" - {t}: Error or 0")

if __name__ == "__main__":
    audit_ids()
