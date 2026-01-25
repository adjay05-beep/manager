-- Add columns for Calendar V2 Features
ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS is_all_day BOOLEAN DEFAULT FALSE;
ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS location TEXT;
ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS link TEXT;
ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS participant_ids JSONB DEFAULT '[]'::jsonb;
