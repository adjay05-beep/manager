-- [Fix RLS for Mobile/Web Access]

-- 1. Enable RLS (Ensure it is on)
ALTER TABLE public.channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.channel_members ENABLE ROW LEVEL SECURITY;

-- 2. Allow users to see their own membership
DROP POLICY IF EXISTS "Users can view own channel memberships" ON public.channel_members;
CREATE POLICY "Users can view own channel memberships"
ON public.channel_members FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

-- 3. Allow users to see channels they belong to
DROP POLICY IF EXISTS "Users can view channels they belong to" ON public.channels;
CREATE POLICY "Users can view channels they belong to"
ON public.channels FOR SELECT
TO authenticated
USING (
  exists (
    select 1 from public.channel_members
    where channel_members.channel_id = channels.id
    and channel_members.user_id = auth.uid()
  )
);

-- 4. Allow users to create channels (if not exists)
DROP POLICY IF EXISTS "Users can create channels" ON public.channels;
CREATE POLICY "Users can create channels"
ON public.channels FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = owner_id);

-- 5. Allow owners to insert membership for themselves (during create)
DROP POLICY IF EXISTS "Owners can insert their own membership" ON public.channel_members;
CREATE POLICY "Owners can insert their own membership"
ON public.channel_members FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);
