-- [SUPABASE REALTIME ENABLEMENT]
-- 이 SQL을 Supabase Dashboard의 'SQL Editor'에 복사하여 실행하세요.
-- 이 명령은 앱에서 실시간 업데이트를 수신할 수 있도록 데이터베이스 설정을 변경합니다.

-- 1. 기존의 supabase_realtime 게시(publication)에 테이블 추가
alter publication supabase_realtime add table chat_messages;
alter publication supabase_realtime add table chat_topics;

-- 2. 만약 publication이 없다면 생성 (보통 기본으로 존재합니다)
-- create publication supabase_realtime for table chat_messages, chat_topics;

-- 3. 확인 (아무것도 나오지 않으면 위 명령이 성공한 것입니다)
-- 이제 앱을 재기동하면 5초 대기 없이 메시지가 즉시 수신됩니다!
