SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'chat_messages';
SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'chat_topics';
SELECT * FROM information_schema.tables WHERE table_name LIKE '%read%';
