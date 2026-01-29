-- Add Business Verification columns to channels table
ALTER TABLE channels 
ADD COLUMN IF NOT EXISTS business_number TEXT,
ADD COLUMN IF NOT EXISTS business_owner_name TEXT,
ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;

-- Optional: Add index for business number
CREATE INDEX IF NOT EXISTS idx_channels_business_number ON channels(business_number);
