alter table public.channels add column if not exists channel_code text;
alter table public.channels add column if not exists location_address text; -- [ADDED] Legacy support
alter table public.channels add column if not exists latitude double precision; -- [ADDED] Legacy support
alter table public.channels add column if not exists longitude double precision; -- [ADDED] Legacy support
alter table public.channels add column if not exists owner_id uuid; -- [ADDED] Legacy support
alter table public.channels add column if not exists subscription_tier text default 'free'; -- [ADDED] Legacy support
alter table public.chat_topics add column if not exists is_favorite boolean default false;
alter table public.chat_topics add column if not exists display_order int default 0;
alter table public.chat_topics add column if not exists is_priority boolean default false; -- [ADDED] Legacy support

-- Ensure schema cache is reloaded
NOTIFY pgrst, 'reload config';
