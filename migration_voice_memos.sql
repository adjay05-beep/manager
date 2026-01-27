-- Create voice_memos table
CREATE TABLE IF NOT EXISTS public.voice_memos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    channel_id BIGINT REFERENCES public.channels(id),
    content TEXT,
    audio_urls TEXT[], -- Support multiple files? No, keep simple TEXT for now or JSONB. Let's stick to TEXT as per plan.
    audio_url TEXT,
    is_private BOOLEAN DEFAULT true,
    audio_expires_at TIMESTAMP WITH TIME ZONE DEFAULT (now() + interval '2 days'),
    text_expires_at TIMESTAMP WITH TIME ZONE DEFAULT (now() + interval '15 days'),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Indexes for Scale
CREATE INDEX idx_voice_memos_user_id ON public.voice_memos(user_id);
CREATE INDEX idx_voice_memos_channel_id ON public.voice_memos(channel_id);
CREATE INDEX idx_voice_memos_audio_exp ON public.voice_memos(audio_expires_at);
CREATE INDEX idx_voice_memos_text_exp ON public.voice_memos(text_expires_at);

-- Enable RLS
ALTER TABLE public.voice_memos ENABLE ROW LEVEL SECURITY;

-- Policies

-- 1. View Policies
-- Users can see their own private memos
CREATE POLICY "Users can view own private memos"
ON public.voice_memos FOR SELECT
USING (auth.uid() = user_id AND is_private = true);

-- Users can see public memos in their channels
CREATE POLICY "Users can view channel public memos"
ON public.voice_memos FOR SELECT
USING (
    is_private = false AND
    channel_id IN (
        SELECT channel_id FROM public.channel_members WHERE user_id = auth.uid()
    )
);

-- 2. Insert Policy
CREATE POLICY "Users can insert own memos"
ON public.voice_memos FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- 3. Delete Policy
-- Users can delete their own memos
CREATE POLICY "Users can delete own memos"
ON public.voice_memos FOR DELETE
USING (auth.uid() = user_id);

-- Owners can delete any public memo in their channel (Optional, for moderation)
CREATE POLICY "Owners can delete channel public memos"
ON public.voice_memos FOR DELETE
USING (
    is_private = false AND
    EXISTS (
        SELECT 1 FROM public.channel_members 
        WHERE user_id = auth.uid() 
        AND channel_id = voice_memos.channel_id 
        AND role = 'owner'
    )
);
