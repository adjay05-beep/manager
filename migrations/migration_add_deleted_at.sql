-- Add deleted_at column for Soft Delete
ALTER TABLE order_memos ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;
