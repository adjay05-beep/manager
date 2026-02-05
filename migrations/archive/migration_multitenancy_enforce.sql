-- [Multi-tenancy Enforcement Migration]
-- Target: Ensure all business tables have channel_id and RLS enabled.

-- 1. Order Memos (Voice Memos for Work)
-- Current: id, content, user_id
-- Action: Add channel_id
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'order_memos' AND column_name = 'channel_id') THEN
        ALTER TABLE public.order_memos ADD COLUMN channel_id BIGINT REFERENCES public.channels(id);
        CREATE INDEX idx_order_memos_channel ON public.order_memos(channel_id);
    END IF;
END $$;

ALTER TABLE public.order_memos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Tenant Isolation for Orders" ON public.order_memos;
CREATE POLICY "Tenant Isolation for Orders" ON public.order_memos
USING (
    channel_id IN (
        SELECT channel_id FROM public.channel_members 
        WHERE user_id = auth.uid()
    )
);

-- 2. Calendars (If missing, create with channel_id)
CREATE TABLE IF NOT EXISTS public.calendars (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name text NOT NULL,
    type text NOT NULL CHECK (type IN ('store_default', 'staff_management', 'private')),
    channel_id BIGINT REFERENCES public.channels(id) ON DELETE CASCADE, -- Mandate Channel ID
    created_by uuid REFERENCES auth.users(id),
    color text DEFAULT '#2196F3',
    created_at timestamptz DEFAULT now()
);

-- Ensure channel_id exists if table already existed without it
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'calendars' AND column_name = 'channel_id') THEN
        ALTER TABLE public.calendars ADD COLUMN channel_id BIGINT REFERENCES public.channels(id) ON DELETE CASCADE;
        CREATE INDEX idx_calendars_channel ON public.calendars(channel_id);
    END IF;
END $$;

ALTER TABLE public.calendars ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Tenant Isolation for Calendars" ON public.calendars;
CREATE POLICY "Tenant Isolation for Calendars" ON public.calendars
USING (
    channel_id IN (
        SELECT channel_id FROM public.channel_members 
        WHERE user_id = auth.uid()
    )
    OR 
    -- Allow created_by access too (for private calendars if they are not channel bound? No, strict mode: everything belongs to channel)
    (type = 'private' AND created_by = auth.uid()) 
);

-- 3. Calendar Events Linkage
CREATE TABLE IF NOT EXISTS public.calendar_events (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    calendar_id uuid REFERENCES public.calendars(id) ON DELETE CASCADE,
    channel_id BIGINT REFERENCES public.channels(id) ON DELETE CASCADE, -- [FIX] Added for Code Compatibility
    title text NOT NULL,
    start_at timestamptz NOT NULL,
    end_at timestamptz NOT NULL,
    metadata jsonb DEFAULT '{}',
    created_by uuid REFERENCES auth.users(id)
);

-- Ensure columns exist (Fix for existing table)
DO $$
BEGIN
    -- Check channel_id
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'calendar_events' AND column_name = 'channel_id') THEN
        ALTER TABLE public.calendar_events ADD COLUMN channel_id BIGINT REFERENCES public.channels(id) ON DELETE CASCADE;
        CREATE INDEX idx_calendar_events_channel ON public.calendar_events(channel_id);
    END IF;

    -- Check calendar_id
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'calendar_events' AND column_name = 'calendar_id') THEN
        ALTER TABLE public.calendar_events ADD COLUMN calendar_id uuid REFERENCES public.calendars(id) ON DELETE CASCADE;
        CREATE INDEX idx_calendar_events_calendar ON public.calendar_events(calendar_id);
    END IF;
END $$;

ALTER TABLE public.calendar_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Tenant Isolation for Events" ON public.calendar_events;
CREATE POLICY "Tenant Isolation for Events" ON public.calendar_events
USING (
    channel_id IN (
        SELECT channel_id FROM public.channel_members 
        WHERE user_id = auth.uid()
    )
);

-- 4. Voice Memos (Check existence)
-- Already checked, but ensure RLS
ALTER TABLE public.voice_memos ENABLE ROW LEVEL SECURITY;
-- (Assuming standard policy exists, but let's re-enforce strict tenant check)
DROP POLICY IF EXISTS "Tentant Isolation for Voice Memos" ON public.voice_memos;
CREATE POLICY "Tentant Isolation for Voice Memos" ON public.voice_memos
USING (
    channel_id IN (
         SELECT channel_id FROM public.channel_members WHERE user_id = auth.uid()
    )
    AND (is_private = false OR user_id = auth.uid())
);
