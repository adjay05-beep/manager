-- Phase 5.1: Calendar RBAC

-- Ensure created_by exists for ownership
ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS created_by uuid REFERENCES profiles(id) ON DELETE SET NULL;

-- Enable RLS for Calendar if desired (Application Level currently used, but good for backup)
ALTER TABLE calendar_events ENABLE ROW LEVEL SECURITY;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_calendar_created_by ON calendar_events(created_by);
