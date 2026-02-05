-- [CRITICAL FIX] Unread Counts View Definition
-- Fixes the issue where own messages were counted as unread.
-- Also ensures 'last_read_at' defaults to epoch if missing.

CREATE OR REPLACE VIEW public.unread_counts_view AS
SELECT 
    cm.topic_id, 
    cm.user_id, 
    COUNT(m.id) AS unread_count
FROM public.chat_topic_members cm
JOIN public.chat_messages m ON m.topic_id = cm.topic_id
LEFT JOIN public.chat_user_reading cur ON cur.topic_id = cm.topic_id AND cur.user_id = cm.user_id
WHERE 
    m.user_id <> cm.user_id  -- [FIX] Exclude own messages
    AND m.created_at > COALESCE(cur.last_read_at, '1970-01-01'::timestamp with time zone)
GROUP BY cm.topic_id, cm.user_id;

-- Force Schema Cache Reload for PostgREST
NOTIFY pgrst, 'reload config';
