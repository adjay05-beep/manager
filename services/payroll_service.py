import asyncio
from datetime import datetime
import calendar as cal_mod
from db import service_supabase
import os

class PayrollService:
    def __init__(self):
        pass

    async def calculate_payroll(self, user_id, channel_id, year, month):
        """
        Calculates payroll for a specific channel and month.
        Returns a dictionary containing:
        - summary: {total_std, total_act, ...}
        - employees: List of dicts with per-employee calc details
        """
        try:
            # 1. Fetch Data (Async)
            from postgrest import SyncPostgrestClient
            # We need a client. Ideally passed in or created.
            # Using service_supabase directly for read operations might be okay via database functions, 
            # but to reuse the logic we saw in work_view which used a client with headers...
            # Actually, for calculation, we can use service_supabase (admin) or pass the client.
            # WORK_VIEW used User's client for RLS visibility.
            # We should probably accept the client or token. But simpler: use the RLS-enforcing client if possible.
            # For now, let's assume we use service_supabase for "calculation" but we must filter correctly.
            # WAIT: If we use service_supabase, we bypass RLS. This might show data the user shouldn't see.
            # The original code used a client created with user headers.
            # Let's mock that or require passing the headers/client.
            # For simplicity in this refactor, let's fallback to service_supabase BUT filter strictly by channel_id.
            # Since channel_id is the boundary, and the user is a manager of that channel (checked by caller), it's safeish.
            
            # [SECURE] Use Authenticated Client to enforce RLS
            # Identify User Token
            from services.auth_service import auth_service
            session = auth_service.get_session()
            if not session or not session.access_token:
               # Fallback for testing/public or error - but for payroll we need security.
               # If no session, we can't show data safely.
               # However, current user_id is passed.
               # Let's try to get headers.
               headers = auth_service.get_auth_headers()
               if not headers:
                   print("WARNING: No Auth Headers for Payroll - RLS might fail or we use Anonymous")
                   # Fallback to service_supabase IF we are sure (Admin Override?)
                   # No, standard execution should fail or be empty if not auth.
                   # But let's use the headers we got.
               else:
                   pass
            else:
                 headers = auth_service.get_auth_headers()

            url = os.environ.get("SUPABASE_URL")
            # Create isolated client with user auth
            # Create isolated client with user auth
            client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public") 
            
            try:
                # Fetch Contracts
                res = await asyncio.to_thread(lambda: client.table("labor_contracts").select("*")
                                                .eq("channel_id", channel_id).execute())
                contracts = res.data or []

                # Fetch Overrides (Work Schedules)
                start_iso = f"{year}-{month:02d}-01T00:00:00"
                last_day = cal_mod.monthrange(year, month)[1]
                end_iso = f"{year}-{month:02d}-{last_day}T23:59:59"
                
                o_res = await asyncio.to_thread(lambda: client.table("calendar_events")
                                                .select("*")
                                                .eq("is_work_schedule", True)
                                                .gte("start_date", start_iso)
                                                .lte("start_date", end_iso)
                                                .eq("channel_id", channel_id)
                                                .execute())
                overrides = o_res.data or []

                # Process Data
                return self._process_calculation(contracts, overrides, year, month)
            finally:
                # [RESOURCE] Close the HTTP session to prevent socket leaks
                try:
                    client.session.close()
                except: pass

        except Exception as e:
            print(f"Payroll Service Calc Error: {e}")
            raise e

    def _process_calculation(self, contracts, overrides, year, month):
        # Helper to map event to name
        eid_to_name = {c['id']: c.get('employee_name', 'Unknown').strip() for c in contracts}
        
        def parse_name(ev):
            eid = ev.get('employee_id')
            if eid and eid in eid_to_name: return eid_to_name[eid]
            t = ev.get('title', '')
            # Filter emojis
            for emoji in ["🟢", "❌", "⭐", "🔥"]:
                t = t.replace(emoji, '')
            return t.split('(')[0].split('결근')[0].strip() or "Unknown"

        name_to_events = {}
        all_names = set(eid_to_name.values())
        
        for o in overrides:
            nm = parse_name(o)
            if not nm: continue
            all_names.add(nm)
            if nm not in name_to_events: name_to_events[nm] = []
            name_to_events[nm].append(o)

        name_to_history = {}
        for c in contracts:
            nm = c.get('employee_name', 'Unknown').strip()
            if nm not in name_to_history: name_to_history[nm] = []
            name_to_history[nm].append(c)

        # Iterate
        employee_results = []
        total_std = 0
        total_act = 0
        days_in_month = cal_mod.monthrange(year, month)[1]
        has_incomplete = False

        for name in sorted(all_names):
            history = name_to_history.get(name, [])
            latest = None
            if history:
                history.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                latest = history[0]

            # 1. Standard Calc
            std_pay = 0
            std_days = 0
            h_wage = None
            m_wage = 0
            wage_type = 'hourly'
            daily_hours = 0
            work_days = []

            if latest:
                # Resigned check
                is_resigned = False
                ed_str = latest.get('contract_end_date')
                if ed_str:
                    try:
                        ed = datetime.strptime(ed_str, "%Y-%m-%d")
                        if ed.year < year or (ed.year == year and ed.month < month): is_resigned = True
                    except: pass
                
                if not is_resigned:
                    wage_type = latest.get('wage_type', 'hourly')
                    h_wage = latest.get('hourly_wage') or 9860
                    m_wage = latest.get('monthly_wage') or 0
                    daily_hours = latest.get('daily_work_hours', 8)
                    work_days = latest.get('work_days', [])

                    for d in range(1, days_in_month + 1):
                        if datetime(year, month, d).weekday() in work_days: std_days += 1
                    
                    if wage_type == 'monthly': std_pay = m_wage
                    else: std_pay = std_days * daily_hours * h_wage

            # 2. Actual Calc
            act_pay = 0
            act_hours = 0
            act_days = 0
            override_wage = None
            override_days = set()

            events = name_to_events.get(name, [])
            for o in events:
                if o.get('hourly_wage'): 
                    override_wage = float(o['hourly_wage'])
                
                try:
                    day = int(o['start_date'].split('T')[0].split('-')[-1])
                    override_days.add(day)
                    
                    s_str = o['start_date'].split('T')[1][:5]
                    e_str = o['end_date'].split('T')[1][:5]
                    sh, sm = map(int, s_str.split(':'))
                    eh, em = map(int, e_str.split(':'))
                    diff = (eh + em/60) - (sh + sm/60)
                    if diff < 0: diff += 24
                    act_hours += diff
                except: pass
            
            act_days = len(override_days)
            
            # Fill non-override days from Standard
            if latest and not is_resigned:
                for d in range(1, days_in_month + 1):
                    if d not in override_days and datetime(year, month, d).weekday() in work_days:
                        act_hours += daily_hours
                        act_days += 1
            
            # Determine Wage
            final_h_wage = h_wage
            if not latest:
                final_h_wage = override_wage
                wage_type = 'hourly'
            elif override_wage:
                final_h_wage = override_wage
            
            # Calculate Final Pay
            final_act_pay = None
            if final_h_wage is None and wage_type == 'hourly':
                final_act_pay = None # Unknown
                if act_hours > 0: has_incomplete = True
            elif wage_type == 'monthly':
                final_act_pay = m_wage
            else:
                final_act_pay = act_hours * (final_h_wage if final_h_wage else 0)

            total_std += std_pay
            if final_act_pay is not None: total_act += final_act_pay

            employee_results.append({
                "name": name,
                "std_pay": std_pay,
                "std_days": std_days,
                "act_pay": final_act_pay,
                "act_days": act_days,
                "act_hours": act_hours,
                "diff": (final_act_pay - std_pay) if final_act_pay is not None else 0,
                "h_wage": final_h_wage,
                "is_incomplete": (final_act_pay is None and act_hours > 0),
                "events": events # Passed for context if needed
            })

        return {
            "summary": {
                "total_std": total_std,
                "total_act": total_act,
                "diff": total_act - total_std,
                "has_incomplete": has_incomplete
            },
            "employees": employee_results
        }

    async def update_wage_override(self, event_ids, new_wage):
        """Updates hourly_wage for specific calendar events"""
        try:
             # [VALIDATION] Ensure wage is non-negative
             try:
                 val = float(new_wage)
                 if val < 0: raise ValueError("Negative Wage")
             except ValueError:
                 raise ValueError(f"Invalid wage value: {new_wage}")

             await asyncio.to_thread(lambda: service_supabase.table("calendar_events").update({
                "hourly_wage": val,
                "wage_updated_at": datetime.now().isoformat()
            }).in_("id", event_ids).execute())
             return True
        except Exception as e:
            print(f"Wage Update Error: {e}")
            raise e

payroll_service = PayrollService()
