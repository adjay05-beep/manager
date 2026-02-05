-- Phase 9: Thread Grouping (Category)
ALTER TABLE chat_topics ADD COLUMN IF NOT EXISTS category TEXT DEFAULT '일반';

-- Initial grouping for existing threads
UPDATE chat_topics SET category = '공지' WHERE name LIKE '%공지%';
UPDATE chat_topics SET category = '일반' WHERE category IS NULL;
