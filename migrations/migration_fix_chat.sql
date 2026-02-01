-- Fix Chat Messages
ALTER TABLE public.chat_messages ADD COLUMN IF NOT EXISTS channel_id BIGINT REFERENCES public.channels(id);
CREATE INDEX IF NOT EXISTS idx_messages_channel ON public.chat_messages(channel_id);

-- Backfill from Topics
UPDATE public.chat_messages m
SET channel_id = t.channel_id
FROM public.chat_topics t
WHERE m.topic_id = t.id
AND m.channel_id IS NULL;
