-- Phase 2.5: Multi-Calendar System

-- 1. Calendars Table
create table if not exists public.calendars (
    id uuid default gen_random_uuid() primary key,
    name text not null,
    type text not null check (type in ('store_default', 'staff_management', 'private')),
    created_by uuid references auth.users(id),
    color text default '#2196F3',
    created_at timestamptz default now()
);

-- 2. Calendar Members Table
create table if not exists public.calendar_members (
    id uuid default gen_random_uuid() primary key,
    calendar_id uuid references public.calendars(id) on delete cascade,
    user_id uuid references auth.users(id) on delete cascade,
    role text default 'viewer', -- owner, editor, viewer
    created_at timestamptz default now()
);

-- 3. RLS Policies
alter table public.calendars enable row level security;
alter table public.calendar_members enable row level security;

-- Users can see calendars they are members of
create policy "View joined calendars"
on public.calendars for select
using (
    exists (
        select 1 from public.calendar_members
        where calendar_id = public.calendars.id
        and user_id = auth.uid()
    )
    or type = 'store_default' -- Everyone sees store default? Or logic handled via members logic?
    -- Let's stick to members logic for cleaner RBAC
);

create policy "View memberships"
on public.calendar_members for select
using (user_id = auth.uid());

-- Triggers or Functions (Optional): Auto-add creator as owner
