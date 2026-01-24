import flet as ft
import datetime
import calendar
import tempfile
import os
import threading
from db import supabase
from voice_service import transcribe_audio

# --- [4] 채팅 화면 (Jandi Style) ---
def get_chat_controls(page: ft.Page, navigate_to):
    state = {"current_topic_id": None}
    topic_list_view = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=5)
    message_list_view = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=15)
    
    msg_input = ft.TextField(
        hint_text="메시지 입력...", 
        expand=True, 
        border_radius=10, 
        bgcolor="white", 
        border_color="#E0E0E0",
        on_submit=lambda e: send_message()
    )
    
    chat_header_title = ft.Text("채팅방을 선택하세요", weight="bold", size=18, color="#333333")
    
    def load_topics(update_ui=True):
        try:
            res = supabase.table("chat_topics").select("id, name").execute()
            topics = res.data or []
            
            topic_list_view.controls = []
            for t in topics:
                is_selected = t['id'] == state["current_topic_id"]
                topic_list_view.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.CHAT_BUBBLE if is_selected else ft.Icons.CHAT_BUBBLE_OUTLINE, 
                                    size=16, color="#00C73C" if is_selected else "#666666"),
                            ft.Text(t['name'], size=14, weight="bold" if is_selected else "normal", color="black"),
                        ], spacing=10),
                        padding=ft.padding.symmetric(horizontal=15, vertical=10),
                        border_radius=8,
                        bgcolor="#E8F5E9" if is_selected else "transparent",
                        on_click=lambda e, topic=t: select_topic(topic),
                        ink=True
                    )
                )
            if update_ui: page.update()
        except Exception as e:
            print(f"Load Topics Error: {e}")

    def select_topic(topic):
        state["current_topic_id"] = topic['id']
        chat_header_title.value = topic['name']
        msg_input.disabled = False
        load_topics(True) 
        load_messages()

    def load_messages():
        if not state["current_topic_id"]: return
        try:
            res = supabase.table("chat_messages").select("*, profiles(username, full_name)").eq("topic_id", state["current_topic_id"]).order("created_at").execute()
            messages = res.data or []
            message_list_view.controls = []
            current_user_id = "00000000-0000-0000-0000-000000000001"
            
            for m in messages:
                is_me = str(m['user_id']) == current_user_id
                profile = m.get('profiles')
                if isinstance(profile, list) and len(profile) > 0: profile = profile[0]
                user_name = profile.get('full_name') if profile else "익명"
                time_str = m['created_at'][11:16]
                
                content_box = ft.Container(
                    content=ft.Column([
                        ft.Text(f"{user_name} • {time_str}", size=10, color="grey"),
                        ft.Text(m['content'], size=14, color="black"),
                    ], spacing=2),
                    bgcolor="#F1F1F1" if not is_me else "#DCF8C6",
                    padding=10, border_radius=10, width=250
                )
                
                row = ft.Row([
                    ft.CircleAvatar(content=ft.Text(user_name[0] if user_name else "?"), radius=15) if not is_me else ft.Container(),
                    content_box,
                ], alignment=ft.MainAxisAlignment.START if not is_me else ft.MainAxisAlignment.END)
                
                message_list_view.controls.append(row)
            page.update()
        except Exception as e:
            print(f"Load Messages Error: {e}")

    def send_message():
        if not msg_input.value or not state["current_topic_id"]: return
        try:
            supabase.table("chat_messages").insert({
                "topic_id": state["current_topic_id"],
                "content": msg_input.value,
                "user_id": "00000000-0000-0000-0000-000000000001"
            }).execute()
            msg_input.value = ""
            load_messages()
        except Exception as e:
            print(f"Send Error: {e}")

    def open_create_topic_dialog(e):
        new_name = ft.TextField(label="새 토픽 이름", autofocus=True)
        def create_it(e):
            if new_name.value:
                supabase.table("chat_topics").insert({"name": new_name.value}).execute()
                page.close(dlg)
                load_topics(True)
        dlg = ft.AlertDialog(
            title=ft.Text("새 토픽 만들기"),
            content=new_name,
            actions=[ft.TextButton("취소", on_click=lambda _: page.close(dlg)), ft.TextButton("만들기", on_click=create_it)]
        )
        page.open(dlg)

    sidebar = ft.Container(
        width=240, bgcolor="#1A1A1A",
        border=ft.border.only(right=ft.border.BorderSide(1, "#333333")),
        content=ft.Column([
            ft.Container(ft.Text("THE MANAGER", size=20, weight="bold", color="white", letter_spacing=1), padding=20),
            ft.Divider(height=1, color="#333333"),
            ft.Container(content=ft.Row([ft.Text("토픽", weight="bold", size=14, color="white70"), ft.IconButton(ft.Icons.ADD, icon_color="white", icon_size=18, on_click=open_create_topic_dialog)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=ft.padding.only(left=20, right=10, top=10)),
            ft.Container(content=topic_list_view, expand=True, padding=ft.padding.only(left=5, right=5)),
            ft.Container(content=ft.TextButton("🏠 홈으로 가기", style=ft.ButtonStyle(color="white70"), on_click=lambda _: navigate_to("home")), padding=15, alignment=ft.Alignment(0,0))
        ])
    )

    main_area = ft.Container(
        expand=True, bgcolor="#2D3436",
        content=ft.Column([
            ft.Container(content=ft.Row([chat_header_title, ft.IconButton(ft.Icons.REFRESH, icon_color="white", on_click=lambda _: load_topics(True))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=15, border=ft.border.only(bottom=ft.border.BorderSide(1, "#444444"))),
            ft.Container(content=message_list_view, expand=True, padding=20),
            ft.Container(content=ft.Row([msg_input, ft.IconButton(ft.Icons.SEND, icon_color="#00C73C", on_click=lambda _: send_message())], spacing=10), padding=10, border=ft.border.only(top=ft.border.BorderSide(1, "#444444")))
        ])
    )
    # Update state for dark theme
    chat_header_title.color = "white"
    msg_input.bgcolor = "#3D4446"
    msg_input.color = "white"
    msg_input.border_color = "#555555"

    load_topics(False)
    return [ft.Row([sidebar, main_area], expand=True, spacing=0)]

# [1] 로그인 화면
def get_login_controls(page, navigate_to):
    pw = ft.TextField(
        label="PIN CODE", 
        password=True, 
        text_align=ft.TextAlign.CENTER, 
        width=240, 
        on_submit=lambda e: navigate_to("home") if pw.value=="1234" else None,
        border_color="white",
        cursor_color="white",
        color="white"
    )
    
    login_card = ft.Container(
        content=ft.Column([
            ft.Text("THE MANAGER", size=32, weight="bold", color="white", letter_spacing=2),
            ft.Text("Izakaya Ju-wol OS", size=14, color="white70"),
            ft.Container(height=40),
            pw,
            ft.ElevatedButton(
                "출근하기", 
                on_click=lambda _: navigate_to("home") if pw.value=="1234" else None, 
                width=240, height=50,
                style=ft.ButtonStyle(
                    color="black",
                    bgcolor="white",
                    shape=ft.RoundedRectangleBorder(radius=10)
                )
            )
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=40,
        border_radius=30,
        bgcolor=ft.Colors.with_opacity(0.15, "white"),
        blur=ft.Blur(20, 20),
        border=ft.border.all(1, ft.Colors.with_opacity(0.2, "white")),
    )

    return [
        ft.Stack([
            ft.Image(src="images/login_bg.png", width=page.window_width, height=page.window_height, fit=ft.ImageFit.COVER),
            ft.Container(expand=True, bgcolor=ft.Colors.with_opacity(0.4, "black")), # Overlay
            ft.Container(content=login_card, alignment=ft.alignment.center, expand=True)
        ], expand=True)
    ]

# [2] 메인 대시보드
def get_home_controls(page, navigate_to):
    def action_btn(label, icon_path, route):
        return ft.Container(
            content=ft.Column([
                ft.Image(src=icon_path, width=80, height=80),
                ft.Text(label, weight="bold", size=16, color="white"),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=165, height=180,
            bgcolor=ft.Colors.with_opacity(0.1, "white"),
            border_radius=25,
            on_click=lambda _: navigate_to(route),
            alignment=ft.alignment.center,
            ink=True,
            blur=ft.Blur(10, 10),
            border=ft.border.all(0.5, ft.Colors.with_opacity(0.1, "white"))
        )

    header = ft.Container(
        padding=ft.padding.only(left=20, right=20, top=40, bottom=20),
        content=ft.Row([
            ft.Column([
                ft.Text("Welcome back,", size=14, color="white70"),
                ft.Text("The Manager", size=24, weight="bold", color="white"),
            ], spacing=2),
            ft.IconButton(ft.Icons.LOGOUT_ROUNDED, icon_color="white", on_click=lambda _: navigate_to("login"))
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    )

    grid = ft.Column([
        ft.Row([
            action_btn("업무 채팅", "images/icon_chat.png", "chat"),
            action_btn("마감 점검", "images/icon_check.png", "closing"),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
        ft.Row([
            action_btn("발주 메모", "images/icon_voice.png", "order"),
            action_btn("근무 캘린더", "images/icon_calendar.png", "calendar"),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
    ], spacing=15)

    return [
        ft.Stack([
            # 다크한 배경 그라데이션
            ft.Container(
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_left,
                    end=ft.alignment.bottom_right,
                    colors=["#1A1A1A", "#2D3436"]
                ),
                expand=True
            ),
            ft.Column([
                header,
                ft.Container(content=grid, padding=20, expand=True)
            ], scroll=ft.ScrollMode.AUTO)
        ], expand=True)
    ]

# [3] 마감 점검
def get_closing_controls(page, navigate_to):
    checklist = ft.Column([
        ft.Container(
            content=ft.Checkbox(label="주방 가스 밸브 차단 확인", label_style=ft.TextStyle(color="white")),
            padding=15, bgcolor=ft.Colors.with_opacity(0.1, "white"), border_radius=10
        ),
        ft.Container(
            content=ft.Checkbox(label="홀 에어컨 및 조명 OFF 확인", label_style=ft.TextStyle(color="white")),
            padding=15, bgcolor=ft.Colors.with_opacity(0.1, "white"), border_radius=10
        ),
    ], spacing=10)

    header = ft.Row([
        ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW, icon_color="white", on_click=lambda _: navigate_to("home")),
        ft.Text("마감 안전 점검", size=24, weight="bold", color="white")
    ])

    return [
        ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_center,
                end=ft.alignment.bottom_center,
                colors=["#1A1A1A", "#2D3436"]
            ),
            padding=30,
            content=ft.Column([
                header,
                ft.Container(height=30),
                ft.Text("Safety Checklist", color="white70", size=14),
                checklist,
                ft.Container(height=40),
                ft.ElevatedButton(
                    "점검 완료 및 퇴근", 
                    on_click=lambda _: navigate_to("home"), 
                    width=400, height=60,
                    style=ft.ButtonStyle(
                        color="white",
                        bgcolor="#00C73C",
                        shape=ft.RoundedRectangleBorder(radius=12)
                    )
                )
            ])
        )
    ]

# [5] 근무 캘린더
def get_calendar_controls(page: ft.Page, navigate_to):
    from datetime import datetime
    now = datetime.now()
    view_state = {"year": now.year, "month": now.month, "today": now.day, "events": []}
    month_label = ft.Text("", size=18, weight="bold", color="#333333")
    grid = ft.GridView(expand=True, runs_count=7, spacing=0, run_spacing=0)

    def load():
        try:
            res = supabase.table("calendar_events").select("*, profiles(full_name)").execute()
            view_state["events"] = res.data or []
            build()
        except Exception as e:
            print(f"Calendar Load Error: {e}")
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
                        ev_stack.controls.append(ft.Container(content=ft.Text(display_text, size=8, color="white", no_wrap=True), bgcolor=ev.get('color', '#1DDB16'), padding=2, border_radius=3))
                    
                    grid.controls.append(
                        ft.Container(
                            content=ft.Column([ft.Container(date_box, padding=4), ft.Container(ev_stack, padding=1)], spacing=2),
                            border=ft.border.all(0.5, "#EEEEEE"), bgcolor="white", ink=True, on_click=lambda e, d=day: open_day_details(d)
                        )
                    )
        page.update()

    def open_day_details(day):
        # 날짜 클릭 시 상세 내용을 보여주는 팝업
        d_str = f"{view_state['year']}-{view_state['month']:02d}-{day:02d}"
        evs = [e for e in view_state["events"] if e['start_date'].startswith(d_str)]
        
        detail_list = ft.Column(spacing=10, tight=True, scroll=ft.ScrollMode.AUTO)
        
        if not evs:
            detail_list.controls.append(ft.Text("등록된 일정이 없습니다.", color="grey", italic=True))
        else:
            for ev in evs:
                prof = ev.get('profiles')
                if isinstance(prof, list) and prof: prof = prof[0]
                un = prof.get('full_name', '익명') if prof else '익명'
                detail_list.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(ev['title'], size=15, weight="bold"),
                            ft.Text(f"작성자: {un}", size=11, color="grey"),
                        ], spacing=2),
                        padding=12, bgcolor="#F8F9FA", border_radius=10, border=ft.border.all(1, "#EEEEEE")
                    )
                )

        def go_to_add(e):
            page.close(dlg_details)
            open_event_editor(day)

        dlg_details = ft.AlertDialog(
            title=ft.Text(f"{view_state['month']}월 {day}일 상세 일정"),
            content=ft.Container(content=detail_list, width=320, padding=10),
            actions=[
                ft.TextButton("닫기", on_click=lambda _: page.close(dlg_details)),
                ft.ElevatedButton("새 일정 추가", on_click=go_to_add, bgcolor="#00C73C", color="white"),
            ]
        )
        page.open(dlg_details)

    def open_event_editor(day, init=""):
        fld = ft.TextField(label="상세 일정 내용", value=init, autofocus=True, multiline=True)
        col = ft.Dropdown(label="분류", options=[ft.dropdown.Option("#00C73C", "✅ 업무"), ft.dropdown.Option("#FF5050", "🚩 긴급"), ft.dropdown.Option("#FF9800", "📦 발주"), ft.dropdown.Option("#2196F3", "🔵 기타")], value="#00C73C" if not init else "#FF9800")
        def save(e):
            if not fld.value: return
            try:
                dt = f"{view_state['year']}-{view_state['month']:02d}-{day:02d}T09:00:00"
                supabase.table("calendar_events").insert({"title": fld.value, "start_date": dt, "end_date": dt, "color": col.value, "user_id": "00000000-0000-0000-0000-000000000001"}).execute()
                page.close(dlg); load()
            except Exception as ex: print(f"Save Error: {ex}")
        dlg = ft.AlertDialog(title=ft.Text(f"{day}일 새로운 일정"), content=ft.Column([fld, col], tight=True, spacing=15), actions=[ft.TextButton("취소", on_click=lambda _: page.close(dlg)), ft.ElevatedButton("저장", on_click=save, bgcolor="#00C73C", color="white")])
        page.open(dlg)

    def change_m(delta):
        view_state["month"] += delta
        if view_state["month"] > 12: view_state["month"]=1; view_state["year"]+=1
        elif view_state["month"] < 1: view_state["month"]=12; view_state["year"]-=1
        load()

    header = ft.Container(height=60, bgcolor="white", border=ft.border.only(bottom=ft.border.BorderSide(1, "#EEEEEE")), padding=ft.padding.symmetric(horizontal=20), content=ft.Row([ft.Row([ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda _: change_m(-1)), month_label, ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda _: change_m(1))], spacing=10), ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: load()), ft.TextButton("나가기", icon=ft.Icons.LOGOUT, on_click=lambda _: navigate_to("home"))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
    load()
    return [ft.Column([header, ft.Container(grid, expand=True, padding=10)], expand=True, spacing=0)]

# [6] 보이스 발주 메모
def get_order_controls(page: ft.Page, navigate_to):
    state = {"is_recording": False, "memos": [], "seconds": 0, "edit_id": None}
    memo_list_view = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
    status_text = ft.Text("버튼을 눌러 녹음을 시작하세요", color="grey", size=14)
    recording_timer = ft.Text("00:00", size=32, weight="bold", color="black", visible=False)
    
    audio_recorder = ft.AudioRecorder()
    page.overlay.append(audio_recorder)

    def load_memos():
        try:
            res = supabase.table("order_memos").select("*").order("created_at", desc=True).execute()
            state["memos"] = res.data or []; render_memos()
        except: pass

    def render_memos():
        memo_list_view.controls = []
        if not state["memos"]:
            memo_list_view.controls.append(ft.Container(content=ft.Text("저장된 발주 메모가 없습니다.", italic=True, color="grey"), padding=20, alignment=ft.alignment.center))
        
        ed_id = state.get("edit_id")
        for m in state["memos"]:
            time_str = m['created_at'][5:16].replace('T', ' ')
            is_ed = (ed_id == m['id'])
            if is_ed:
                fld = ft.TextField(value=m['content'], multiline=True, expand=True, autofocus=True, text_size=15, border_color="#00C73C")
                memo_content = ft.Row([fld, ft.Column([ft.IconButton(ft.Icons.CHECK_CIRCLE, icon_color="#00C73C", on_click=lambda e, mid=m['id'], f=fld: save_inline(mid, f)), ft.IconButton(ft.Icons.CANCEL, icon_color="red", on_click=lambda _: cancel_ed())], spacing=0)], alignment="spaceBetween")
            else:
                memo_content = ft.Row([ft.Column([ft.Row([ft.Icon(ft.Icons.RECEIPT_LONG, size=16, color="#448AFF"), ft.Text(time_str, size=11, color="grey")], spacing=5), ft.Text(m['content'], size=15, weight="w500", color="black")], spacing=5, expand=True), ft.Row([ft.IconButton(ft.Icons.CALENDAR_TODAY, icon_size=18, icon_color="#FF9800", on_click=lambda e, t=m['content']: pkr(t)), ft.IconButton(ft.Icons.COPY, icon_size=18, on_click=lambda e, t=m['content']: copy(t)), ft.IconButton(ft.Icons.EDIT, icon_size=18, on_click=lambda e, mid=m['id']: enter_ed(mid))], spacing=0)], alignment="spaceBetween")
            memo_list_view.controls.append(ft.Container(content=memo_content, padding=15, bgcolor="#F8F9FA", border_radius=10, border=ft.border.all(1, "#EEEEEE")))
        page.update()

    def pkr(txt):
        def on_date(e):
            if not date_picker.value: return
            dt = date_picker.value.strftime("%Y-%m-%dT09:00:00")
            supabase.table("calendar_events").insert({"title": txt, "start_date": dt, "end_date": dt, "color": "#FF9800", "user_id": "00000000-0000-0000-0000-000000000001"}).execute()
            page.snack_bar = ft.SnackBar(ft.Text("일정에 추가되었습니다! 📅"))
            page.snack_bar.open = True
            navigate_to("calendar")
        date_picker = ft.DatePicker(on_change=on_date)
        page.open(date_picker)

    def enter_ed(mid): state["edit_id"] = mid; render_memos()
    def cancel_ed(): state["edit_id"] = None; render_memos()
    def save_inline(mid, f):
        supabase.table("order_memos").update({"content": f.value}).eq("id", mid).execute()
        state["edit_id"] = None; load_memos()

    def copy(t):
        page.set_clipboard(t); page.snack_bar = ft.SnackBar(ft.Text("복사되었습니다!")); page.snack_bar.open = True; page.update()

    def toggle_rec(e):
        if not state["is_recording"]:
            if not audio_recorder.has_permission(): audio_recorder.request_permission(); return
            state["is_recording"] = True; state["seconds"] = 0; status_text.value = "녹음 중..."; recording_timer.visible = True
            def upd():
                import time
                while state["is_recording"]:
                    time.sleep(1); state["seconds"] += 1
                    mins, secs = divmod(state["seconds"], 60); recording_timer.value = f"{mins:02d}:{secs:02d}"; page.update()
            threading.Thread(target=upd, daemon=True).start()
            path = os.path.join(tempfile.gettempdir(), "order_voice.wav"); audio_recorder.start_recording(path); page.update()
        else:
            state["is_recording"] = False; status_text.value = "변환 중..."; recording_timer.visible = False
            path = audio_recorder.stop_recording()
            if not path or "blob" in path: status_text.value = "환경 오류 (데스크탑 앱 권장)"; page.update(); return
            def proc():
                try:
                    # Get keywords for prompt
                    prompts_res = supabase.table("voice_prompts").select("keyword").execute()
                    keywords = [p['keyword'] for p in prompts_res.data or []]
                    prompt_str = ", ".join(keywords) if keywords else None
                    
                    t = transcribe_audio(path, prompt=prompt_str)
                    if t: supabase.table("order_memos").insert({"content": t, "user_id": "00000000-0000-0000-0000-000000000001"}).execute(); load_memos()
                    status_text.value = "기다리는 중..."
                except Exception as ex:
                    print(f"Proc Error: {ex}")
                finally:
                    page.update()
            threading.Thread(target=proc).start(); page.update()

    def open_dictionary(e):
        # 1. 컴포넌트 선언을 먼저 합니다.
        prompt_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, height=300)
        
        def load_prompts():
            try:
                res = supabase.table("voice_prompts").select("*").order("created_at").execute()
                prompt_list.controls = [
                    ft.Row([
                        ft.Text(p['keyword'], size=14, expand=True),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color="red", 
                                      on_click=lambda e, pid=p['id']: delete_prompt(pid))
                    ]) for p in res.data or []
                ]
                # 다이얼로그와 페이지 모두 갱신
                if dlg_dict.open:
                    dlg_dict.update()
                page.update()
            except Exception as ex:
                print(f"Load Prompts Error: {ex}")

        def delete_prompt(pid):
            try:
                supabase.table("voice_prompts").delete().eq("id", pid).execute()
                load_prompts()
            except Exception as ex:
                print(f"Delete Prompt Error: {ex}")

        def add_prompt_event(e):
            val = new_word.value.strip()
            if not val: return
            
            # 클릭 반응 확인용 피드백
            page.snack_bar = ft.SnackBar(ft.Text(f"'{val}' 저장 중..."), duration=1000)
            page.snack_bar.open = True
            page.update()

            try:
                # DB Insert
                supabase.table("voice_prompts").insert({
                    "keyword": val, 
                    "user_id": "00000000-0000-0000-0000-000000000001"
                }).execute()
                
                new_word.value = ""
                new_word.focus()
                
                page.snack_bar = ft.SnackBar(ft.Text(f"'{val}' 추가 성공!"), bgcolor="#00C73C")
                page.snack_bar.open = True
                load_prompts()
            except Exception as ex:
                print(f"Add Prompt Error: {ex}")
                page.snack_bar = ft.SnackBar(ft.Text(f"저장 실패: {ex}"), bgcolor="red")
                page.snack_bar.open = True
                page.update()

        new_word = ft.TextField(
            label="추가할 단어/메뉴", 
            expand=True,
            on_submit=add_prompt_event
        )

        dlg_dict = ft.AlertDialog(
            title=ft.Text("메뉴/키워드 사전"),
            content=ft.Column([
                ft.Text("AI가 잘 못알아듣는 단어를 등록하세요.", size=12, color="grey"),
                ft.Row([
                    new_word, 
                    ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color="#00C73C", on_click=add_prompt_event)
                ], spacing=10),
                ft.Divider(),
                prompt_list
            ], tight=True, width=320),
            actions=[ft.TextButton("닫기", on_click=lambda _: page.close(dlg_dict))]
        )

        page.open(dlg_dict)
        load_prompts()

    mic_btn = ft.Container(content=ft.Icon(ft.Icons.MIC, size=40, color="white"), width=80, height=80, bgcolor="#00C73C", border_radius=40, alignment=ft.alignment.center, on_click=toggle_rec, shadow=ft.BoxShadow(blur_radius=10, color="#00C73C"), ink=True)
    header = ft.Container(content=ft.Row([ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to("home")), ft.Text("보이스 발주 메모", size=20, weight="bold")]), ft.IconButton(ft.Icons.BOOKMARK_ADDED, tooltip="단어장", on_click=open_dictionary)], alignment="spaceBetween"), padding=10, border=ft.border.only(bottom=ft.border.BorderSide(1, "#EEEEEE")))
    load_memos()
    return [ft.Container(expand=True, bgcolor="white", content=ft.Column([header, ft.Container(memo_list_view, expand=True, padding=20), ft.Container(content=ft.Column([status_text, recording_timer, mic_btn, ft.Container(height=10)], horizontal_alignment="center", spacing=10), padding=20, bgcolor="#F8F9FA", border_radius=ft.border_radius.only(top_left=30, top_right=30))], spacing=0))]

