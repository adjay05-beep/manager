-- 1. Relax constraints on profiles (allow users without strict Auth linkage for Demo)
alter table profiles drop constraint if exists profiles_id_fkey;

-- 2. Insert a Demo User (The Manager)
insert into profiles (id, username, full_name, avatar_url)
values ('00000000-0000-0000-0000-000000000001', '점장님', 'The Manager', '👤')
on conflict (id) do nothing;

-- 3. Allow anonymous inserts for Chat Messages (for Demo)
-- Drop existing restricted policy if possible, or add a permissive one
drop policy if exists "Authenticated users can insert messages" on chat_messages;
create policy "Allow Anon Inserts for Demo" on chat_messages for insert with check (true);
