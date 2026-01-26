-- Phase 2: Labor Contracts & Salary Management

create table if not exists public.labor_contracts (
    id uuid default gen_random_uuid() primary key,
    user_id uuid references auth.users(id) not null,
    employee_name text not null,
    employee_type text not null check (employee_type in ('full', 'part')),
    hourly_wage int not null default 0,
    daily_work_hours float not null default 0,
    work_days jsonb not null default '[]'::jsonb, -- Array of ints: 0=Mon, 6=Sun
    contract_start_date date not null default current_date,
    contract_end_date date,
    created_at timestamptz default now()
);

-- Enable RLS
alter table public.labor_contracts enable row level security;

-- Policies
create policy "Users can manage their own contracts"
on public.labor_contracts for all
using (auth.uid() = user_id);

-- Indexes
create index idx_contracts_user on public.labor_contracts(user_id);
