CREATE TABLE IF NOT EXISTS public.order_memos (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at timestamptz DEFAULT now(),
    content text NOT NULL,
    user_id uuid REFERENCES public.profiles(id)
);

-- Enable Realtime
alter publication supabase_realtime add table order_memos;
