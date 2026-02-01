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
        client = None
        try:
            from postgrest import SyncPostgrestClient
            from services.auth_service import auth_service

            # [CRITICAL FIX] Safely get auth headers with fallback
            headers = auth_service.get_auth_headers()

            if not headers:
                # Fallback to service_supabase for admin operations
                print("WARNING: No Auth Headers for Payroll - Using service client")
                # Use service_supabase directly instead of creating new client
                res = await asyncio.to_thread(lambda: service_supabase.table("labor_contracts").select("*")
                                                .eq("channel_id", channel_id).execute())
                contracts = res.data or []

                start_iso = f"{year}-{month:02d}-01T00:00:00"
                last_day = cal_mod.monthrange(year, month)[1]
                end_iso = f"{year}-{month:02d}-{last_day}T23:59:59"

                o_res = await asyncio.to_thread(lambda: service_supabase.table("calendar_events")
                                                .select("*")
                                                .eq("is_work_schedule", True)
                                                .gte("start_date", start_iso)
                                                .lte("start_date", end_iso)
                                                .eq("channel_id", channel_id)
                                                .execute())
                overrides = o_res.data or []
                return self._process_calculation(contracts, overrides, year, month)

            url = os.environ.get("SUPABASE_URL")
            if not url:
                raise ValueError("SUPABASE_URL environment variable not set")

            # Create isolated client with user auth
            client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public", timeout=30)

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
                except Exception:
                    pass  # Session cleanup failed

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
            is_resigned = False  # [FIX] 변수 범위를 블록 바깥으로 이동

            if latest:
                # Resigned check
                ed_str = latest.get('contract_end_date')
                if ed_str:
                    try:
                        ed = datetime.strptime(ed_str, "%Y-%m-%d")
                        if ed.year < year or (ed.year == year and ed.month < month): is_resigned = True
                    except ValueError:
                        pass  # Invalid date format
                
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
                except (ValueError, IndexError, KeyError):
                    pass  # Invalid date/time format in event data
            
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
                "wage_type": wage_type, # [NEW] Pass wage type for UI logic
                "is_registered": bool(latest), # [NEW] Flag for UI
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
