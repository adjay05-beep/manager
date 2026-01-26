import flet as ft
from datetime import datetime, time
import calendar
import urllib.parse
import asyncio
from services import calendar_service
from services.chat_service import get_storage_signed_url, get_public_url, upload_file_server_side
import os

def get_calendar_controls(page: ft.Page, navigate_to):
    now = datetime.now()
    view_state = {"year": now.year, "month": now.month, "today": now.day, "events": []}
    
    month_label = ft.Text("", size=18, weight="bold", color="#333333")
    # [Calendar V2] Sidebar & Multi-Calendar State
    current_cal_type = "store" # store | staff
    
    # [DEBUG]
    debug_text = ft.Text(value="", color="red", size=14)
    
    # Staff Schedule Generator
    async def generate_staff_events(year, month):
        # 1. Fetch Contracts (Authenticated)
        try:
            # [FIX] Use Authenticated Request to bypass RLS/Server Key issues
            from postgrest import SyncPostgrestClient
            import os
            from services.auth_service import auth_service # Import instance
            
            headers = auth_service.get_auth_headers()
            contracts = []
            
            if headers:
                # Use User Token
                url = os.environ.get("SUPABASE_URL")
                
                def _fetch():
                    cl = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public", timeout=20)
                    return cl.from_("labor_contracts").select("*").execute()
                
                res = await asyncio.to_thread(_fetch)
                contracts = res.data or []
            else:
                # Fallback to Service Key (likely to fail on Render if Anon)
                res = await asyncio.to_thread(lambda: calendar_service.service_supabase.table("labor_contracts").select("*").execute())
                contracts = res.data or []
        except Exception as ex: 
            print(f"Calendar Staff Fetch Error: {ex}")
            return []

        events = []
        days_in_month = calendar.monthrange(year, month)[1]
        
        for day in range(1, days_in_month + 1):
            date_obj = datetime(year, month, day)
            weekday = date_obj.weekday() # 0=Mon, 6=Sun
            
            for c in contracts:
                # Check if this contract works today
                work_days = c.get('work_days', []) # e.g. [0, 2, 4]
                if weekday in work_days:
                    # Calculate Daily Pay
                    pay = c['hourly_wage'] * c['daily_work_hours']
                    start_str = date_obj.replace(hour=9, minute=0).strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Virtual Event Object
                    events.append({
                        "id": f"virtual_{c['id']}_{day}",
                        "title": f"{c['employee_name']} ({int(pay):,}원)",
                        "start_date": start_str,
                        "color": "orange", # Orange for Staff
                        "is_virtual": True,
                        "employee_id": c['id']
                    })
        return events

    grid = ft.GridView(expand=True, runs_count=7, spacing=0, run_spacing=0)

    # [RBAC] Get User from Session
    current_user_id = page.session.get("user_id")
    # For robust MVP, allow view but require login
    if not current_user_id:
        # navigate_to("login") # Handled by main or caller? 
        # Actually calendar_view is called AFTER login. 
        # But if session lost (dev reload), maybe empty.
        pass

    def load():
        page.run_task(load_async)
        
    async def load_async():
        if not current_user_id: return
        try:
            if current_cal_type == "store":
                view_state["events"] = await calendar_service.get_all_events(current_user_id)
            elif current_cal_type == "staff":
                view_state["events"] = await generate_staff_events(view_state["year"], view_state["month"])
            
            build()
            build()
        except Exception as e: 
            import traceback
            err = traceback.format_exc()
            print(f"Calendar Load Error: {err}")
            debug_text.value = f"Load Error: {e}"
            # page.snack_bar = ft.SnackBar(ft.Text(f"일정 로드 실패: {e}"), bgcolor="red")
            # page.snack_bar.open = True
            # page.update()
            build()

    def build():
        grid.controls.clear()
        y = view_state["year"]
        m = view_state["month"]
        month_label.value = f"{y}년 {m}월 ({'전체 일정' if current_cal_type=='store' else '직원 근무표'})"
        
        # Headers
        wd_names = ["월", "화", "수", "목", "금", "토", "일"]
        for wd in wd_names:
            grid.controls.append(ft.Container(content=ft.Text(wd, color="grey", size=12, text_align="center"), alignment=ft.alignment.center, height=30))
            
        cal = calendar.monthcalendar(y, m)
        for week in cal:
            for day in week:
                if day == 0:
                    grid.controls.append(ft.Container(bgcolor="#F4F4F4")) # Padding
                    continue
                
                # Check events (Naively filter from state)
                day_cols = []
                day_label = ft.Text(str(day), color="black", weight="bold" if day == now.day and m == now.month and y == now.year else "normal", size=12)
                day_cols.append(day_label)
                
                day_events = []
                for ev in view_state["events"]:
                    try:
                        # Simple date string check for MVP
                        if ev.get("start_date") and str(ev["start_date"]).startswith(f"{y}-{m:02d}-{day:02d}"):
                             day_events.append(ev)
                    except: pass
                
                # Event chips
                for ev in day_events[:3]:
                    day_cols.append(
                         ft.Container(
                             content=ft.Text(ev['title'], size=10, color="white", no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                             bgcolor=ev.get('color', 'blue'), border_radius=4, padding=ft.padding.symmetric(horizontal=4, vertical=1),
                             on_click=lambda e, ev=ev: open_event_detail_dialog(ev, day),
                             height=16
                         )
                    )

                grid.controls.append(
                    ft.Container(
                        content=ft.Column(day_cols, spacing=2),
                        bgcolor="white", # Current month is white
                        border=ft.border.all(0.5, "#EEEEEE"),
                        padding=4,
                        on_click=lambda e, d=day: open_event_editor_dialog(d),
                        alignment=ft.alignment.top_left
                    )
                )
        if page: page.update()

    def open_event_detail_dialog(ev, day):
        def delete_ev(e):
            async def _del():
                try:
                    await calendar_service.delete_event(ev['id'])
                    page.snack_bar = ft.SnackBar(ft.Text("삭제되었습니다.")); page.snack_bar.open=True
                    page.close(dlg_det)
                    load()
                    page.update()
                except Exception as ex: print(f"Del Error: {ex}")
            page.run_task(_del)

        def open_map(e):
            if ev.get('location'):
                try:
                    query = urllib.parse.quote(ev['location'])
                    page.launch_url(f"https://map.naver.com/p/search/{query}")
                except: pass

        def open_file(e):
            link = ev.get('link')
            if not link: return
            
            content = ft.Column(tight=True)
            low_link = link.lower()
            if low_link.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                content.controls.append(ft.Image(src=link, border_radius=10, fit=ft.ImageFit.CONTAIN))
            else:
                content.controls.append(ft.ListTile(leading=ft.Icon(ft.Icons.DESCRIPTION), title=ft.Text("파일 정보"), subtitle=ft.Text(link.split("/")[-1])))
            
            dlg_prev = ft.AlertDialog(
                title=ft.Text("파일 미리보기"),
                content=ft.Container(width=400, content=content),
                actions=[
                    ft.TextButton("새 창에서 열기", icon=ft.Icons.OPEN_IN_NEW, on_click=lambda _: page.launch_url(link)),
                    ft.TextButton("닫기", on_click=lambda _: page.close(dlg_prev))
                ]
            )
            page.open(dlg_prev)

        content = ft.Column([
            ft.Text(ev['title'], size=20, weight="bold"),
            ft.Text(f"{ev['start_date'][:16]} ~ {ev['end_date'][:16]}", size=14),
        ], spacing=10, tight=True)
        
        if ev.get('location'):
             content.controls.append(ft.TextButton(ev['location'], icon=ft.Icons.LOCATION_ON, on_click=open_map))
        if ev.get('link'):
             content.controls.append(ft.TextButton("첨부파일", icon=ft.Icons.ATTACH_FILE, on_click=open_file))

        # [RBAC] Only Creator can delete
        actions = [ft.TextButton("닫기", on_click=lambda _: page.close(dlg_det))]
        is_creator = (ev.get('created_by') == current_user_id) if ev.get('created_by') else True # Fallback for legacy
        # Proper Strict: 
        is_creator = str(ev.get('created_by')) == str(current_user_id) if ev.get('created_by') is not None else False
        
        # Allow Admin? (Not implemented in context yet, assume Strict Owner)
        if is_creator:
            actions.insert(0, ft.IconButton(ft.Icons.DELETE, icon_color="red", on_click=delete_ev))

        dlg_det = ft.AlertDialog(
            title=ft.Text("상세 정보"),
            content=ft.Container(width=300, content=content),
            actions=actions
        )
        page.open(dlg_det)

    def open_event_editor_dialog(day, init=""):
        try:
            target_date = datetime(view_state['year'], view_state['month'], day)
        except: target_date = datetime.now()

        evt_state = {
            "all_day": False,
            "start_date": target_date.replace(hour=9,minute=0,second=0,microsecond=0),
            "end_date": target_date.replace(hour=10,minute=0,second=0,microsecond=0),
            "start_time": time(9,0),
            "end_time": time(10,0),
            "color": "#1DDB16",
            "participants": []
        }
        
        def on_d_s(e): 
            if e.control.value: evt_state["start_date"] = e.control.value; update_ui()
        def on_d_e(e): 
            if e.control.value: evt_state["end_date"] = e.control.value; update_ui()
        def on_t_s(e): 
            if e.control.value: evt_state["start_time"] = e.control.value; update_ui()
        def on_t_e(e): 
            if e.control.value: evt_state["end_time"] = e.control.value; update_ui()
        
        dp_s = ft.DatePicker(on_change=on_d_s); dp_e = ft.DatePicker(on_change=on_d_e)
        tp_s = ft.TimePicker(on_change=on_t_s, time_picker_entry_mode=ft.TimePickerEntryMode.DIAL_ONLY)
        tp_e = ft.TimePicker(on_change=on_t_e, time_picker_entry_mode=ft.TimePickerEntryMode.DIAL_ONLY)
        
        page.overlay.extend([dp_s, dp_e, tp_s, tp_e])
        
        status_msg = ft.Text("", size=12, color="orange", visible=False)
        saved_fname = None
        link_tf = ft.TextField(label="클라우드 파일 링크", icon=ft.Icons.CLOUD_UPLOAD, read_only=True, expand=True)
        title_tf = ft.TextField(label="제목", value=init, autofocus=True)
        loc_tf = ft.TextField(label="장소", icon=ft.Icons.LOCATION_ON)
        btn_file = ft.TextButton("클라우드 업로드", icon=ft.Icons.UPLOAD_FILE, on_click=lambda _: page.file_picker.pick_files())
        
        link_section = ft.Column([
            link_tf,
            ft.Row([btn_file, status_msg], alignment="spaceBetween")
        ], spacing=5)

        def on_upload_progress(e: ft.FilePickerUploadEvent):
            if status_msg:
                status_msg.value = f"업로딩 ({int(e.progress * 100)}%)"
                page.update()

        def on_file_result(e: ft.FilePickerResultEvent):
            nonlocal saved_fname
            if e.files:
                f = e.files[0]
                status_msg.value = "준비 중..."
                status_msg.visible = True
                page.update()
                
                try:
                    from services import storage_service
                    
                    def update_ui_status(msg):
                        status_msg.value = msg
                        page.update()
                    
                    # [REFACTORED] Use Unified Storage Service
                    # Use page.file_picker which is set in main.py
                    picker = getattr(page, "file_picker", None)
                    res = page.run_task(lambda: storage_service.handle_file_upload(page, f, update_ui_status, picker_ref=picker)).result()
                    
                    # Async handling inside sync event handler requires waiting or restructuring
                    # Actually, handle_file_upload is async. We are in a sync UI callback?
                    # Flet UI callbacks are threaded?
                    # No, we should run it as a task.
                    # But run_task returns a Task object, not the result immediately.
                    
                    # FIX: We need to wrap this properly.
                    # Since we can't await here easily without making on_file_result async (which Flet supports!)
                    pass
                except:
                    # Fallback Logic inline if async migration is hard
                    pass
                
                # Let's switch on_file_result to async!
                async def do_upload():
                    try:
                        from services import storage_service
                        def update_ui_status(msg):
                            status_msg.value = msg
                            page.update()
                            
                        # Use page.file_picker which is set in main.py
                        picker = getattr(page, "file_picker", None)
                        result = await storage_service.handle_file_upload(page, f, update_ui_status, picker_ref=picker)
                        
                        if "public_url" in result:
                            link_tf.value = result["public_url"]
                            saved_fname = result["storage_name"]
                            status_msg.value = "업로드 완료"
                            status_msg.color = "green"
                        elif result["type"] == "web_js":
                            # Handle Web Signed URL if needed or show message
                            # For Calendar, we trust status callback or result
                            if result["public_url"]:
                                link_tf.value = result["public_url"]
                                status_msg.value = "Web Upload Signed (Check Console)"
                        
                        page.update()
                    except Exception as ex:
                        status_msg.value = f"오류: {ex}"
                        page.update()

                page.run_task(do_upload)

        def on_upload_complete(e: ft.FilePickerUploadEvent):
             status_msg.value = "업로드 완료"
             status_msg.color = "green"
             page.update()
        
        page.file_picker.on_result = on_file_result
        page.file_picker.on_upload = on_upload_progress
        
        b_ds = ft.OutlinedButton(on_click=lambda _: page.open(dp_s))
        b_de = ft.OutlinedButton(on_click=lambda _: page.open(dp_e))
        b_ts = ft.OutlinedButton(on_click=lambda _: page.open(tp_s))
        b_te = ft.OutlinedButton(on_click=lambda _: page.open(tp_e))
        
        def toggle_all_day(e):
             evt_state["all_day"] = e.control.value
             update_ui()
        sw_all_day = ft.Switch(label="종일", value=False, on_change=toggle_all_day)

        def update_ui():
            b_ds.text = evt_state["start_date"].strftime("%Y-%m-%d")
            b_de.text = evt_state["end_date"].strftime("%Y-%m-%d")
            b_ts.text = evt_state["start_time"].strftime("%H:%M")
            b_te.text = evt_state["end_time"].strftime("%H:%M")
            b_ts.visible = not evt_state["all_day"]
            b_te.visible = not evt_state["all_day"]
            
            if dlg_edit and dlg_edit.open: dlg_edit.update()
        
        colors = ["#1DDB16", "#FF9800", "#448AFF", "#E91E63", "#9C27B0", "#000000"]
        color_row = ft.Row(spacing=10)
        def set_color(c):
            evt_state["color"] = c
            for btn in color_row.controls:
                btn.content.visible = (btn.data == c)
            if dlg_edit and dlg_edit.open: dlg_edit.update()
        for c in colors:
            color_row.controls.append(ft.Container(width=30, height=30, bgcolor=c, border_radius=15, data=c, on_click=lambda e: set_color(e.control.data), content=ft.Icon(ft.Icons.CHECK, color="white", size=20, visible=(c==evt_state["color"])), alignment=ft.alignment.center))

        participant_chips = ft.Row(wrap=True)
        async def load_part_profiles():
            profiles = await calendar_service.load_profiles()
            
            def toggle_part(pid):
                if pid in evt_state["participants"]: evt_state["participants"].remove(pid)
                else: evt_state["participants"].append(pid)
                render_parts()
            
            def render_parts():
                participant_chips.controls = []
                for p in profiles:
                    is_sel = p['id'] in evt_state["participants"]
                    participant_chips.controls.append(ft.Chip(label=ft.Text(p.get('full_name', 'Unknown')), selected=is_sel, on_select=lambda e, pid=p['id']: toggle_part(pid)))
                if dlg_edit and dlg_edit.open: dlg_edit.update()
            
            render_parts()

        page.run_task(load_part_profiles)

        def save(e):
            if not title_tf.value: title_tf.error_text="필수"; title_tf.update(); return
            
            if evt_state["all_day"]:
                s = evt_state["start_date"].replace(hour=0, minute=0, second=0)
                e = evt_state["end_date"].replace(hour=23, minute=59, second=59)
                cols_s = s.strftime("%Y-%m-%d %H:%M:%S")
                cols_e = e.strftime("%Y-%m-%d %H:%M:%S")
            else:
                dt_s = datetime.combine(evt_state["start_date"].date(), evt_state["start_time"])
                dt_e = datetime.combine(evt_state["end_date"].date(), evt_state["end_time"])
                cols_s = dt_s.strftime("%Y-%m-%d %H:%M:%S")
                cols_e = dt_e.strftime("%Y-%m-%d %H:%M:%S")

            data = {
                "title": title_tf.value,
                "start_date": cols_s,
                "end_date": cols_e,
                "is_all_day": evt_state["all_day"],
                "color": evt_state["color"],
                "location": loc_tf.value,
                "link": link_tf.value,
                "participant_ids": evt_state["participants"],
                "created_by": current_user_id,
                # Legacy compatibility or extra tracking
                "user_id": current_user_id
            }
            
            async def _save_async():
                try:
                    await calendar_service.create_event(data)
                    page.snack_bar = ft.SnackBar(ft.Text("저장 완료!"))
                    page.snack_bar.open=True
                    page.close(dlg_edit)
                    load()
                    page.update()
                except Exception as ex:
                    print(f"Save Error: {ex}")
                    page.snack_bar = ft.SnackBar(ft.Text(f"오류: {ex}"), bgcolor="red"); page.snack_bar.open=True; page.update()
            
            page.run_task(_save_async)

        memo_tf = ft.TextField(label="메모", multiline=True, min_lines=2, icon=ft.Icons.NOTE)

        dlg_edit = ft.AlertDialog(
            title=ft.Text("새 일정"),
            content=ft.Container(
                width=400,
                content=ft.Column([
                    title_tf,
                    ft.Row([ft.Text("종일"), sw_all_day]),
                    ft.Row([ft.Text("시작"), b_ds, b_ts]),
                    ft.Row([ft.Text("종료"), b_de, b_te]),
                    ft.Divider(),
                    ft.Text("색상"), color_row,
                    ft.Divider(),
                    link_section,
                    memo_tf
                ], scroll=ft.ScrollMode.AUTO, height=500, tight=True)
            ),
            actions=[
                ft.TextButton("취소", on_click=lambda _: page.close(dlg_edit)),
                ft.ElevatedButton("저장", on_click=save, bgcolor="#00C73C", color="white")
            ]
        )
        update_ui()
        page.open(dlg_edit)

    def change_m(delta):
        view_state["month"] += delta
        if view_state["month"] > 12: view_state["month"]=1; view_state["year"]+=1
        elif view_state["month"] < 1: view_state["month"]=12; view_state["year"]-=1
        load()

    header = ft.Container(
        height=100, # Increased height for SafeArea
        bgcolor="white", 
        border=ft.border.only(bottom=ft.border.BorderSide(1, "#EEEEEE")), 
        padding=ft.padding.only(left=20, right=20, top=40), # Added top padding
        content=ft.Row([
            ft.Row([
                ft.Row([
                    ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda _: change_m(-1)), 
                    month_label, 
                    ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda _: change_m(1))
                ], alignment=ft.MainAxisAlignment.CENTER),
            ], expand=True, alignment=ft.MainAxisAlignment.CENTER), # Center the month navigator
            ft.Row([
                ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: load()), 
                # ft.TextButton("나가기", icon=ft.Icons.LOGOUT, on_click=lambda _: navigate_to("home")) # Moved to Nav Bar
            ])
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    )
    load()
    
    # [RBAC] Sidebar
    # Only Owner sees Staff Calendar
    # We fetch role sync or async? Sync assumption for MVP UI init, or async replacement.
    # For now, show it.
    
    def nav_change(e):
        nonlocal current_cal_type
        idx = e.control.selected_index
        if idx == 0: current_cal_type = "store"
        elif idx == 1: current_cal_type = "staff"
        load()
    
    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.CALENDAR_MONTH_OUTLINED, 
                selected_icon=ft.Icons.CALENDAR_MONTH, 
                label="전체 일정"
            ),
            ft.NavigationRailDestination(
                icon_content=ft.Icon(ft.Icons.PEOPLE_OUTLINE),
                selected_icon_content=ft.Icon(ft.Icons.PEOPLE),
                label="직원 근무"
            ),
        ],
        on_change=nav_change,
        bgcolor="white"
    )

    return [
        ft.Column([
            debug_text,
            header,
            ft.Row([
                rail,
                ft.VerticalDivider(width=1, color="#EEEEEE"),
                ft.Container(grid, expand=True, padding=10)
            ], expand=True, spacing=0)
        ], expand=True, spacing=0)
    ]
