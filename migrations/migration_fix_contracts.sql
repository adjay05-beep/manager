-- Fix Labor Contracts
ALTER TABLE public.labor_contracts ADD COLUMN IF NOT EXISTS channel_id BIGINT REFERENCES public.channels(id);
CREATE INDEX IF NOT EXISTS idx_contracts_channel ON public.labor_contracts(channel_id);

-- Optional: Backfill? 
-- If we assume single channel for now or just leave null.
-- App logic handles null access (filtered out).
