from db import supabase

sql = """
CREATE TABLE IF NOT EXISTS public.calendar_events (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at timestamptz DEFAULT now(),
    title text NOT NULL,
    description text,
    start_date timestamptz NOT NULL,
    end_date timestamptz NOT NULL,
    event_type text DEFAULT 'shift',
    color text DEFAULT '#1DDB16',
    user_id uuid REFERENCES public.profiles(id)
);

-- Enable Realtime
alter publication supabase_realtime add table calendar_events;
"""

try:
    # Attempting to run via a potential exec_sql RPC if it exists
    # If not, we'll inform the user or try another way.
    print("Attempting to create calendar_events table...")
    # Many Supabase setups have a 'exec_sql' or similar to help agents.
    # If not, this might fail, but it's worth a try.
    supabase.rpc('exec_sql', {'sql_query': sql}).execute()
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
    print("\nPlease run the following SQL in your Supabase SQL Editor:\n")
    print(sql)
