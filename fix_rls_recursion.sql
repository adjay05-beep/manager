
-- Fix Recursion in channel_members policy

-- 1. Create a secure function to check membership
CREATE OR REPLACE FUNCTION public.is_member_of(_channel_id bigint)
RETURNS boolean AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 
    FROM public.channel_members 
    WHERE channel_id = _channel_id 
    AND user_id = auth.uid()
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Update Policy for channel_members
DROP POLICY IF EXISTS "View members of my channels" ON public.channel_members;
CREATE POLICY "View members of my channels" ON public.channel_members
FOR SELECT USING (
  -- I can see myself
  user_id = auth.uid()
  OR
  -- I can see members of channels I belong to (using secure function to break recursion)
  public.is_member_of(channel_id)
);
