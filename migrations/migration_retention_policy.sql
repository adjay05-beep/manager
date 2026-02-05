-- Migration: Add empty_since column to chat_topics for retention policy
-- Purpose: Track when a topic becomes empty to allow for auto-deletion after a grace period (e.g. 3 days).

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='chat_topics' AND column_name='empty_since') THEN
        ALTER TABLE chat_topics ADD COLUMN empty_since TIMESTAMP WITH TIME ZONE DEFAULT NULL;
        RAISE NOTICE 'Added empty_since column to chat_topics';
    ELSE
        RAISE NOTICE 'Column empty_since already exists in chat_topics';
    END IF;
END $$;
