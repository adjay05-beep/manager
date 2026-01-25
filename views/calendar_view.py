import flet as ft
from datetime import datetime, time
import calendar
import urllib.parse
from services import calendar_service
from services.chat_service import get_storage_signed_url, get_public_url, upload_file_server_side

def get_calendar_controls(page: ft.Page, navigate_to):
    now = datetime.now()
    view_state = {"year": now.year, "month": now.month, "today": now.day, "events": []}
    
    month_label = ft.Text("", size=18, weight="bold", color="#333333")
    grid = ft.GridView(expand=True, runs_count=7, spacing=0, run_spacing=0)

    def load():
        page.run_task(load_async)
        
    async def load_async():
        try:
            view_state["events"] = await calendar_service.get_all_events()
            build()
        except Exception as e: 
            page.snack_bar = ft.SnackBar(ft.Text(f"일정 로드 실패: {e}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()
            build()

    def build():
        month_label.value = f"{view_state['year']}년 {view_state['month']}월"
        grid.controls = []
        days = ["일", "월", "화", "수", "목", "금", "토"]
        for i, d in enumerate(days):
            color = "#FF5252" if i == 0 else "#448AFF" if i == 6 else "#666666"
            grid.controls.append(ft.Container(content=ft.Text(d, size=11, weight="bold", color=color), alignment=ft.Alignment(0, 0), height=30, border=ft.border.only(bottom=ft.border.BorderSide(1, "#EEEEEE"))))
        
        cal_obj = calendar.Calendar(firstweekday=6)
        month_days = cal_obj.monthdayscalendar(view_state["year"], view_state["month"])
        today_f = datetime.now()
        
        for week in month_days:
            for i, day in enumerate(week):
                if day == 0:
                    grid.controls.append(ft.Container(border=ft.border.all(0.5, "#F9F9F9")))
                else:
                    is_t = (day == today_f.day and view_state['month'] == today_f.month and view_state['year'] == today_f.year)
                    d_str = f"{view_state['year']}-{view_state['month']:02d}-{day:02d}"
                    evs = [e for e in view_state["events"] if e['start_date'].startswith(d_str)]
                    
                    date_color = "#FF5252" if i == 0 else "#448AFF" if i == 6 else "black"
                    date_box = ft.Container(
                        content=ft.Text(str(day), size=12, weight="bold", color="white" if is_t else date_color),
                        bgcolor="black" if is_t else None, width=24, height=24, border_radius=12, alignment=ft.Alignment(0, 0)
                    )
                    ev_stack = ft.Column(spacing=2, tight=True)
                    for ev in evs:
                        prof = ev.get('profiles')
                        if isinstance(prof, list) and prof: prof = prof[0]
                        un = prof.get('full_name', '익명') if prof else '익명'
                        
                        display_text = f"[{un[0]}] {ev['title']}"
                        ev_stack.controls.append(
                            ft.Container(content=ft.Text(display_text, size=8, color="white", no_wrap=True), bgcolor=ev.get('color', '#1DDB16'), padding=2, border_radius=3)
                        )
                    
                    def make_day_click(d_val):
                        return lambda e: show_day_details_dialog(d_val)

                    grid.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Container(date_box, padding=4), 
                                ft.Container(ev_stack, padding=1, height=60, clip_behavior=ft.ClipBehavior.HARD_EDGE)
                            ], spacing=2, tight=True),
                            border=ft.border.all(0.5, "#EEEEEE"), 
                            bgcolor="white", 
                            height=100,
                            ink=True, 
                            on_click=make_day_click(day)
                        )
                    )
        page.update()

    def show_day_details_dialog(day):
        d_str = f"{view_state['year']}-{view_state['month']:02d}-{day:02d}"
        evs = [e for e in view_state["events"] if e['start_date'].startswith(d_str)]
        
        detail_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, height=300)
        
        dlg_day = None

        if not evs:
            detail_list.controls.append(ft.Container(content=ft.Text("등록된 일정이 없습니다.", color="grey", text_align="center"), alignment=ft.alignment.center, padding=20))
        else:
            for ev in evs:
                prof = ev.get('profiles')
                if isinstance(prof, list) and prof: prof = prof[0]
                un = prof.get('full_name', '익명') if prof else '익명'
                
                def make_go_detail(event_data):
                    return lambda e: open_event_detail_dialog(event_data, day)

                detail_list.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.CIRCLE, color=ev.get('color', '#1DDB16'), size=20),
                        title=ft.Text(ev['title'], weight="bold", color="black"),
                        subtitle=ft.Text(f"{un}", size=12, color="grey"),
                        bgcolor="white",
                        on_click=make_go_detail(ev),
                        shape=ft.RoundedRectangleBorder(radius=8),
                    )
                )

        def go_editor(e):
             dlg_day.open = False
             page.update()
             open_event_editor_dialog(day)

        dlg_day = ft.AlertDialog(
            title=ft.Text(f"{view_state['month']}월 {day}일"),
            content=ft.Container(width=300, content=detail_list),
            actions=[
                ft.TextButton("닫기", on_click=lambda _: page.close(dlg_day)),
                ft.ElevatedButton("일정 추가", on_click=go_editor, bgcolor="#00C73C", color="white")
            ]
        )
        page.open(dlg_day)

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

        dlg_det = ft.AlertDialog(
            title=ft.Text("상세 정보"),
            content=ft.Container(width=300, content=content),
            actions=[
                ft.IconButton(ft.Icons.DELETE, icon_color="red", on_click=delete_ev),
                ft.TextButton("닫기", on_click=lambda _: page.close(dlg_det))
            ]
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
                "user_id": "00000000-0000-0000-0000-000000000001"
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
                ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda _: change_m(-1)), 
                month_label, 
                ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda _: change_m(1))
            ], spacing=10), 
            ft.Row([
                ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: load()), 
                ft.TextButton("나가기", icon=ft.Icons.LOGOUT, on_click=lambda _: navigate_to("home"))
            ])
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    )
    load()
    return [ft.Column([header, ft.Container(grid, expand=True, padding=10)], expand=True, spacing=0)]
