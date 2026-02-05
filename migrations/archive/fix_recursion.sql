-- Fix Infinite Recursion on channel_members RLS
-- The error "infinite recursion detected in policy" (42P17) occurs because the RLS policy references the table itself in a subquery.
-- We fix this by moving the check logic into a "SECURITY DEFINER" function which bypasses RLS.

-- 1. Create a SECURITY DEFINER function to break the recursion loop
-- This function runs with the privileges of the creator (admin/service_role), safely checking membership without triggering RLS.
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

-- 2. Drop the problematic policies (Removing potentially conflicting policies)
DROP POLICY IF EXISTS "Enable read access for all users" ON "public"."channel_members";
DROP POLICY IF EXISTS "Members can view other members" ON "public"."channel_members";
DROP POLICY IF EXISTS "View members" ON "public"."channel_members";
DROP POLICY IF EXISTS "Public profiles are viewable by everyone." ON "public"."channel_members"; 

-- 3. Create the new non-recursive policy
CREATE POLICY "View members" ON "public"."channel_members"
AS PERMISSIVE FOR SELECT
TO authenticated
USING (
  -- User can see their own membership
  user_id = auth.uid()
  OR
  -- User can see other members in the same channel (using the function to bypass recursion)
  public.is_channel_member(channel_id)
);

-- 4. Enable RLS (Ensure it is on)
ALTER TABLE "public"."channel_members" ENABLE ROW LEVEL SECURITY;

-- 5. Grant access to the function
GRANT EXECUTE ON FUNCTION public.is_channel_member TO authenticated, service_role;
