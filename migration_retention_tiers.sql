-- Add subscription_tier to channels
ALTER TABLE public.channels ADD COLUMN IF NOT EXISTS subscription_tier TEXT DEFAULT 'free';

-- Validate allowed values (simple check constraint)
ALTER TABLE public.channels DROP CONSTRAINT IF EXISTS check_tier_values;
ALTER TABLE public.channels ADD CONSTRAINT check_tier_values CHECK (subscription_tier IN ('free', 'standard', 'premium'));

-- Index for analytics if needed
CREATE INDEX IF NOT EXISTS idx_channels_tier ON public.channels(subscription_tier);
