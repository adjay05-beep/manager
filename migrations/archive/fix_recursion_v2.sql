-- Fix Recursion V2: Aggressive Clean using PL/pgSQL
-- This script removes ALL policies on 'channel_members' to ensure the broken recursive policy is gone, then recreates necessary policies.

-- 1. Drop ALL policies on channel_members
DO $$
DECLARE
  pol record;
BEGIN
  FOR pol IN SELECT policyname FROM pg_policies WHERE tablename = 'channel_members' LOOP
    EXECUTE 'DROP POLICY IF EXISTS "' || pol.policyname || '" ON "public"."channel_members"';
  END LOOP;
END $$;

-- 2. Create/Update the SECURITY DEFINER function
-- This function allows safe membership checks without triggering RLS recursion
CREATE OR REPLACE FUNCTION public.is_channel_member(check_channel_id bigint)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM channel_members
    WHERE channel_id = check_channel_id
    AND user_id = auth.uid()
  );
$$;

-- 3. Create CLEAN policies

-- A. VIEW (Select)
CREATE POLICY "Safe View Members" ON "public"."channel_members"
FOR SELECT
TO authenticated
USING (
  user_id = auth.uid() -- Can see self
  OR
  public.is_channel_member(channel_id) -- Can see others in my channel
);

-- B. INSERT (Join)
CREATE POLICY "Allow Join" ON "public"."channel_members"
FOR INSERT
TO authenticated
WITH CHECK (true);

-- C. UPDATE (Self only or Admin?)
CREATE POLICY "Update Self" ON "public"."channel_members"
FOR UPDATE
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

-- D. DELETE (Self only)
CREATE POLICY "Leave Channel" ON "public"."channel_members"
FOR DELETE
TO authenticated
USING (user_id = auth.uid());

-- 4. Ensure RLS is enabled
ALTER TABLE "public"."channel_members" ENABLE ROW LEVEL SECURITY;

-- 5. Grant access to function
GRANT EXECUTE ON FUNCTION public.is_channel_member TO authenticated, service_role;
