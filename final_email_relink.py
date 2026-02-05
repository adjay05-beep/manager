from db import service_supabase

def final_correct_relink():
    print("--- Final Email-Based Relinking ---")
    
    # 1. MAPPING Definition
    # Identity A: adjay@naver.com / 정재훈
    ADJAY_STREAMS = [
        "0014c533-ad54-42a3-b2cf-b5eb49eae54e", # Legacy 정재훈 (4 msgs)
        "ce89c5a4-7f97-4900-a89e-18a713c7968f"  # Older candidate
    ]
    ADJAY_TARGET = "2ae8b5e0-11e9-4ad5-bab6-5fc321a195a0" # Current '정재훈'
    
    # Identity B: juwal24@naver.com / 정재훈24 (Name changed from 정재훈2)
    JUWAL_STREAMS = [
        "7662acf7-89a4-49b7-97ed-ad94a4a548aa"  # Legacy '정재훈2' (73 msgs)
    ]
    JUWAL_TARGET = "020de13f-a84d-4441-8cd2-b03f4780dc19" # Current '정재훈24'

    tables_to_update = [
        ("channels", "owner_id"),
        ("channel_members", "user_id"),
        ("chat_messages", "user_id"),
        ("chat_topics", "created_by"),
        ("chat_topic_members", "user_id"),
        ("chat_user_reading", "user_id"),
        ("handovers", "user_id"),
        ("voice_prompts", "user_id"),
        ("invite_codes", "created_by"),
        ("attendance_logs", "user_id")
    ]

    # Relink Helper
    def run_relink(sources, target):
        print(f"\n>> Relinking to target: {target}")
        for old_id in sources:
            print(f"   From source: {old_id}")
            for table, col in tables_to_update:
                try:
                    res = service_supabase.table(table).update({col: target}).eq(col, old_id).execute()
                    if len(res.data) > 0:
                        print(f"     ✓ {table}.{col}: {len(res.data)} rows updated")
                except Exception as e:
                    print(f"     ! Error on {table}: {e}")
            
            # Delete legacy profile after migration
            try:
                service_supabase.table("profiles").delete().eq("id", old_id).execute()
                print(f"   ✓ Legacy profile {old_id} deleted.")
            except:
                pass

    # Execute
    run_relink(ADJAY_STREAMS, ADJAY_TARGET)
    run_relink(JUWAL_STREAMS, JUWAL_TARGET)

    print("\n--- FINAL RELINKING COMPLETE ---")

if __name__ == "__main__":
    final_correct_relink()
