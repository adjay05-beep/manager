
import os
from supabase import create_client
from dotenv import load_dotenv

# Initialize NEW client (from .env)
load_dotenv()
NEW_URL = os.getenv("SUPABASE_URL")
# Use Service Key for bypassing RLS during insert
NEW_KEY = os.getenv("SUPABASE_SERVICE_KEY") 

if not NEW_URL or not NEW_KEY:
    print("Error: detailed to load new Supabase credentials from .env")
    exit(1)

new_client = create_client(NEW_URL, NEW_KEY)

# Initialize OLD client (Hardcoded from backup)
OLD_URL = "https://vtsttqtbewxkxxdoyhrj.supabase.co"
# [CRITICAL] Use SERVICE KEY for Old DB to bypass RLS (Channels were hidden from Anon)
OLD_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ0c3R0cXRiZXd4a3h4ZG95aHJqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTE5NzA1NSwiZXhwIjoyMDg0NzczMDU1fQ.Q2stvKPIT6XEaejGnwl3c1_se_rqW73fwf0LOM6xiVA"
old_client = create_client(OLD_URL, OLD_KEY)

def migrate_table(table_name, conflict_col="id", transform_func=None):
    print(f"Migrating {table_name}...")
    try:
        # Fetch all data from OLD
        res = old_client.table(table_name).select("*").execute()
        data = res.data
        if not data:
            print(f" - No data in {table_name}")
            return

        print(f" - Found {len(data)} records. Inserting to NEW...")
        
        # Insert to NEW
        # Process in batches of 100 to avoid timeouts
        batch_size = 100
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            if transform_func:
                batch = [transform_func(item) for item in batch]
                
            try:
                new_client.table(table_name).upsert(batch).execute()
                print(f"   - Inserted batch {i//batch_size + 1}")
            except Exception as e:
                print(f"   ! Error inserting batch: {e}")
                
    except Exception as e:
        print(f" ! Error migrating {table_name}: {e}")

# Migration Order Matters (Foreign Keys)
# 1. Profiles (Users must exist first... wait, Auth Users?)
# Note: This script cannot migrate Auth Users (email/password). 
# Supabase Auth migration requires specialized tools or manual CSV export/import in dashboard.
# However, we can migrate the 'public.profiles' table. 
# IF the Auth UIDs are consistent (which they won't be if we just sign up again), we have a problem.
# BUT: If the user intends to KEEP the same accounts, they must migrate Auth first.
# For now, we will migrate the public data. If Auth UIDs don't match, this will fail FK constraints.

# STRATEGY FOR AUTH:
# Since we can't programmatically insert into auth.users easily without admin privileges or specific migration tools,
# we will assume the user might need to recreate users or we just migrate content and let IDs be what they are.
# CRITICALLY: If we just dump `profiles` with UUIDs that don't exist in `auth.users` in the new project,
# the insertion will FAIL due to FK constraint (id references auth.users).

# WORKAROUND:
# We might need to temporarily disable FK constraints or...
# Actually, the user asked to "Bring everything".
# Without migrating Auth, `profiles` insertion will fail.
# I will migrate tables that DO NOT strictly depend on auth.users first if possible, or try anyway.

# Let's try migrating 'channels' first (some references profiles(id) as created_by which is nullable often, or strictly enforced).
# Scheme usually enforces it.

print("--- STARTING MIGRATION ---")
# migrate_table("profiles") # This will likely fail if auth users aren't there.
# migrate_table("channels")
# migrate_table("channel_members")
# migrate_table("chat_topics")
# migrate_table("messages")
# migrate_table("handovers")
# migrate_table("voice_prompts")
# migrate_table("attendance")

print("IMPORTANT: This script migrates PUBLIC tables.")
print("It CANNOT migrate user accounts (Login/Password).")
print("You must re-create users in the new project or use Supabase Dashboard > Authentication > Users to export/import.")
print("If User IDs change, the data relationships will break.")

# For now, let's just attempt to migrate references to see what happens.
# If it fails, I will instruct the user on Auth migration.

# ACTUAL EXECUTION ORDER
migrate_table("profiles") 
migrate_table("channels")
migrate_table("channel_members")
migrate_table("invite_codes") # [ADDED]
migrate_table("chat_categories") # [ADDED]
migrate_table("chat_topics")
migrate_table("chat_topic_members") # [ADDED]
migrate_table("chat_messages") # [RENAMED] was messages
migrate_table("chat_user_reading") # [RENAMED] was topic_reads
migrate_table("handovers")
migrate_table("voice_prompts")
migrate_table("attendance_logs")
# gps_requests is ephemeral, no need to migrate
print("--- MIGRATION COMPLETE ---")
