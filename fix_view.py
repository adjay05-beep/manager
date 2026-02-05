from db import service_supabase
import httpx
import os

def update_view():
    print("--- Updating unread_counts_view ---")
    
    sql = """
    create or replace view public.unread_counts_view as
    select 
        cm.topic_id, 
        cm.user_id, 
        count(m.id) as unread_count
    from public.chat_topic_members cm
    join public.chat_messages m on m.topic_id = cm.topic_id
    left join public.chat_user_reading cur on cur.topic_id = cm.topic_id and cur.user_id = cm.user_id
    where m.user_id <> cm.user_id
      and m.created_at > coalesce(cur.last_read_at, '1970-01-01'::timestamp with time zone)
    group by cm.topic_id, cm.user_id;

    NOTIFY pgrst, 'reload config';
    """
    
    # Since we can't run raw SQL via the SDK easily without a pre-defined RPC,
    # and the MCP is read-only, I'll advise the user OR try to find a way.
    # Actually, many Supabase projects have a 'exec_sql' RPC for migrations.
    # Let's try to see if it exists.
    
    try:
        service_supabase.rpc("exec_sql", {"sql": sql}).execute()
        print("✓ View updated successfully via RPC.")
    except Exception as e:
        print(f"! Failed to update view via RPC: {e}")
        print("\nPlease run the following SQL in your Supabase Dashboard SQL Editor:")
        print(sql)

if __name__ == "__main__":
    update_view()
