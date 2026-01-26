-- Fix RLS for Profiles to allow user updates

-- 1. Enable RLS (Ensure it's on)
alter table public.profiles enable row level security;

-- 2. Policy: Allow Users to Update their OWN profile
drop policy if exists "Users can update own profile" on public.profiles;
create policy "Users can update own profile"
on public.profiles for update
using ( auth.uid() = id );

-- 3. Policy: Allow Users to Insert their OWN profile
drop policy if exists "Users can insert own profile" on public.profiles;
create policy "Users can insert own profile"
on public.profiles for insert
with check ( auth.uid() = id );

-- 4. Policy: Allow Users to Select their OWN profile (and potentially others if needed for team view)
-- For now, strict: Own profile + Service Role bypasses everything
drop policy if exists "Users can view own profile" on public.profiles;
create policy "Users can view own profile"
on public.profiles for select
using ( auth.uid() = id );

-- Grant permissions to authenticated users
grant all on public.profiles to authenticated;
grant all on public.profiles to service_role;
