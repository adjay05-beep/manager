-- Migration: Add Address Support
ALTER TABLE channels ADD COLUMN IF NOT EXISTS address text;
