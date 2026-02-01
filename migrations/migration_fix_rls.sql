-- Enable RLS on all tables
ALTER TABLE public.channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.channel_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.calendar_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.labor_contracts ENABLE ROW LEVEL SECURITY;
-- voice_memos already enabled

-- Helper: Check Membership

-- 1. Channels
DROP POLICY IF EXISTS "View channels if member" ON public.channels;
CREATE POLICY "View channels if member" ON public.channels
FOR SELECT USING (
  exists (select 1 from public.channel_members where channel_id = id and user_id = auth.uid())
);

-- 2. Channel Members
DROP POLICY IF EXISTS "View members of my channels" ON public.channel_members;
CREATE POLICY "View members of my channels" ON public.channel_members
FOR SELECT USING (
  exists (
    select 1 from public.channel_members cm 
    where cm.channel_id = channel_members.channel_id 
    and cm.user_id = auth.uid()
  ) OR user_id = auth.uid()
);

-- 3. Calendar Events
DROP POLICY IF EXISTS "View channel events" ON public.calendar_events;
CREATE POLICY "View channel events" ON public.calendar_events
FOR SELECT USING (
  exists (select 1 from public.channel_members where channel_id = calendar_events.channel_id and user_id = auth.uid())
);

DROP POLICY IF EXISTS "Modify channel events" ON public.calendar_events;
CREATE POLICY "Modify channel events" ON public.calendar_events
FOR ALL USING (
  exists (select 1 from public.channel_members where channel_id = calendar_events.channel_id and user_id = auth.uid())
);

-- 4. Labor Contracts
DROP POLICY IF EXISTS "View own or managed contracts" ON public.labor_contracts;
CREATE POLICY "View own or managed contracts" ON public.labor_contracts
FOR SELECT USING (
  (user_id = auth.uid()) OR 
  exists (select 1 from public.channel_members where channel_id = labor_contracts.channel_id and user_id = auth.uid() and role = 'owner')
);

DROP POLICY IF EXISTS "Owner manage contracts" ON public.labor_contracts;
CREATE POLICY "Owner manage contracts" ON public.labor_contracts
FOR ALL USING (
  exists (select 1 from public.channel_members where channel_id = labor_contracts.channel_id and user_id = auth.uid() and role = 'owner')
);

-- 5. Chat Categories/Topics/Messages
DROP POLICY IF EXISTS "View channel chat" ON public.chat_categories;
CREATE POLICY "View channel chat" ON public.chat_categories FOR SELECT USING (exists (select 1 from public.channel_members where channel_id = chat_categories.channel_id and user_id = auth.uid()));

DROP POLICY IF EXISTS "View channel topics" ON public.chat_topics;
CREATE POLICY "View channel topics" ON public.chat_topics FOR SELECT USING (exists (select 1 from public.channel_members where channel_id = chat_topics.channel_id and user_id = auth.uid()));

DROP POLICY IF EXISTS "View channel messages" ON public.chat_messages;
CREATE POLICY "View channel messages" ON public.chat_messages FOR SELECT USING (exists (select 1 from public.channel_members where channel_id = chat_messages.channel_id and user_id = auth.uid()));

DROP POLICY IF EXISTS "Insert channel messages" ON public.chat_messages;
CREATE POLICY "Insert channel messages" ON public.chat_messages FOR INSERT WITH CHECK (exists (select 1 from public.channel_members where channel_id = chat_messages.channel_id and user_id = auth.uid()));
