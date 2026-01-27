import flet as ft
from datetime import datetime, timedelta
from db import service_supabase
import asyncio
import os
import calendar as cal_mod
import re

def get_work_controls(page: ft.Page, navigate_to):
    print("Initializing Work View...", flush=True)
    
    # 0. Common Variables & Styles
    black_text = "black"
    grey_text = "grey"
    
    # 1. Weekly Schedule Summary Widget (Define First)
    weekly_summary_list = ft.Column(spacing=5)
    weekly_summary_container = ft.Container(
        content=ft.Column([
            ft.Text("근무 현황", weight="bold", size=16),
            weekly_summary_list
        ]),
        bgcolor="white",
        padding=15,
        border_radius=10,
        border=ft.border.all(1, "#EEEEEE")
    )
    
    # 2. Form Inputs
    reg_name = ft.TextField(label="이름", width=150, color=black_text, label_style=ft.TextStyle(color=grey_text))
    reg_type = ft.Dropdown(
        label="고용 형태", width=120,
        options=[ft.dropdown.Option("full", "정규직"), ft.dropdown.Option("part", "아르바이트")],
        value="part", color=black_text, label_style=ft.TextStyle(color=grey_text)
    )
    reg_wage_type = ft.Dropdown(
        label="급여 형태", width=100,
        options=[ft.dropdown.Option("hourly", "시급"), ft.dropdown.Option("monthly", "월급")],
        value="hourly", color=black_text, label_style=ft.TextStyle(color=grey_text)
    )
    reg_wage = ft.TextField(label="금액 (원)", width=120, value="10320", keyboard_type="number", color=black_text, label_style=ft.TextStyle(color=grey_text))
    reg_start_date = ft.TextField(label="근무 시작일", width=120, value=datetime.now().strftime("%Y-%m-%d"), color=black_text, label_style=ft.TextStyle(color=grey_text))
    
    # Days Schedule
    days_map = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}
    day_schedule = {}
    for day_idx in range(7):
        day_schedule[day_idx] = {
            "enabled": ft.Checkbox(label=days_map[day_idx], value=False),
            "start": ft.TextField(value="09:00", width=60, color=black_text, label_style=ft.TextStyle(color=grey_text), text_size=12),
            "end": ft.TextField(value="18:00", width=60, color=black_text, label_style=ft.TextStyle(color=grey_text), text_size=12)
        }
    
    # Schedule UI Components
    uniform_start = ft.TextField(label="시작", value="09:00", width=70, color=black_text, label_style=ft.TextStyle(color=grey_text))
    uniform_end = ft.TextField(label="종료", value="18:00", width=70, color=black_text, label_style=ft.TextStyle(color=grey_text))
    
    # Separate checkboxes for Uniform Mode to avoid parent conflict
    uniform_day_checks = [ft.Checkbox(label=days_map[i], value=False) for i in range(7)]

    uniform_ui = ft.Column([
        ft.Text("근무 시간:", size=12, color=black_text, weight="bold"),
        ft.Row([uniform_start, ft.Text("~"), uniform_end], spacing=5),
        ft.Text("근무 요일:", size=12, color=black_text, weight="bold"),
        ft.Row(uniform_day_checks, spacing=20, alignment=ft.MainAxisAlignment.START, wrap=False, scroll=ft.ScrollMode.AUTO)
    ])
    
    custom_ui = ft.Column([
        ft.Text("요일별 시간:", size=12, color=black_text, weight="bold"),
        ft.Row([
            ft.Container(
                content=ft.Row([
                    day_schedule[i]["enabled"],
                    day_schedule[i]["start"],
                    ft.Text("~", size=12),
                    day_schedule[i]["end"]
                ], spacing=3, alignment=ft.MainAxisAlignment.START),
                width=250,  # Fixed width for each day's control set
                padding=5,
                border=ft.border.all(1, "#EEEEEE"),
                border_radius=5
            )
            for i in range(7)
        ], wrap=True, spacing=10, run_spacing=10)
    ], visible=False)
    
    # Mode Buttons
    mode_btn_uniform = ft.Container(
        content=ft.Text("모든 요일 동일", size=12, color="white"),
        bgcolor="#1A237E", padding=8, border_radius=5, ink=True
    )
    mode_btn_custom = ft.Container(
        content=ft.Text("요일별 다르게", size=12, color="black"),
        border=ft.border.all(1, "grey"), padding=8, border_radius=5, ink=True
    )
    
    schedule_mode_state = {"value": "uniform"}
    
    def set_mode(mode):
        print(f"Set mode: {mode}", flush=True)
        schedule_mode_state["value"] = mode
        if mode == "uniform":
            uniform_ui.visible = True; custom_ui.visible = False
            mode_btn_uniform.bgcolor = "#1A237E"; mode_btn_uniform.content.color = "white"; mode_btn_uniform.border = None
            mode_btn_custom.bgcolor = None; mode_btn_custom.content.color = "black"; mode_btn_custom.border = ft.border.all(1, "grey")
        else:
            uniform_ui.visible = False; custom_ui.visible = True
            mode_btn_custom.bgcolor = "#1A237E"; mode_btn_custom.content.color = "white"; mode_btn_custom.border = None
            mode_btn_uniform.bgcolor = None; mode_btn_uniform.content.color = "black"; mode_btn_uniform.border = ft.border.all(1, "grey")
        page.update()
        
    mode_btn_uniform.on_click = lambda e: set_mode("uniform")
    mode_btn_custom.on_click = lambda e: set_mode("custom")
    
    # 3. Contract List
    contract_list = ft.Column(spacing=10)
    
    # Edit Dialog Function
    def open_edit_dialog(contract):
        print(f"Opening edit dialog for {contract.get('id')}", flush=True)
        
        # Mode Selection
        edit_mode = ft.RadioGroup(content=ft.Row([
            ft.Radio(value="correction", label="단순 정보 수정"),
            ft.Radio(value="change", label="근무/급여 조건 변경")
        ]), value="correction")
        
        # Effective Date (for change mode)
        effective_date = ft.TextField(label="변경 적용 약속일 (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d"), visible=False)
        
        def on_mode_change(e):
            effective_date.visible = (e.control.value == "change")
            page.update()
        
        edit_mode.on_change = on_mode_change

        e_name = ft.TextField(label="이름", value=contract.get('employee_name'))
        e_type = ft.Dropdown(options=[ft.dropdown.Option("full", "정규직"), ft.dropdown.Option("part", "아르바이트")], value=contract.get('employee_type'))
        e_wage_type = ft.Dropdown(options=[ft.dropdown.Option("hourly", "시급"), ft.dropdown.Option("monthly", "월급")], value=contract.get('wage_type', 'hourly'))
        
        wage_val = contract.get('hourly_wage') or contract.get('monthly_wage') or 0
        e_wage = ft.TextField(label="금액", value=str(wage_val))
        
        # Initialize checkboxes based on current work_days
        current_days = contract.get('work_days', [])
        # Create NEW checkboxes for the dialog
        e_day_checks = [ft.Checkbox(label=days_map[i], value=(i in current_days)) for i in range(7)]
        
        # Initialize time from existing schedule (take first day found or default)
        ws = contract.get('work_schedule', {})
        start_val = "09:00"
        end_val = "18:00"
        if ws:
            # ws keys are strings "0", "1", etc.
            first_k = next(iter(ws))
            start_val = ws[first_k].get('start', "09:00")
            end_val = ws[first_k].get('end', "18:00")
            
        e_start = ft.TextField(label="시작", value=start_val, width=80)
        e_end = ft.TextField(label="종료", value=end_val, width=80)
        
        async def save_edit(e=None):
             try:
                 print("Save edit triggered", flush=True)
                 new_schedule = {}
                 selected_indices = [i for i, chk in enumerate(e_day_checks) if chk.value]
                 
                 if not selected_indices:
                     page.open(ft.SnackBar(ft.Text("최소 하루 이상 선택해주세요."), bgcolor="red"))
                     page.update()
                     return
                     
                 for i in selected_indices:
                     new_schedule[str(i)] = {"start": e_start.value, "end": e_end.value}
                 
                 # Prepare Base Payload
                 payload = {
                     "employee_name": e_name.value,
                     "employee_type": e_type.value,
                     "wage_type": e_wage_type.value,
                     "hourly_wage": int(e_wage.value) if e_wage_type.value == 'hourly' else None,
                     "monthly_wage": int(e_wage.value) if e_wage_type.value == 'monthly' else None,
                     "work_days": selected_indices,
                     "work_schedule": new_schedule,
                     "daily_work_hours": contract.get('daily_work_hours', 8)
                 }

                 from services.auth_service import auth_service
                 from postgrest import SyncPostgrestClient
                 headers = auth_service.get_auth_headers()
                 if not headers: return
                 if "apikey" not in headers: headers["apikey"] = os.environ.get("SUPABASE_KEY")
                 
                 url = os.environ.get("SUPABASE_URL")
                 client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public", timeout=20)
                 
                 if edit_mode.value == "correction":
                     # SIMPLE UPDATE
                     await asyncio.to_thread(lambda: client.from_("labor_contracts").update(payload).eq("id", contract['id']).execute())
                     page.open(ft.SnackBar(ft.Text("정보가 수정되었습니다."), bgcolor="green"))
                     
                 else:
                     # CONDITION CHANGE (History Tracking)
                     eff_date_str = effective_date.value
                     try:
                         # Validate date
                         eff_dt = datetime.strptime(eff_date_str, "%Y-%m-%d")
                         # Prev end date = eff date - 1 day
                         prev_end = (eff_dt - timedelta(days=1)).strftime("%Y-%m-%d")
                         
                         # 1. Update Old Contract
                         await asyncio.to_thread(lambda: client.from_("labor_contracts").update({
                             "contract_end_date": prev_end
                         }).eq("id", contract['id']).execute())
                         
                         # 2. Insert New Contract
                         new_contract = payload.copy()
                         new_contract["user_id"] = contract["user_id"]
                         new_contract["contract_start_date"] = eff_date_str
                         new_contract["contract_end_date"] = None # Open-ended
                         
                         await asyncio.to_thread(lambda: client.from_("labor_contracts").insert(new_contract).execute())
                         page.open(ft.SnackBar(ft.Text("새로운 계약 조건이 적용되었습니다."), bgcolor="green"))
                         
                     except ValueError:
                         page.open(ft.SnackBar(ft.Text("날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)."), bgcolor="red"))
                         page.update()
                         return
                 
                 page.close(dlg)
                 page.update()
                 await load_contracts_async()
                 # await build_monthly_calendar()
                 
             except Exception as ex:
                 print(f"Edit Save Error: {ex}")
                 import traceback
                 traceback.print_exc()
                 page.open(ft.SnackBar(ft.Text(f"오류 발생: {ex}"), bgcolor="red"))
                 page.update()
        
        dlg = ft.AlertDialog(
            title=ft.Text("직원 정보 수정"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("수정 유형 선택:", size=12, color="grey"),
                    edit_mode,
                    effective_date,
                    ft.Divider(),
                    e_name, 
                    e_type, 
                    ft.Row([e_wage_type, e_wage]),
                    ft.Divider(),
                    ft.Text("근무 일정 (전체 적용)"),
                    ft.Row(e_day_checks, wrap=True),
                    ft.Row([e_start, ft.Text("~"), e_end])
                ], tight=True, scroll=ft.ScrollMode.AUTO),
                width=400, height=500
            ),
            actions=[
                ft.TextButton("저장", on_click=lambda e: page.run_task(save_edit)),
                ft.TextButton("취소", on_click=lambda e: page.close(dlg))
            ]
        )
        page.open(dlg)
        print("Dialog open command sent via page.open()", flush=True)

    def open_resign_dialog(contract, mode="resign"):
        # mode: "resign" or "restore"
        if mode == "resign":
            res_date = ft.TextField(label="퇴사 일자 (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d"))
            title_text = f"{contract.get('employee_name')} 퇴사 처리"
            desc_text = "입력하신 날짜를 기준으로 계약을 종료합니다. 정말 퇴사 처리하시겠습니까?"
            btn_text = "퇴사 처리"
            btn_color = "orange"
        else:
            res_date = None
            title_text = f"{contract.get('employee_name')} 복구"
            desc_text = "퇴사 처리를 취소하고 다시 근무 상태로 복구하시겠습니까?"
            btn_text = "근무 복구"
            btn_color = "blue"
        
        async def save_action(e=None):
            try:
                from services.auth_service import auth_service
                from postgrest import SyncPostgrestClient
                headers = auth_service.get_auth_headers()
                if not headers: return
                if "apikey" not in headers: headers["apikey"] = os.environ.get("SUPABASE_KEY")
                url = os.environ.get("SUPABASE_URL")
                client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public", timeout=20)

                new_val = res_date.value if mode == "resign" else None
                await asyncio.to_thread(lambda: client.from_("labor_contracts").update({"contract_end_date": new_val}).eq("id", contract['id']).execute())
                
                page.close(dlg)
                msg = f"{contract.get('employee_name')}님이 퇴사 처리되었습니다." if mode == "resign" else f"{contract.get('employee_name')}님이 복구되었습니다."
                page.open(ft.SnackBar(ft.Text(msg), bgcolor="orange" if mode=="resign" else "blue"))
                page.update()
                await load_contracts_async()
            except Exception as ex:
                page.open(ft.SnackBar(ft.Text(f"처리 오류: {ex}"), bgcolor="red"))
                page.update()

        content_list = [ft.Text(desc_text, size=12, color="grey")]
        if res_date: content_list.append(res_date)

        dlg = ft.AlertDialog(
            title=ft.Text(title_text),
            content=ft.Column(content_list, tight=True),
            actions=[
                ft.TextButton(btn_text, on_click=lambda e: page.run_task(save_action)),
                ft.TextButton("취소", on_click=lambda e: page.close(dlg))
            ]
        )
        page.open(dlg)
        page.update()

    # 4. Async Functions
    async def load_contracts_async():
        print("Loading contracts...", flush=True)
        user_id = page.session.get("user_id")
        if not user_id: return

        try:
            from services.auth_service import auth_service
            from postgrest import SyncPostgrestClient
            headers = auth_service.get_auth_headers()
            if not headers: return
            if "apikey" not in headers: headers["apikey"] = os.environ.get("SUPABASE_KEY")
            
            url = os.environ.get("SUPABASE_URL")
            client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public", timeout=20)
            
            # [Cleanup] Delete contracts resigned more than 30 days ago
            one_month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            await asyncio.to_thread(lambda: client.from_("labor_contracts").delete().lte("contract_end_date", one_month_ago).execute())

            res = await asyncio.to_thread(lambda: client.from_("labor_contracts").select("*").eq("user_id", user_id).order("created_at", desc=True).execute())
            contracts = res.data or []
            
            # Categories
            full_list = []
            part_list = []
            resigned_list = []

            # Group by Name to find latest/earliest
            grouped = {}
            for c in contracts:
                name = c.get('employee_name', 'Unknown')
                if name not in grouped: grouped[name] = []
                grouped[name].append(c)

            for name, history in grouped.items():
                latest = history[0]
                earliest = history[-1]
                
                # Check weekly hours
                ws = latest.get('work_schedule', {})
                weekly_hours = 0
                for day, times in ws.items():
                    try:
                        sh, sm = map(int, times['start'].split(':'))
                        eh, em = map(int, times['end'].split(':'))
                        duration = (eh + em/60) - (sh + sm/60)
                        if duration < 0: duration += 24
                        weekly_hours += duration
                    except: pass
                
                # If weekly_hours is 0, fallback
                if weekly_hours == 0:
                    weekly_hours = (latest.get('daily_work_hours') or 8) * len(latest.get('work_days', []))

                is_resigned = False
                if latest.get('contract_end_date'):
                    try:
                        ed = datetime.strptime(latest.get('contract_end_date'), "%Y-%m-%d")
                        if ed.date() <= datetime.now().date():
                            is_resigned = True
                    except: pass

                # Build Card
                original_start = earliest.get('contract_start_date')
                w_days = [days_map[d] for d in latest.get('work_days', []) if d in days_map]
                day_str = ",".join(w_days)
                
                status_chips = [
                    ft.Container(content=ft.Text("알바" if latest.get('employee_type')=='part' else "정규", size=10, color="white"), bgcolor="orange", padding=ft.padding.symmetric(horizontal=8, vertical=4), border_radius=5)
                ]
                if is_resigned:
                    status_chips.append(ft.Container(content=ft.Text("퇴사", size=10, color="white"), bgcolor="grey", padding=ft.padding.symmetric(horizontal=8, vertical=4), border_radius=5))

                main_info = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Row([
                                ft.Text(name, weight="bold", size=16, color="black" if not is_resigned else "grey"),
                                ft.Row(status_chips, spacing=5)
                            ], spacing=10),
                            ft.Row([
                                ft.IconButton(ft.Icons.EDIT, icon_color="blue", tooltip="조건 변경/수정", on_click=lambda e, c=latest: open_edit_dialog(c)),
                                ft.IconButton(
                                    ft.Icons.RESTORE if is_resigned else ft.Icons.LOGOUT, 
                                    icon_color="blue" if is_resigned else "orange", 
                                    tooltip="복구" if is_resigned else "퇴사 처리", 
                                    on_click=lambda e, c=latest, ir=is_resigned: open_resign_dialog(c, "restore" if ir else "resign")
                                ),
                                ft.IconButton(ft.Icons.DELETE, icon_color="red", tooltip="삭제", data=latest.get('id'), on_click=delete_contract_click)
                            ], spacing=0)
                        ], alignment="spaceBetween"),
                        ft.Text(f"최초 근무 시작: {original_start}", size=11, weight="bold", color="#1A237E"),
                        ft.Text(f"현재 급여: {latest.get('hourly_wage') or latest.get('monthly_wage'):,}원 ({latest.get('wage_type')})", size=12, color="grey"),
                        ft.Text(f"현재 일정: {day_str} (주 {weekly_hours:.1f}시간)", size=12, color="grey")
                    ]),
                    padding=15, bgcolor="white", border_radius=10, border=ft.border.all(1, "#EEEEEE")
                )

                if len(history) > 1:
                    history_items = []
                    for h in history[1:]:
                        h_days = [days_map[d] for d in h.get('work_days', []) if d in days_map]
                        history_items.append(
                            ft.Container(
                                content=ft.Row([
                                    ft.Text(f"~ {h.get('contract_end_date') or '?'}", size=11, color="grey"),
                                    ft.Text(f"{h.get('hourly_wage') or h.get('monthly_wage'):,}원", size=11),
                                    ft.Text(f"{','.join(h_days)}", size=11),
                                ], alignment="spaceBetween"),
                                padding=5, bgcolor="#FAFAFA"
                            )
                        )
                    item = ft.Column([
                        main_info,
                        ft.ExpansionTile(
                            title=ft.Text(f"과거 이력 ({len(history)-1}건)", size=12, color="grey"),
                            controls=history_items,
                            bgcolor="white", text_color="grey"
                        )
                    ], spacing=0)
                else:
                    item = main_info

                # Assign to category
                if is_resigned:
                    resigned_list.append(item)
                elif weekly_hours >= 15:
                    full_list.append(item)
                else:
                    part_list.append(item)

            contract_list.controls.clear()
            
            def add_section(title, icon, items, color):
                if not items: return
                contract_list.controls.append(
                    ft.Container(
                        content=ft.Row([ft.Icon(icon, color=color, size=16), ft.Text(title, weight="bold", size=14, color=color)]),
                        padding=ft.padding.only(top=10, bottom=5)
                    )
                )
                contract_list.controls.extend(items)

            add_section("정규 (주 15시간 이상)", ft.Icons.PEOPLE, full_list, "#1A237E")
            add_section("알바 (주 15시간 미만)", ft.Icons.PEOPLE_OUTLINE, part_list, "orange")
            add_section("퇴사 직원", ft.Icons.PERSON_OFF, resigned_list, "grey")

            # Update Weekly Summary
            await update_weekly_summary(contracts)
            
            page.update()
        except Exception as e:
            print(f"Load Contracts Error: {e}", flush=True)
            import traceback
            traceback.print_exc()

    async def update_weekly_summary(contracts):
        try:
            weekly_summary_list.controls.clear()
            
            # Filter active contracts
            active_contracts = []
            grouped = {}
            for c in contracts:
                name = c.get('employee_name', 'Unknown')
                if name not in grouped: grouped[name] = []
                grouped[name].append(c)
            
            for name, history in grouped.items():
                latest = history[0]
                if latest.get('contract_end_date'):
                    try:
                        ed = datetime.strptime(latest.get('contract_end_date'), "%Y-%m-%d")
                        if ed.date() <= datetime.now().date():
                            continue # Skip resigned
                    except: pass
                active_contracts.append(latest)

            # Build Day map
            # day_idx: [ "name(start-end)", ... ]
            day_users = {i: [] for i in range(7)}
            for c in active_contracts:
                ws = c.get('work_schedule', {})
                for day_str, times in ws.items():
                    d_idx = int(day_str)
                    name = c.get('employee_name')
                    start = times.get('start', '00:00')
                    end = times.get('end', '00:00')
                    day_users[d_idx].append(f"{name}({start}~{end})")

            for i in range(7):
                day_name = days_map[i]
                users_str = ", ".join(day_users[i]) if day_users[i] else "근무자 없음"
                
                weekly_summary_list.controls.append(
                    ft.Row([
                        ft.Text(f"{day_name}요일", weight="bold", size=13, width=50),
                        ft.Text(users_str, size=13, color="grey")
                    ], vertical_alignment="start")
                )
            page.update()
        except Exception as e:
            print(f"Weekly Summary Error: {e}")

    async def delete_contract_click(e):
        contract_id = e.control.data
        if not contract_id: return
        
        async def _delete():
            try:
                from services.auth_service import auth_service
                from postgrest import SyncPostgrestClient
                headers = auth_service.get_auth_headers()
                if not headers: return
                if "apikey" not in headers: headers["apikey"] = os.environ.get("SUPABASE_KEY")
                
                url = os.environ.get("SUPABASE_URL")
                client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public", timeout=20)
                
                await asyncio.to_thread(lambda: client.from_("labor_contracts").delete().eq("id", contract_id).execute())
                
                page.open(ft.SnackBar(ft.Text("삭제되었습니다."), bgcolor="green"))
                page.update()
                await load_contracts_async()
            except Exception as ex:
                print(f"Delete Error: {ex}")
                page.open(ft.SnackBar(ft.Text(f"삭제 오류: {ex}"), bgcolor="red"))
                page.update()
        page.run_task(_delete)

    def save_contract_click(e):
        print("Save button clicked", flush=True)
        async def _save():
            try:
                if not reg_name.value:
                    page.open(ft.SnackBar(ft.Text("이름을 입력해주세요."), bgcolor="red"))
                    page.update()
                    return
                
                user_id = page.session.get("user_id")
                if not user_id:
                    page.open(ft.SnackBar(ft.Text("로그인이 필요합니다."), bgcolor="red"))
                    page.update()
                    return

                work_schedule = {}
                if schedule_mode_state["value"] == "uniform":
                    for idx in range(7):
                        if uniform_day_checks[idx].value:
                            work_schedule[str(idx)] = {"start": uniform_start.value, "end": uniform_end.value}
                else:
                    for idx in range(7):
                        if day_schedule[idx]["enabled"].value:
                            work_schedule[str(idx)] = {
                                "start": day_schedule[idx]["start"].value,
                                "end": day_schedule[idx]["end"].value
                            }
                
                selected_days = [int(i) for i in work_schedule.keys()]
                if not selected_days:
                    page.open(ft.SnackBar(ft.Text("근무 요일을 최소 하나 이상 선택해주세요."), bgcolor="red"))
                    page.update()
                    return

                data = {
                    "user_id": user_id,
                    "employee_name": reg_name.value,
                    "employee_type": reg_type.value,
                    "wage_type": reg_wage_type.value,
                    "hourly_wage": int(reg_wage.value) if reg_wage_type.value=="hourly" else None,
                    "monthly_wage": int(reg_wage.value) if reg_wage_type.value=="monthly" else None,
                    "work_schedule": work_schedule,
                    "work_days": selected_days,
                    "daily_work_hours": 8,
                    "contract_start_date": reg_start_date.value
                }
                print(f"Saving data: {data}", flush=True)

                from services.auth_service import auth_service
                from postgrest import SyncPostgrestClient
                headers = auth_service.get_auth_headers()
                if not headers:
                    page.open(ft.SnackBar(ft.Text("인증 정보가 없습니다. 다시 로그인해주세요."), bgcolor="red"))
                    page.update()
                    return

                # [FIX] Add apikey to headers
                if "apikey" not in headers:
                    headers["apikey"] = os.environ.get("SUPABASE_KEY")
                url = os.environ.get("SUPABASE_URL")
                client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public", timeout=20)
                
                await asyncio.to_thread(lambda: client.from_("labor_contracts").insert(data).execute())
                
                page.open(ft.SnackBar(ft.Text("등록되었습니다."), bgcolor="green"))
                
                # Reset
                reg_name.value = ""
                # Reset
                reg_name.value = ""
                for idx in range(7): 
                    day_schedule[idx]["enabled"].value = False
                    uniform_day_checks[idx].value = False
                page.update()
                
                await load_contracts_async()
                
            except Exception as ex:
                print(f"Save Error: {ex}", flush=True)
                import traceback
                traceback.print_exc()
                page.open(ft.SnackBar(ft.Text(f"저장 오류: {str(ex)}"), bgcolor="red"))
                page.update()
        
        page.run_task(_save)

    # 5. Main Layouts
    contract_content = ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text("신규 직원 등록", weight="bold", size=16, color="black"),
                ft.Container(height=10),
                ft.Row([reg_name, reg_type]),
                ft.Row([reg_wage_type, reg_wage]),
                ft.Row([reg_start_date, ft.Text("부터 근무 시작", size=12, color="grey")], vertical_alignment="center"),
                ft.Text("근무 일정:", size=12, color="black", weight="bold"),
                ft.Row([mode_btn_uniform, mode_btn_custom], spacing=10),
                uniform_ui,
                custom_ui,
                ft.Container(height=10),
                ft.ElevatedButton("신규 등록", on_click=save_contract_click, width=300, bgcolor="#1A237E", color="white")
            ]),
            padding=20, bgcolor="white", border_radius=10, shadow=ft.BoxShadow(blur_radius=5, color="#05000000")
        ),
        ft.Divider(),
        ft.Text("나의 직원 리스트", weight="bold", color="black"),
        contract_list,
        ft.Text("요일별 근무 명단", weight="bold", size=16, color="black"),
        weekly_summary_container
    ], scroll=ft.ScrollMode.ALWAYS, expand=True)
    
    labor_content = ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text("2025 최저임금", size=20, weight="bold", color="#333333"),
                ft.Row([
                    ft.Text("10,320원", size=40, weight="bold", color="#2196F3"),
                    ft.Text("(전년 대비 +1.7%)", size=14, color="grey")
                ], alignment="center"),
                ft.Divider(),
                ft.Text("주휴수당이란?", weight="bold", size=16),
                ft.Text("1주 동안 규정된 근무일수를 다 채운 근로자에게 유급 주휴일을 주는 것.", size=12, color="grey"),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Column([
                        ft.Text("주휴수당 계산법", weight="bold", color="white"),
                        ft.Text("(1주 근로시간 / 40) × 8 × 시급", color="white", size=16),
                        ft.Text("* 주 15시간 이상 근무 시 적용", size=12, color="white70")
                    ]),
                    bgcolor="#2196F3", padding=20, border_radius=10, width=400
                )
            ]),
            padding=20, bgcolor="white", border_radius=10, shadow=ft.BoxShadow(blur_radius=5, color="#05000000")
        )
    ], scroll=ft.ScrollMode.AUTO)

    tax_content = ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text("일반 vs 간이 과세자", size=20, weight="bold", color="#333333"),
                ft.Container(height=10),
                 ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("구분")),
                        ft.DataColumn(ft.Text("일반과세자")),
                        ft.DataColumn(ft.Text("간이과세자")),
                    ],
                    rows=[
                        ft.DataRow(cells=[ft.DataCell(ft.Text("기준")), ft.DataCell(ft.Text("연 1.04억 이상")), ft.DataCell(ft.Text("연 1.04억 미만"))]),
                        ft.DataRow(cells=[ft.DataCell(ft.Text("세율")), ft.DataCell(ft.Text("10%")), ft.DataCell(ft.Text("1.5~4%"))]),
                        ft.DataRow(cells=[ft.DataCell(ft.Text("신고")), ft.DataCell(ft.Text("1월, 7월")), ft.DataCell(ft.Text("1월"))]),
                    ],
                    width=400,
                ),
                ft.Divider(),
                ft.Text("주요 세무 일정", weight="bold", size=16),
                ft.ListTile(leading=ft.Icon(ft.Icons.CALENDAR_MONTH, color="red"), title=ft.Text("1월 25일"), subtitle=ft.Text("부가세 확정 신고 (모두)")),
                ft.ListTile(leading=ft.Icon(ft.Icons.CALENDAR_MONTH, color="blue"), title=ft.Text("5월 31일"), subtitle=ft.Text("종합소득세 신고")),
               ft.ListTile(leading=ft.Icon(ft.Icons.CALENDAR_MONTH, color="orange"), title=ft.Text("7월 25일"), subtitle=ft.Text("부가세 확정 신고 (일반)")),
            ]),
            padding=20, bgcolor="white", border_radius=10, shadow=ft.BoxShadow(blur_radius=5, color="#05000000")
        )
    ], scroll=ft.ScrollMode.AUTO)

    # Payroll (Simplified)
    payroll_res_col = ft.Column()
    now_dt = datetime.now()
    dd_year = ft.Dropdown(options=[ft.dropdown.Option(str(y)) for y in range(2025, 2030)], value=str(now_dt.year), width=100)
    dd_month = ft.Dropdown(options=[ft.dropdown.Option(str(m)) for m in range(1, 13)], value=str(now_dt.month), width=80)

    def calc_payroll(e):
        async def _calc():
            try:
                user_id = page.session.get("user_id")
                if not user_id: 
                    payroll_res_col.controls = [ft.Text("로그인이 필요합니다.", color="red")]
                    page.update()
                    return
                
                y = int(dd_year.value)
                m = int(dd_month.value)
                payroll_res_col.controls = [ft.ProgressBar()]
                page.update()
                
                from services.auth_service import auth_service
                from postgrest import SyncPostgrestClient
                headers = auth_service.get_auth_headers()
                if not headers:
                    payroll_res_col.controls = [ft.Text("인증 정보가 없습니다.", color="red")]
                    page.update()
                    return

                # [FIX] Add apikey to headers
                if "apikey" not in headers:
                    headers["apikey"] = os.environ.get("SUPABASE_KEY")
                
                url = os.environ.get("SUPABASE_URL")
                client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public", timeout=20)
                
                res = await asyncio.to_thread(lambda: client.from_("labor_contracts").select("*").eq("user_id", user_id).execute())
                contracts = res.data or []
                
                # Fetch Overrides (Strictly filtered by user_id)
                start_iso = f"{y}-{m:02d}-01T00:00:00"
                last_day = cal_mod.monthrange(y, m)[1]
                end_iso = f"{y}-{m:02d}-{last_day}T23:59:59"
                o_res = await asyncio.to_thread(lambda: client.from_("calendar_events")
                                               .select("*")
                                               .eq("is_work_schedule", True)
                                               .eq("created_by", user_id)
                                               .gte("start_date", start_iso)
                                               .lte("start_date", end_iso)
                                               .execute())
                overrides = o_res.data or []
                
                # [Group by Name] Consolidate overrides and contracts
                eid_to_name = {c['id']: c.get('employee_name', 'Unknown').strip() for c in contracts}
                
                def parse_name(ev):
                    eid = ev.get('employee_id')
                    if eid and eid in eid_to_name: return eid_to_name[eid]
                    t = ev.get('title', '')
                    # Strictly require an emoji for non-linked entries to be counted as "Ledger" entries
                    if not any(em in t for em in ["🟢", "❌", "⭐", "🔥"]) and not eid:
                        return None
                    for emoji in ["🟢", "❌", "⭐", "🔥"]:
                        t = t.replace(emoji, '')
                    return t.split('(')[0].split('결근')[0].strip() or "Unknown"

                name_to_events = {}
                all_names = set(eid_to_name.values())
                for o in overrides:
                    nm = parse_name(o)
                    if not nm: continue # Skip ghost/legacy data
                    all_names.add(nm)
                    if nm not in name_to_events: name_to_events[nm] = []
                    name_to_events[nm].append(o)
                
                name_to_history = {}
                for c in contracts:
                    nm = c.get('employee_name', 'Unknown').strip()
                    if nm not in name_to_history: name_to_history[nm] = []
                    name_to_history[nm].append(c)

                std_items, act_items = [], []
                total_std, total_act = 0, 0
                has_incomplete = False
                days_in_month = cal_mod.monthrange(y, m)[1]

                for name in sorted(all_names):
                    history = name_to_history.get(name, [])
                    latest = None
                    if history:
                        history.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                        latest = history[0]

                    # Standard setup
                    std_pay, std_days = 0, 0
                    h_wage, m_wage = None, 0
                    wage_type = 'hourly'
                    daily_hours, work_days = 0, []

                    if latest:
                        # Resigned check
                        ed_str = latest.get('contract_end_date')
                        if ed_str:
                            try:
                                ed = datetime.strptime(ed_str, "%Y-%m-%d")
                                if ed.year < y or (ed.year == y and ed.month < m): continue
                            except: pass
                        
                        wage_type = latest.get('wage_type', 'hourly')
                        h_wage = latest.get('hourly_wage') or 9860
                        m_wage = latest.get('monthly_wage') or 0
                        daily_hours = latest.get('daily_work_hours', 8)
                        work_days = latest.get('work_days', [])
                        
                        for d in range(1, days_in_month + 1):
                            if datetime(y, m, d).weekday() in work_days: std_days += 1
                        
                        if wage_type == 'monthly': std_pay = m_wage
                        else: std_pay = std_days * daily_hours * h_wage
                        
                        total_std += std_pay
                        if std_days > 0:
                            std_items.append(
                                ft.Container(
                                    content=ft.Row([
                                        ft.Column([ft.Text(name, weight="bold", size=14), ft.Text(f"계약 스케줄 ({std_days}일)", size=10, color="grey")], spacing=2),
                                        ft.Text(f"{int(std_pay):,}원", weight="bold", size=14)
                                    ], alignment="spaceBetween"),
                                    padding=10, bgcolor="white", border_radius=8, border=ft.border.all(1, "#F0F0F0")
                                )
                            )

                    # Actual calculation
                    act_pay, act_hours, act_days = 0, 0, 0
                    override_wage = None
                    
                    # Track which days have overrides to avoid double-counting standard hours
                    override_days = set()
                    
                    for o in name_to_events.get(name, []):
                        # Use hourly_wage column from DB
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
                    
                    for d in range(1, days_in_month + 1):
                        if d not in override_days and datetime(y, m, d).weekday() in work_days:
                            act_hours += daily_hours
                            act_days += 1

                    if not latest:
                        h_wage = override_wage
                        wage_type = 'hourly'
                    elif override_wage: # Contract exists but event has override
                        h_wage = override_wage

                    if h_wage is None and wage_type == 'hourly':
                        act_pay = None # Unknown
                        if (act_hours > 0): has_incomplete = True
                    elif wage_type == 'monthly': 
                        act_pay = m_wage
                    else: 
                        act_pay = act_hours * h_wage
                    
                    if act_pay is not None: total_act += act_pay
                    if act_days > 0 or act_hours > 0:
                        diff_val = (act_pay - std_pay) if act_pay is not None else 0
                        diff_color = "red" if diff_val > 0 else "blue" if diff_val < 0 else "grey"
                        
                        pay_display = ft.Text(f"{int(act_pay):,}원", weight="bold", size=16, color="blue") if act_pay is not None else ft.Text("???원", weight="bold", size=16, color="red")
                        
                        # Inline Edit for Substitutes or Overrides
                        async def on_wage_submit(e, nm=name, custom_val=None):
                            try:
                                raw_val = custom_val if custom_val is not None else e.control.value
                                if not raw_val: return
                                val = float(str(raw_val).replace(',', '').strip())
                                
                                # Update all events for this name/month
                                target_ids = [o['id'] for o in name_to_events.get(nm, [])]
                                if target_ids:
                                    # Update hourly_wage column with audit tracking
                                    await asyncio.to_thread(lambda: client.from_("calendar_events").update({
                                        "hourly_wage": val,
                                        "wage_updated_at": datetime.now().isoformat()
                                    }).in_("id", target_ids).execute())
                                    
                                    page.open(ft.SnackBar(ft.Text(f"{nm}님 시급 {val:,}원으로 연동되었습니다."), bgcolor="green"))
                                    await _calc()
                                else:
                                    page.open(ft.SnackBar(ft.Text(f"{nm}님의 근무 기록을 찾을 수 없습니다."), bgcolor="orange"))
                            except Exception as ex:
                                print(f"Wage Update Error: {ex}")
                                page.open(ft.SnackBar(ft.Text(f"입력 오류: {ex}"), bgcolor="red"))

                        wage_input = ft.TextField(
                            label="시급", value=str(int(h_wage)) if h_wage else "", 
                            width=100, text_size=12, content_padding=5,
                            on_submit=lambda e, n=name: page.run_task(on_wage_submit, e, n),
                        )
                        
                        save_btn = ft.ElevatedButton(
                            text="입력",
                            color="white",
                            bgcolor="blue",
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5), padding=5),
                            on_click=lambda _, n=name, inp=wage_input: page.run_task(on_wage_submit, None, n, inp.value)
                        )

                        act_items.append(
                            ft.Container(
                                content=ft.Row([
                                    ft.Column([
                                        ft.Row([
                                            ft.Text(name, weight="bold", size=14),
                                            ft.Container(
                                                content=ft.Text(f"{'+' if diff_val>0 else ''}{int(diff_val):,}원", size=9, color="white", weight="bold"),
                                                bgcolor=diff_color, padding=ft.padding.symmetric(horizontal=5, vertical=2),
                                                border_radius=4, visible=(diff_val!=0 and act_pay is not None)
                                            ),
                                            ft.Row([wage_input, save_btn], spacing=5) if (not latest or h_wage is None) else ft.Container()
                                        ], spacing=5, vertical_alignment="center"),
                                        ft.Text(f"실제 근무 ({act_days}일, {act_hours:.1f}시간)", size=10, color="grey")
                                    ], spacing=2, expand=True),
                                    pay_display,
                                ], alignment="spaceBetween"),
                                padding=ft.padding.symmetric(horizontal=15, vertical=12),
                                bgcolor="#F8F9FF", border_radius=8, border=ft.border.all(1, "#E8EFFF")
                            )
                        )
                
                summary = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"{y}년 {m}월 정산 요약", size=14, color="white70"),
                            ft.Container(
                                content=ft.Text("최종 확정", size=10, color="white"),
                                bgcolor="blue", padding=ft.padding.symmetric(horizontal=8, vertical=4), border_radius=5
                            )
                        ], alignment="spaceBetween"),
                        ft.Row([
                            ft.Text("실제 총 지출", size=18, weight="bold", color="white"),
                            ft.Column([
                                ft.Text(f"{int(total_act):,}원" + (" + α" if has_incomplete else ""), size=24, weight="bold", color="white"),
                                ft.Text(f"표준 대비 {'+' if total_act-total_std>0 else ''}{int(total_act-total_std):,}원", size=11, color="white70")
                            ], horizontal_alignment="end")
                        ], alignment="spaceBetween")
                    ]),
                    padding=20, bgcolor="#1A237E", border_radius=12
                )
                
                # Build final output
                final_controls = [summary, ft.Divider(height=30, color="transparent")]
                
                # Section 1: Standard
                final_controls.append(ft.Text("1. 계약서상 인건비 (기준)", weight="bold", size=15, color="grey"))
                if not std_items:
                    final_controls.append(ft.Text("  기록 없음", size=12, color="grey"))
                else:
                    final_controls.extend(std_items)
                    final_controls.append(ft.Container(
                        content=ft.Row([ft.Text("표준 합계", size=12, color="grey"), ft.Text(f"{int(total_std):,}원", size=14, weight="bold")], alignment="spaceBetween"),
                        padding=ft.padding.only(right=10)
                    ))

                final_controls.append(ft.Divider(height=40, color="#EEEEEE"))

                # Section 2: Actual
                final_controls.append(ft.Text("2. 실제 인건비 (정산)", weight="bold", size=16, color="blue"))
                if not act_items:
                    final_controls.append(ft.Text("  기록 없음", size=12, color="grey"))
                else:
                    final_controls.extend(act_items)
                    final_controls.append(ft.Container(
                        content=ft.Row([ft.Text("실제 합계", size=13, color="blue"), ft.Text(f"{int(total_act):,}원", size=18, weight="bold", color="blue")], alignment="spaceBetween"),
                        padding=ft.padding.only(right=10)
                    ))

                payroll_res_col.controls = final_controls
                page.update()
                
            except Exception as ex:
                print(f"Payroll Error: {ex}")
                payroll_res_col.controls = [ft.Text(f"오류: {ex}", color="red")]
                page.update()
        page.run_task(_calc)

    payroll_content = ft.Column([
        ft.Text("급여 정산", weight="bold", size=18),
        ft.Text("* 상단: 계약 기준 예상 / 하단: 캘린더 실제 기록 기준", size=12, color="grey"),
        ft.Row([dd_year, ft.Text("년"), dd_month, ft.Text("월"), ft.ElevatedButton("조회", on_click=calc_payroll)], vertical_alignment="center"),
        ft.Divider(),
        payroll_res_col
    ], scroll=ft.ScrollMode.AUTO)

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        height=45,
        tabs=[
            ft.Tab(text="계약 관리", icon=ft.Icons.FOLDER_SHARED),
            ft.Tab(text="급여 정산", icon=ft.Icons.MONETIZATION_ON),
            ft.Tab(text="노무 정보", icon=ft.Icons.WORK),
            ft.Tab(text="세무 가이드", icon=ft.Icons.ATTACH_MONEY),
        ]
    )

    body = ft.Container(content=contract_content, expand=True)

    def on_tab_change(e):
        idx = e.control.selected_index
        if idx == 0:
            body.content = contract_content
            page.run_task(load_contracts_async)
        elif idx == 1:
            body.content = payroll_content
            # No async task needed immediately for payroll, it's manual
        elif idx == 2:
            body.content = labor_content
        elif idx == 3:
            body.content = tax_content
        page.update()

    tabs.on_change = on_tab_change

    header = ft.Container(
        content=ft.Row([
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to("home")), 
                ft.Text("직원 관리", size=20, weight="bold", color="black")
            ]), 
        ], alignment="spaceBetween"), 
        padding=10, 
        border=ft.border.only(bottom=ft.border.BorderSide(1, "#EEEEEE"))
    )

    # [FIX] Initial Data Load
    page.run_task(load_contracts_async)

    return [
        ft.Column([
            ft.Container(header, bgcolor="white"),
            ft.Container(tabs, height=45),
            ft.Container(body, expand=True, padding=10)
        ], spacing=0, expand=True)
    ]
