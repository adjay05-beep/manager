-- [CRITICAL FIX] Reset ID Sequences (v2 - Robust)
-- This script fixes the "Duplicate key value violates unique constraint" error.
-- It works correctly even if the tables are completely empty.

-- 1. Chat Messages
SELECT setval(pg_get_serial_sequence('public.chat_messages', 'id'), 
              COALESCE((SELECT MAX(id) FROM public.chat_messages), 1), 
              (SELECT MAX(id) FROM public.chat_messages) IS NOT NULL);

-- 2. Chat Topics
SELECT setval(pg_get_serial_sequence('public.chat_topics', 'id'), 
              COALESCE((SELECT MAX(id) FROM public.chat_topics), 1), 
              (SELECT MAX(id) FROM public.chat_topics) IS NOT NULL);

-- 3. Chat Topic Members
SELECT setval(pg_get_serial_sequence('public.chat_topic_members', 'id'), 
              COALESCE((SELECT MAX(id) FROM public.chat_topic_members), 1), 
              (SELECT MAX(id) FROM public.chat_topic_members) IS NOT NULL);

-- 4. Channels
SELECT setval(pg_get_serial_sequence('public.channels', 'id'), 
              COALESCE((SELECT MAX(id) FROM public.channels), 1), 
              (SELECT MAX(id) FROM public.channels) IS NOT NULL);

-- 5. Chat Categories
SELECT setval(pg_get_serial_sequence('public.chat_categories', 'id'), 
              COALESCE((SELECT MAX(id) FROM public.chat_categories), 1), 
              (SELECT MAX(id) FROM public.chat_categories) IS NOT NULL);

-- 6. Handovers
SELECT setval(pg_get_serial_sequence('public.handovers', 'id'), 
              COALESCE((SELECT MAX(id) FROM public.handovers), 1), 
              (SELECT MAX(id) FROM public.handovers) IS NOT NULL);

-- 7. Attendance Logs
SELECT setval(pg_get_serial_sequence('public.attendance_logs', 'id'), 
              COALESCE((SELECT MAX(id) FROM public.attendance_logs), 1), 
              (SELECT MAX(id) FROM public.attendance_logs) IS NOT NULL);

