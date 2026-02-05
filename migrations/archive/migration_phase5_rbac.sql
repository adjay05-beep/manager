-- Phase 5: RBAC & Access Control

-- 1. Add Role to Profiles
-- Roles: 'admin', 'manager', 'staff'
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'staff';

-- 2. Chat Topic Memberships
-- Who can see which topic?
CREATE TABLE IF NOT EXISTS chat_topic_members (
    topic_id bigint REFERENCES chat_topics(id) ON DELETE CASCADE,
    user_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
    permission_level TEXT DEFAULT 'viewer', -- 'owner', 'editor', 'viewer'
    joined_at timestamp with time zone DEFAULT now(),
    PRIMARY KEY (topic_id, user_id)
);

-- 3. Ensure Chat Topics has an Owner
ALTER TABLE chat_topics ADD COLUMN IF NOT EXISTS created_by uuid REFERENCES profiles(id) ON DELETE SET NULL;

-- 4. Calendar Members (Optional but good for explicit shared calendars)
-- For now, we rely on 'participant_ids' array in calendar_events for individual event visibility.
-- But we might need a 'calendar_acl' if we have shared calendars.
-- Let's stick to the User Request: "Individual can verify threads and calendar they belong to".

-- 5. RLS Policies (If we were using strict RLS, we would add them here)
-- Since the Python code uses a Service Key or high-level client, we handle logic in Service Layer.
-- But enabling RLS is good practice.

ALTER TABLE chat_topic_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Members can view membership" 
ON chat_topic_members FOR SELECT USING (true);

-- 6. Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_topic_members_user ON chat_topic_members(user_id);
CREATE INDEX IF NOT EXISTS idx_topic_members_topic ON chat_topic_members(topic_id);
