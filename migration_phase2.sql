-- Phase 2: Priority and Unread Tracking

-- 1. Add is_priority to chat_topics
ALTER TABLE chat_topics ADD COLUMN IF NOT EXISTS is_priority BOOLEAN DEFAULT FALSE;

-- 2. Create tracking table for unread status
CREATE TABLE IF NOT EXISTS chat_user_reading (
    topic_id bigint REFERENCES chat_topics(id) ON DELETE CASCADE,
    user_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
    last_read_at timestamp with time zone DEFAULT now(),
    PRIMARY KEY (topic_id, user_id)
);

-- Enable RLS for the new table
ALTER TABLE chat_user_reading ENABLE ROW LEVEL SECURITY;

-- Simple policies for demo/manager use
CREATE POLICY "Users can view their own reading status" 
ON chat_user_reading FOR SELECT USING (true);

CREATE POLICY "Users can update their own reading status" 
ON chat_user_reading FOR INSERT WITH CHECK (true);

CREATE POLICY "Users can update their own reading status (Update)" 
ON chat_user_reading FOR UPDATE USING (true);
