-- [MIGRATION] Add ON DELETE CASCADE to chat-related tables to prevent timeouts during manual deletion
-- This allows deleting a topic in a single request, and the DB will handle the cleanup.

-- 1. chat_messages
ALTER TABLE public.chat_messages
DROP CONSTRAINT IF EXISTS chat_messages_topic_id_fkey,
ADD CONSTRAINT chat_messages_topic_id_fkey
FOREIGN KEY (topic_id)
REFERENCES public.chat_topics(id)
ON DELETE CASCADE;

-- 2. chat_topic_members
ALTER TABLE public.chat_topic_members
DROP CONSTRAINT IF EXISTS chat_topic_members_topic_id_fkey,
ADD CONSTRAINT chat_topic_members_topic_id_fkey
FOREIGN KEY (topic_id)
REFERENCES public.chat_topics(id)
ON DELETE CASCADE;

-- 3. chat_user_reading
ALTER TABLE public.chat_user_reading
DROP CONSTRAINT IF EXISTS chat_user_reading_topic_id_fkey,
ADD CONSTRAINT chat_user_reading_topic_id_fkey
FOREIGN KEY (topic_id)
REFERENCES public.chat_topics(id)
ON DELETE CASCADE;

-- Inform that the schema is updated
SELECT 'Cascade Delete Constraints Applied' as status;
