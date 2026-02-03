-- GPS Requests Table for temporary GPS data exchange
-- This table is used to communicate GPS coordinates from the browser to the server

CREATE TABLE IF NOT EXISTS gps_requests (
    id TEXT PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'error')),
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    accuracy DOUBLE PRECISION,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_gps_requests_id ON gps_requests(id);
CREATE INDEX IF NOT EXISTS idx_gps_requests_created ON gps_requests(created_at);

-- Auto-delete old records (older than 5 minutes)
CREATE OR REPLACE FUNCTION cleanup_old_gps_requests()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM gps_requests WHERE created_at < NOW() - INTERVAL '5 minutes';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to cleanup on insert
DROP TRIGGER IF EXISTS trigger_cleanup_gps_requests ON gps_requests;
CREATE TRIGGER trigger_cleanup_gps_requests
    AFTER INSERT ON gps_requests
    EXECUTE FUNCTION cleanup_old_gps_requests();

-- RLS Policies
ALTER TABLE gps_requests ENABLE ROW LEVEL SECURITY;

-- Allow anyone to insert (for anonymous GPS page)
CREATE POLICY "Allow insert for all" ON gps_requests
    FOR INSERT WITH CHECK (true);

-- Allow anyone to select (for polling)
CREATE POLICY "Allow select for all" ON gps_requests
    FOR SELECT USING (true);

-- Allow anyone to update (for GPS page to update status)
CREATE POLICY "Allow update for all" ON gps_requests
    FOR UPDATE USING (true);

-- Allow anyone to delete (for cleanup)
CREATE POLICY "Allow delete for all" ON gps_requests
    FOR DELETE USING (true);

-- Grant permissions
GRANT ALL ON gps_requests TO anon;
GRANT ALL ON gps_requests TO authenticated;
