-- CRITICAL PRODUCTION FIX: Grant Permissions to Tables

-- 1. Labor Contracts (Fixes Blank Calendar in Staff Mode)
GRANT ALL ON TABLE public.labor_contracts TO authenticated;
GRANT ALL ON TABLE public.labor_contracts TO service_role;

-- 2. Calendar Events (Fixes Store Mode)
GRANT ALL ON TABLE public.calendar_events TO authenticated;
GRANT ALL ON TABLE public.calendar_events TO service_role;

-- 3. Sequences (Ensures ID generation works)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- 4. Enable RLS on Labor Contracts (Safety)
ALTER TABLE public.labor_contracts ENABLE ROW LEVEL SECURITY;

-- 5. Policy for Labor Contracts
DROP POLICY IF EXISTS "Authenticated users can select contracts" ON public.labor_contracts;
CREATE POLICY "Authenticated users can select contracts" ON public.labor_contracts
    FOR SELECT
    USING (true); 
