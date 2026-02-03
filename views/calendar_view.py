import flet as ft
from datetime import datetime, time
import calendar
import re
import urllib.parse
import asyncio
from services import calendar_service
from services.chat_service import get_storage_signed_url, get_public_url, upload_file_server_side
import os
from utils.logger import log_debug, log_error, log_info
from views.styles import AppColors, AppLayout, AppTextStyles
from views.components.app_header import AppHeader
from views.components.modal_overlay import ModalOverlay
import threading
from db import supabase

class ThreadSafeState:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = {"is_active": True}
    def get(self, key, default=None):
        with self._lock: return self._data.get(key, default)
    def set(self, key, value):
        with self._lock: self._data[key] = value
    def __getitem__(self, key):
        with self._lock: return self._data[key]
    def __setitem__(self, key, value):
        with self._lock: self._data[key] = value

    def close(self):
        self.close_force()
        
    def close_all(self):
        self.close_force()

    def cleanup_pickers(self):
        # Already handled by clear()
        pass

async def get_calendar_controls(page: ft.Page, navigate_to):
    now = datetime.now()
    view_state = {"year": now.year, "month": now.month, "today": now.day, "events": []}
    
    # [FIX] Helper for updates (Flet 0.80+ page.update() is sync)
    def update_page():
        page.update()
    
    # [FIX] Multi-Channel
    log_debug("Entering get_calendar_controls")
    channel_id = page.app_session.get("channel_id")
    log_debug(f"Channel ID: {channel_id}")
    
    state = ThreadSafeState()
    # dialog_manager removed
    
    state["cid"] = channel_id
    
    # [FAUX DIALOG]
    overlay = ModalOverlay(page)

    if not channel_id:
        log_error("No Channel ID - returning error UI")
        return [ft.Container(content=ft.Text("매장 정보가 없습니다.", color="red"), padding=20)]
    
    month_label = ft.Text("", size=18, weight="bold", color="#333333")
    # [Calendar V2] Sidebar & Multi-Calendar State
    current_cal_type = "store" # Default to store view
    
    # State for UI rebuilds
    # current_cal_type = "store" # Moved up # store | staff
    

    
    # [FIX] Initialize container for Flex Layout (Column of Rows)
    # Replaces GridView to allow flexible height adaptation
    # [FIX] Initialize container as empty to prevent infinite spinner
    # [STABILITY] Start blank; load_async() will populate or build empty grid
    calendar_container = ft.Column(
        expand=True,
        spacing=0,
        alignment=ft.MainAxisAlignment.START,
        controls=[] 
    )
    
    # Staff Schedule Generator
    async def generate_staff_events(year, month):
        client = None
        try:
            from postgrest import SyncPostgrestClient
            import os
            from services.auth_service import auth_service

            headers = auth_service.get_auth_headers()
            if not headers: return []
            url = os.environ.get("SUPABASE_URL")
            if not url: return []

            client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public", timeout=20)

            # 1. Fetch Contracts (Filtered by Channel to see ALL staff)
            c_res = await asyncio.to_thread(lambda: client.from_("labor_contracts").select("*").eq("channel_id", channel_id).execute())
            contracts = c_res.data or []

            # 2. Fetch Overrides (is_work_schedule = True, Filtered by Channel)
            start_iso = f"{year}-{month:02d}-01T00:00:00"
            last_day = calendar.monthrange(year, month)[1]
            end_iso = f"{year}-{month:02d}-{last_day}T23:59:59"

            # [TIMEOUT SAFETY] 10s limit
            o_res = await asyncio.wait_for(asyncio.to_thread(lambda: client.from_("calendar_events")
                                           .select("*")
                                           .eq("is_work_schedule", True)
                                           .gte("start_date", start_iso)
                                           .lte("start_date", end_iso)
                                           .eq("channel_id", channel_id)
                                           .execute()), timeout=10)
            overrides = o_res.data or []
        except Exception as ex:
            log_error(f"Calendar Staff Fetch Error: {ex}")
            return []
        finally:
            # [CRITICAL FIX] 리소스 누수 방지 - HTTP 클라이언트 정리
            if client:
                try:
                    client.session.close()
                except Exception:
                    pass

        # Map overrides by [employee_id][day]
        override_map = {}
        for o in overrides:
            eid = o.get('employee_id')
            if not eid: continue
            try:
                # Handle ISO string from DB (might be with or without Z/TZ)
                d_str = o['start_date'].split('T')[0]
                day = int(d_str.split('-')[-1])
                if eid not in override_map: override_map[eid] = {}
                override_map[eid][day] = o
            except (ValueError, KeyError, IndexError):
                pass  # Invalid date format

        events = []
        days_in_month = calendar.monthrange(year, month)[1]
        
        # 1. Map contracts by name -> list of contracts (history)
        name_to_history = {}
        eid_to_name = {}
        for c in contracts:
            name = c.get('employee_name', 'Unknown').strip()
            eid_to_name[c['id']] = name
            if name not in name_to_history: name_to_history[name] = []
            name_to_history[name].append(c)

        for name in name_to_history:
            name_to_history[name].sort(key=lambda x: x.get('created_at', ''), reverse=True)

        # 2. Map overrides by name -> day -> override
        # Use name as the key to consolidate overrides from different contract IDs of the same person
        name_day_overrides = {}
        for o in overrides:
            eid = o.get('employee_id')
            name = eid_to_name.get(eid)
            if not name:
                # Fallback: parse name from title if orphaned
                title = o.get('title', '')
                # Strictly require an ledger emoji for orphaned entries
                if '⭐' in title: name = title.split('(')[0].replace('⭐', '').strip()
                elif '❌' in title: name = title.replace('❌', '').replace('결근', '').strip()
                elif '🟢' in title: name = title.split('(')[0].replace('🟢', '').strip()
                elif '🔥' in title: name = title.split('(')[0].replace('🔥', '').strip()
                else: continue # SKIP Ghost/Legacy data
            
            name = name.strip()
            if name not in name_day_overrides: name_day_overrides[name] = {}
            try:
                day = int(o['start_date'].split('T')[0].split('-')[-1])
                # If multiple overrides for same name/day, keep latest created?
                # (usually there's only one, but let's be safe)
                old_o = name_day_overrides[name].get(day)
                if not old_o or (o.get('created_at', '') > old_o.get('created_at', '')):
                    name_day_overrides[name][day] = o
            except (ValueError, KeyError, IndexError):
                pass  # Invalid date format

        all_names = set(name_to_history.keys()) | set(name_day_overrides.keys())

        for name in all_names:
            history = name_to_history.get(name, [])
            
            for day in range(1, days_in_month + 1):
                date_obj = datetime(year, month, day)
                weekday = date_obj.weekday()
                
                # A. Check for Override (Actual)
                o = name_day_overrides.get(name, {}).get(day)
                if o:
                    try:
                        st = o['start_date'].split('T')[1][:5]
                        et = o['end_date'].split('T')[1][:5]
                    except: st, et = "??", "??"
                    
                    is_absence = (st == et == "00:00")
                    
                    # Determine color based on contract presence
                    valid_c_for_day = None
                    for h in history:
                        sd = h.get('contract_start_date')
                        ed = h.get('contract_end_date')
                        if sd and datetime.strptime(sd, "%Y-%m-%d") > date_obj: continue
                        if ed and datetime.strptime(ed, "%Y-%m-%d") < date_obj: continue
                        # Check if this weekday is in contract schedule
                        if str(weekday) in h.get('work_schedule', {}):
                            valid_c_for_day = h
                            break
                    
                    final_color = o.get('color')
                    if not final_color:
                        final_color = "green"
                        if is_absence: final_color = "red"
                        elif not valid_c_for_day: final_color = "blue"

                    events.append({
                        "id": o['id'],
                        "title": o.get('title', f"⭐ {name} ({st}~{et})"),
                        "start_date": o['start_date'],
                        "end_date": o['end_date'],
                        "color": final_color,
                        "is_virtual": False,
                        "employee_id": o['employee_id'], # Keep original eid link
                        "employee_name": name,
                        "memo": o.get('memo')
                    })

                # B. Check for Contract Default (Baseline)
                # Only show baseline if it's currently valid for the date
                valid_c = None
                for h in history:
                    sd = h.get('contract_start_date')
                    ed = h.get('contract_end_date')
                    if sd and datetime.strptime(sd, "%Y-%m-%d") > date_obj: continue
                    if ed and datetime.strptime(ed, "%Y-%m-%d") < date_obj: continue
                    valid_c = h
                    break
                
                if valid_c:
                    ws = valid_c.get('work_schedule', {})
                    if str(weekday) in ws:
                        times = ws[str(weekday)]
                        start_t = times.get('start', '09:00')
                        end_t = times.get('end', '18:00')
                        events.append({
                            "id": f"virtual_{valid_c['id']}_{day}",
                            "title": f"{name} ({start_t}~{end_t})",
                            "start_date": f"{year}-{month:02d}-{day:02d}T{start_t}:00",
                            "end_date": f"{year}-{month:02d}-{day:02d}T{end_t}:00",
                            "color": "orange",
                            "is_virtual": True,
                            "employee_id": valid_c['id'],
                            "employee_name": name
                        })
        return events

    # [RBAC] Get User from Session
    current_user_id = page.app_session.get("user_id")
    # For robust MVP, allow view but require login
    async def load(e=None):
        log_debug("load() called - scheduling load_async")
        await load_async()
        
    async def load_async():
        log_debug(f"load_async start. User: {current_user_id}, Channel: {channel_id}, Type: {current_cal_type}")
        if not current_user_id: 
            log_debug("No current_user_id")
            return
            
        try:
            if current_cal_type == "store":
                log_debug("Fetching store events...")
                # [TIMEOUT SAFETY] 10s limit
                view_state["events"] = await asyncio.wait_for(calendar_service.get_all_events(current_user_id, channel_id), timeout=10)
                log_debug(f"Store events fetched: {len(view_state['events'])}")
            elif current_cal_type == "staff":
                log_debug("Fetching staff events...")
                view_state["events"] = await generate_staff_events(view_state["year"], view_state["month"])
                log_debug(f"Staff events fetched: {len(view_state['events'])}")
            
            log_debug("Fetch complete. Success.")
        except asyncio.TimeoutError:
            log_error("Calendar Load Timeout - rendering empty grid")
            view_state["events"] = []
        except Exception as e: 
            import traceback
            err = traceback.format_exc()
            log_error(f"Calendar Load Error: {err}")
            # [FIX] SnackBar for user awareness
            try:
                page.open(ft.SnackBar(ft.Text(f"데이터 로딩 실패: {e}"), bgcolor="red"))
                page.update()
            except: pass
        finally:
            log_debug("Calling build() and update_page() in finally block")
            await build()
            update_page()
            log_debug("load_async exit")

    # Removed dialog_manager setup

    async def build():
        try:
            log_debug(f"build() called for {view_state['year']}-{view_state['month']}")
            calendar_container.controls.clear()
            y = view_state["year"]
            m = view_state["month"]
            month_label.value = f"{y}년 {m}월"
            
            cal = calendar.monthcalendar(y, m)
            log_debug(f"Calendar generated weeks: {len(cal)}")
            
            # Flex Layout Construction
            for week in cal:
                week_row = ft.Row(
                    expand=True, # Each week row shares vertical space equally
                    spacing=0,
                )
                
                for day in week:
                    if day == 0:
                        # Empty cell
                        week_row.controls.append(
                            ft.Container(expand=True, bgcolor="#F4F4F4", border=ft.border.all(0.5, "#E0E0E0"))
                        )
                        continue
                        
                    # Active Day Cell
                    is_today = (day == now.day and m == now.month and y == now.year)
                    day_bg = "red" if is_today else None
                    day_text_color = "white" if is_today else "black"
                    date_obj = datetime(y, m, day)
                    
                    day_label = ft.Container(
                        content=ft.Text(str(day), color=day_text_color, size=12, weight="bold"),
                        bgcolor=day_bg,
                        border_radius=10, 
                        width=20, height=20, 
                        alignment=ft.Alignment(0, 0)
                    )
                    
                    day_events = []
                    current_date = f"{y}-{m:02d}-{day:02d}"
                    for ev in view_state["events"]:
                        try:
                            s_dt = ev.get("start_date", "")[:10]
                            e_dt = ev.get("end_date", "")[:10]
                            if not s_dt or not e_dt: continue
                            
                            # Check if the day falls within the event range
                            if s_dt <= current_date <= e_dt:
                                 # Decorate event object with position info for rendering
                                 ev_copy = dict(ev)
                                 ev_copy["_is_start"] = (current_date == s_dt)
                                 ev_copy["_is_end"] = (current_date == e_dt)
                                 day_events.append(ev_copy)
                        except Exception as e: 
                            log_error(f"Event Range Check Error: {e}")
                            pass
                    
                    # [STABILITY] Sort consistently to encourage row alignment across days
                    day_events.sort(key=lambda x: (str(x.get("start_date", "")), str(x.get("id", ""))))
                    
                    
                    # Chip container - Stretch to fill width
                    day_content_col = ft.Column(spacing=2, tight=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH) 
                    day_content_col.controls.append(ft.Container(content=day_label, alignment=ft.Alignment(0, 0), padding=ft.padding.only(bottom=2)))
                    
                    async def handle_day_click(d):
                        if current_cal_type == "staff":
                            await open_staff_day_ledger(d)
                        else:
                            await open_day_agenda_dialog(d)

                    for ev in day_events[:5]:
                        bg_color = ev.get("color", "blue")
                        if bg_color == "green": bg_color = "#4CAF50" # Vibrant Green
                        elif bg_color == "red": bg_color = "#F44336" # Vibrant Red
                        elif bg_color == "blue": bg_color = "#2196F3" # Vibrant Blue
                        elif bg_color == "orange": bg_color = "#FF9800" # Vibrant Orange
                        elif bg_color.startswith("#"): pass # Keep hex colors as is
                        else: bg_color = "#2196F3"
                        
                        is_start = ev.get("_is_start", True)
                        is_end = ev.get("_is_end", True)
                        weekday = date_obj.weekday() # 0=Mon, 6=Sun
                        
                        title = ev.get("title", "")
                        # Only show title on the start day OR on Mondays (start of week)
                        display_text = title if (is_start or weekday == 0) else ""
                        
                        # Calculate border radius to make it look like a continuous bar
                        # [TopLeft, TopRight, BottomRight, BottomLeft]
                        br = ft.border_radius.all(4)
                        if not is_start and not is_end:
                            br = ft.border_radius.all(0)
                        elif is_start and not is_end:
                            if weekday == 6: # Sunday: round the end too
                                br = ft.border_radius.all(4)
                            else:
                                br = ft.border_radius.only(top_left=4, bottom_left=4)
                        elif not is_start and is_end:
                            if weekday == 0: # Monday: round the start too
                                br = ft.border_radius.all(4)
                            else:
                                br = ft.border_radius.only(top_right=4, bottom_right=4)

                        chip = ft.Container(
                            content=ft.Text(display_text, size=9, weight="bold", color="white", no_wrap=True, overflow=ft.TextOverflow.CLIP),
                            bgcolor=bg_color,
                            border_radius=br,
                            height=18, # Consistent height for bars
                            alignment=ft.Alignment(-1, 0),
                            padding=ft.padding.only(left=5, right=5),
                            margin=ft.margin.only(
                                left=(-4 if not is_start and weekday != 0 else 0), 
                                right=(-4 if not is_end and weekday != 6 else 0)
                            ),
                            on_click=lambda e, d=day: asyncio.create_task(handle_day_click(d)),
                        )
                        day_content_col.controls.append(chip)
                        
                    remaining = len(day_events) - 5
                    if remaining > 0:
                         day_content_col.controls.append(ft.Text(f"+{remaining}", size=8, color="grey", text_align="center"))



                    # Main Day Container
                    week_row.controls.append(
                        ft.Container(
                            expand=True, # Share horizontal space equally
                            content=day_content_col,
                            bgcolor="white",
                            border=ft.border.all(0.5, "#E0E0E0"),
                            padding=2,
                            on_click=lambda e, d=day: asyncio.create_task(handle_day_click(d)),
                            alignment=ft.Alignment(0, -1)
                        )
                    )
                
                calendar_container.controls.append(week_row)

            if page: update_page()
        except Exception as build_err:
            print(f"Calendar Build Error: {build_err}")
            import traceback
            traceback.print_exc()
            # debug_text removed
            if page: update_page()

    # [FIX] Hooks to ensure dialogs are closed on navigation
    original_route_handler = page.on_route_change
    def on_route_change_wrapper(e):
        overlay.close()
        if original_route_handler:
            original_route_handler(e)
    page.on_route_change = on_route_change_wrapper

    async def open_day_agenda_dialog(day):
        print(f"DEBUG_FAUX: Opening agenda for {day}")
        
        y, m = view_state["year"], view_state["month"]
        day_str = f"{y}-{m:02d}-{day:02d}"
        day_events = [ev for ev in view_state["events"] if not ev.get('is_virtual') and str(ev.get('start_date', '')).startswith(day_str)]
        day_events.sort(key=lambda x: x.get('start_date', ''))
        
        weekday_map = ["월", "화", "수", "목", "금", "토", "일"]
        d_obj = datetime(y, m, day)
        wd = weekday_map[d_obj.weekday()]

        agenda_items = []
        for ev in day_events:
            start_time = ev.get('start_date', '')[11:16]
            end_time = ev.get('end_date', '')[11:16]
            time_display = f"{start_time}-{end_time}" if start_time else "종일"
            
            def on_item_click(e, event=ev):
                open_event_detail_dialog(event, day)
            
            agenda_items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(time_display, size=12, color=AppColors.TEXT_SECONDARY, width=80),
                        ft.Container(width=1, height=20, bgcolor=AppColors.PRIMARY),
                        ft.Text(ev['title'], size=15, weight="bold", color=AppColors.TEXT_PRIMARY, expand=True),
                        ft.Icon(ft.Icons.ARROW_FORWARD_IOS, size=12, color=AppColors.BORDER)
                    ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=10,
                    border=ft.border.only(bottom=ft.border.BorderSide(1, AppColors.BORDER)),
                    on_click=on_item_click,
                    ink=True
                )
            )

        if not agenda_items:
            agenda_items.append(
                ft.Container(
                    content=ft.Text("오늘 등록된 일정이 없습니다.", color=AppColors.TEXT_SECONDARY),
                    alignment=ft.Alignment(0, 0), expand=True, padding=40
                )
            )

        # Build Internal Card (The actual dialog box)
        dialog_card = ft.Container(
            width=min(400, (page.window_width or 400) * 0.94),
            bgcolor=AppColors.SURFACE, padding=20,
            border_radius=20,
            on_click=lambda e: e.control.page.update(), # Eat click event so it doesn't close
            content=ft.Column([
                ft.Row([
                    ft.Text(f"{m}월 {day}일 {wd}요일", size=22, weight="bold", color=AppColors.TEXT_PRIMARY),
                    ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color=AppColors.PRIMARY, icon_size=32, 
                                  on_click=lambda _: asyncio.create_task(async_close_and_open_editor(None, day))),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=10, color="transparent"),
                ft.Column(agenda_items, spacing=10, scroll=ft.ScrollMode.AUTO, max_height=400),
                ft.Row([
                    ft.Container(expand=True),
                    ft.TextButton("닫기 (Faux)", on_click=lambda _: overlay.close())
                ])
            ], tight=True)
        )
        
        overlay.open(dialog_card)

    async def async_close_and_open_editor(dlg, day):
        # Close faux dialog then open editor
        overlay.close()
        open_event_editor_dialog(day)
    
    def open_event_detail_dialog(ev, day):
        def format_pretty_date(date_str):
            if not date_str: return "-"
            try:
                clean_str = date_str.replace("T", " ")[:16]
                dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M")
                wd_map = ["월", "화", "수", "목", "금", "토", "일"]
                wd = wd_map[dt.weekday()]
                return f"{dt.year}년 {dt.month}월 {dt.day}일 ({wd})"
            except: return date_str

        def delete_ev(e):
            async def _del():
                try:
                    await calendar_service.delete_event(ev['id'], current_user_id)
                    page.open(ft.SnackBar(ft.Text("삭제되었습니다."), bgcolor="green"))
                    overlay.close()
                    load()
                    update_page()
                except Exception as ex:
                    page.open(ft.SnackBar(ft.Text(f"삭제 실패: {ex}"), bgcolor="red")); update_page()
            asyncio.create_task(_del())

        creator_name = ev.get('profiles', {}).get('full_name', '알 수 없음')
        initials = creator_name[0] if creator_name else "?"
        
        detail_card = ft.Container(
            width=min(450, (page.window_width or 450) * 0.94),
            bgcolor=AppColors.SURFACE, padding=20, border_radius=28,
            on_click=lambda e: e.control.page.update(),
            shadow=ft.BoxShadow(blur_radius=20, color="#20000000"),
            content=ft.Column([
                # Header with Actions
                ft.Row([
                    ft.IconButton(ft.Icons.ARROW_BACK, icon_color=AppColors.TEXT_SECONDARY, on_click=lambda _: open_day_agenda_dialog(day)),
                    ft.Container(expand=True),
                    ft.TextButton("수정", icon=ft.Icons.EDIT, icon_color=AppColors.PRIMARY, 
                                 visible=(str(ev.get('created_by')) == str(current_user_id)),
                                 on_click=lambda _: open_event_editor_dialog(day, existing_event=ev))
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                # Main Title Content (Centered)
                ft.Column([
                    ft.Container(
                        content=ft.Text(initials, color="white", weight="bold", size=16), 
                        width=48, height=48, bgcolor="#D81B60", border_radius=24, 
                        alignment=ft.Alignment(0,0)
                    ),
                    ft.Text(ev['title'], size=24, weight="bold", color=AppColors.PRIMARY, text_align="center"),
                    ft.Text(f"{format_pretty_date(ev['start_date'])} ~ {format_pretty_date(ev['end_date'])}", 
                            size=14, color=AppColors.TEXT_SECONDARY, text_align="center"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                
                ft.Divider(height=30, color=AppColors.BORDER),
                
                # Description Scroll Area
                ft.Container(
                    content=ft.Column([
                        ft.Text("상세 내용", size=12, color=AppColors.TEXT_SECONDARY, weight="bold"),
                        ft.Text(ev.get('description', '상세 내용 없음'), size=16, color=AppColors.TEXT_PRIMARY),
                    ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.START, scroll=ft.ScrollMode.AUTO, max_height=200),
                    padding=ft.padding.symmetric(horizontal=10),
                    alignment=ft.Alignment(-1, 0)
                ),
                
                # Bottom Action Buttons (Centered)
                ft.Column([
                    ft.TextButton(
                        "이 일정 삭제하기", 
                        icon=ft.Icons.DELETE_OUTLINE, 
                        icon_color="red", 
                        style=ft.ButtonStyle(color="red"),
                        visible=(str(ev.get('created_by')) == str(current_user_id)), 
                        on_click=delete_ev
                    ),
                    ft.TextButton(
                        "닫기", 
                        on_click=lambda _: overlay.close(),
                        style=ft.ButtonStyle(color=AppColors.TEXT_SECONDARY)
                    )
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0, tight=True)
        )
        overlay.open(detail_card)


    async def delete_staff_event(ev_id):
        from services.auth_service import auth_service
        from postgrest import SyncPostgrestClient
        client = None
        try:
            headers = auth_service.get_auth_headers()
            if not headers: return
            if "apikey" not in headers: headers["apikey"] = os.environ.get("SUPABASE_KEY")
            url = os.environ.get("SUPABASE_URL")
            if not url: return
            client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public", timeout=20)
            await asyncio.to_thread(lambda: client.from_("calendar_events").delete().eq("id", ev_id).execute())
        finally:
            if client:
                try:
                    client.session.close()
                except Exception:
                    pass

    
    async def open_staff_day_ledger(day):
        y, m = view_state["year"], view_state["month"]
        current_day_evs = [ev for ev in view_state["events"] if not ev.get('is_virtual') and str(ev.get('start_date', '')).startswith(f"{y}-{m:02d}-{day:02d}")]
        
        staff_dd = ft.Dropdown(label="직원 선택", width=160)
        substitute_tf = ft.TextField(label="기타 성함", width=150)
        type_dd = ft.Dropdown(label="유형", width=120, options=[ft.dropdown.Option("absence", "결근"), ft.dropdown.Option("overtime", "연장")], value="absence")
        
        async def add_record():
            name = staff_dd.value or substitute_tf.value
            if not name: return
            # ... (Simplified logic for now to ensure rendering works)
            page.open(ft.SnackBar(ft.Text("기록 기능 준비중 (Faux UI 우선 적용)")))
            update_page()

        card = ft.Container(
            width=min(500, (page.window_width or 500) * 0.94),
            bgcolor=AppColors.SURFACE, padding=20, border_radius=20,
            on_click=lambda e: e.control.page.update(),
            content=ft.Column([
                ft.Text(f"{y}/{m}/{day} 근무 장부", size=18, weight="bold"),
                ft.Text("기록 추가", size=12, weight="bold"),
                ft.Row([staff_dd, substitute_tf], wrap=True),
                ft.Row([type_dd], wrap=True),
                ft.ElevatedButton("기록하기", on_click=lambda _: asyncio.create_task(add_record())),
                ft.Divider(),
                ft.TextButton("닫기", on_click=lambda _: overlay.close())
            ], spacing=10, scroll=ft.ScrollMode.AUTO, tight=True, max_height=page.window_height * 0.8)
        )
        overlay.open(card)


    
    def open_event_editor_dialog(day, init_title="", existing_event=None):
        print(f"DEBUG_FAUX: Opening editor for day {day}")
        try:
            target_date = datetime(view_state['year'], view_state['month'], day)
        except: target_date = datetime.now()

        if existing_event:
            s_dt = datetime.strptime(existing_event["start_date"].replace("T", " ")[:19], "%Y-%m-%d %H:%M:%S")
            e_dt = datetime.strptime(existing_event["end_date"].replace("T", " ")[:19], "%Y-%m-%d %H:%M:%S")
            evt_state = {
                "all_day": existing_event.get("is_all_day", False),
                "start_date": s_dt,
                "end_date": e_dt,
                "start_time": s_dt.time(),
                "end_time": e_dt.time(),
                "color": existing_event.get("color", "#1DDB16"),
                "participants": existing_event.get("participant_ids", []) or []
            }
        else:
            evt_state = {
                "all_day": False,
                "start_date": target_date.replace(hour=9,minute=0,second=0,microsecond=0),
                "end_date": target_date.replace(hour=10,minute=0,second=0,microsecond=0),
                "start_time": time(9,0),
                "end_time": time(10,0),
                "color": "#1DDB16",
                "participants": []
            }
        
        status_msg = ft.Text("", size=11, color="orange", italic=True)
        title_tf = ft.TextField(label="제목", value=existing_event.get("title", init_title) if existing_event else init_title, autofocus=True)
        loc_tf = ft.TextField(label="장소", icon=ft.Icons.LOCATION_ON, value=existing_event.get("location", "") if existing_event else "")
        memo_tf = ft.TextField(label="메모", multiline=True, min_lines=2, icon=ft.Icons.NOTE, value=existing_event.get("description", "") if existing_event else "")
        
        tf_ds = ft.TextField(width=100, text_size=12, content_padding=5, label="YYYY-MM-DD", value=evt_state["start_date"].strftime("%Y-%m-%d"))
        tf_de = ft.TextField(width=100, text_size=12, content_padding=5, label="YYYY-MM-DD", value=evt_state["end_date"].strftime("%Y-%m-%d"))
        tf_ts = ft.TextField(width=70, text_size=12, content_padding=5, label="HH:MM", value=evt_state["start_time"].strftime("%H:%M"), visible=not evt_state["all_day"])
        tf_te = ft.TextField(width=70, text_size=12, content_padding=5, label="HH:MM", value=evt_state["end_time"].strftime("%H:%M"), visible=not evt_state["all_day"])
        
        def toggle_all_day(e):
             evt_state["all_day"] = e.control.value
             tf_ts.visible = not e.control.value
             tf_te.visible = not e.control.value
             update_page()

        sw_all_day = ft.Switch(label="종일", value=evt_state["all_day"], on_change=toggle_all_day)
        
        colors = ["#1DDB16", "#FF9800", "#448AFF", "#E91E63", "#9C27B0", "#000000"]
        color_row = ft.Row(spacing=10)
        async def set_color(e):
            c = e.control.data
            evt_state["color"] = c
            for btn in color_row.controls:
                btn.content.visible = (btn.data == c)
            update_page()

        for c in colors:
            color_row.controls.append(ft.Container(width=30, height=30, bgcolor=c, border_radius=15, data=c, on_click=lambda e: asyncio.create_task(set_color(e)), content=ft.Icon(ft.Icons.CHECK, color="white", size=20, visible=(c==evt_state["color"])), alignment=ft.Alignment(0, 0)))

        def save(e):
            if not title_tf.value: 
                title_tf.error_text="필수"; title_tf.update(); return

            try:
                ds = datetime.strptime(tf_ds.value, "%Y-%m-%d").date()
                de = datetime.strptime(tf_de.value, "%Y-%m-%d").date()
                if not evt_state["all_day"]:
                    ts = datetime.strptime(tf_ts.value, "%H:%M").time()
                    te = datetime.strptime(tf_te.value, "%H:%M").time()
                else:
                    ts = time(0,0); te = time(23,59,59)
                cols_s = datetime.combine(ds, ts).strftime("%Y-%m-%d %H:%M:%S")
                cols_e = datetime.combine(de, te).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                page.open(ft.SnackBar(ft.Text("날짜/시간 형식이 올바르지 않습니다"), bgcolor="red"))
                page.update(); return

            data = {
                "title": title_tf.value, "start_date": cols_s, "end_date": cols_e,
                "is_all_day": evt_state["all_day"], "color": evt_state["color"],
                "location": loc_tf.value, "description": memo_tf.value,
                "participant_ids": evt_state["participants"], "created_by": current_user_id,
                "channel_id": channel_id
            }
            
            async def _save_async():
                try:
                    if existing_event: await calendar_service.update_event(existing_event["id"], data, current_user_id)
                    else: await calendar_service.create_event(data)
                    page.open(ft.SnackBar(ft.Text("저장 완료!")))
                    overlay.close()
                    load()
                    update_page()
                except Exception as ex:
                    page.open(ft.SnackBar(ft.Text(f"오류: {ex}"), bgcolor="red")); update_page()
            asyncio.create_task(_save_async())

        dialog_card = ft.Container(
            width=min(450, (page.window_width or 450) * 0.94),
            bgcolor=AppColors.SURFACE, padding=20, border_radius=20,
            on_click=lambda e: e.control.page.update(),
            content=ft.Column([
                ft.Text("일정 수정" if existing_event else "새 일정", size=20, weight="bold"),
                title_tf,
                ft.Row([ft.Text("종일"), sw_all_day]),
                ft.Row([ft.Text("시작"), tf_ds, tf_ts], wrap=True),
                ft.Row([ft.Text("종료"), tf_de, tf_te], wrap=True),
                ft.Text("색상"), color_row,
                memo_tf,
                ft.Row([
                    ft.Container(expand=True),
                    ft.TextButton("취소", on_click=lambda _: overlay.close()),
                    ft.ElevatedButton("저장", on_click=save, bgcolor="#00C73C", color="white")
                ], spacing=10)
            ], scroll=ft.ScrollMode.AUTO, spacing=15, tight=True, max_height=page.window_height * 0.8)
        )
        overlay.open(dialog_card)


    async def change_m(delta, e=None):
        view_state["month"] += delta
        if view_state["month"] > 12: view_state["month"]=1; view_state["year"]+=1
        elif view_state["month"] < 1: view_state["month"]=12; view_state["year"]-=1
        await load()

    async def on_swipe(e: ft.DragEndEvent):
        # Velocity-based horizontal swipe detection
        if e.primary_velocity is not None:
            if e.primary_velocity > 400: # Swiping Right -> Prev Month
                await change_m(-1)
            elif e.primary_velocity < -400: # Swiping Left -> Next Month
                await change_m(1)

    # Shadow removed

    def go_today():
        now = datetime.now()
        view_state["year"] = now.year
        view_state["month"] = now.month
        asyncio.create_task(load())

    def open_event_dialog():
        open_event_editor_dialog(datetime.now().day)

    # [NEW] Drawer & Channel Switching
    def switch_channel(ch):
        page.app_session["channel_id"] = ch["id"]
        page.app_session["channel_name"] = ch["name"]
        page.app_session["user_role"] = ch["role"]
        page.close_drawer()
        navigate_to("calendar") # Refresh view

    def on_drawer_change(e):
        nonlocal current_cal_type
        idx = e.control.selected_index
        if idx == 0: current_cal_type = "store"
        elif idx == 1: current_cal_type = "staff"
        
        # Update label immediately (load will do it too but for responsiveness)
        month_label.value = f"{view_state['year']}년 {view_state['month']}월"
        load()
        page.close(page.drawer)

    def build_drawer():
        print("DEBUG_CAL: build_drawer start")
        u_name = page.app_session.get("display_name") or "User"
        
        # Fetch Channels
        from services.auth_service import auth_service
        from services.channel_service import channel_service
        token = auth_service.get_access_token()
        # [FIX] Wrap sync call to prevent hang
        try:
            import asyncio
            # Use a slightly more robust way to fetch if possible, or just stay simple but safe
            channels = channel_service.get_user_channels(current_user_id, token)
        except Exception as e:
            print(f"DEBUG_CAL: Channel fetch err: {e}")
            channels = []
        
        print(f"DEBUG_CAL: build_drawer channels: {len(channels)}")
        
        drawer = ft.NavigationDrawer(
            on_change=on_drawer_change,
            bgcolor="white",
            selected_index=(0 if current_cal_type == 'store' else 1),
            controls=[
                ft.Container(
                    padding=ft.padding.only(left=20, top=50, bottom=20), 
                    bgcolor="white",
                    content=ft.Row([
                        ft.CircleAvatar(
                            content=ft.Text(u_name[0] if u_name else "U", size=20, weight="bold"),
                            bgcolor="#1565C0", radius=25, color="white"
                        ),
                        ft.Column([
                            ft.Text(u_name, color="black", size=18, weight="bold"),
                            ft.Text("나의 캘린더", color="grey", size=12)
                        ], spacing=2)
                    ], spacing=15)
                ),
                ft.Divider(thickness=1, color="#EEEEEE"),
                ft.NavigationDrawerDestination(
                    icon=ft.Icons.CALENDAR_MONTH_OUTLINED, 
                    label="전체 일정 (Store)",
                    selected_icon=ft.Icons.CALENDAR_MONTH
                ),
                 ft.NavigationDrawerDestination(
                    icon=ft.Icons.PEOPLE_OUTLINE, 
                    label="직원 근무표 (Staff)",
                    selected_icon=ft.Icons.PEOPLE
                ),
                ft.Divider(thickness=1, color="#EEEEEE"),
            ]
        )
        
        # [REMOVED] Store List as per request
            
        drawer.controls.append(ft.Divider(thickness=1, color="#EEEEEE"))
        drawer.controls.append(ft.Divider(thickness=1, color="#EEEEEE"))
        drawer.controls.append(
            ft.Container(
                content=ft.Row([ft.Icon(ft.Icons.ADD_BOX_OUTLINED, color="grey"), ft.Text("새 캘린더 만들기 (준비중)", color="grey")]),
                padding=ft.padding.symmetric(horizontal=20, vertical=15),
                on_click=lambda _: page.open(ft.SnackBar(ft.Text("다중 캘린더 기능은 준비 중입니다!"))) or page.update()
            )
        )
        return drawer

    # Apply Drawer
    drawer = build_drawer()
    page.drawer = drawer
    page.update()

    # [Standardized Header]
    async def go_prev_month(e):
        await change_m(-1)

    async def go_next_month(e):
        await change_m(1)

    header = AppHeader(
        title_text=ft.Row([
            ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda e: asyncio.create_task(go_prev_month(e)), icon_color=AppColors.TEXT_PRIMARY),
            month_label,
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda e: asyncio.create_task(go_next_month(e)), icon_color=AppColors.TEXT_PRIMARY)
        ], alignment=ft.MainAxisAlignment.CENTER),
        left_button=ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW, icon_color=AppColors.TEXT_PRIMARY, on_click=lambda e: asyncio.create_task(navigate_to("home")), tooltip="뒤로"),
            ft.IconButton(ft.Icons.MENU, icon_color=AppColors.TEXT_PRIMARY, on_click=lambda _: page.open(drawer), tooltip="메뉴"),
        ], spacing=0),
        action_button=ft.IconButton(ft.Icons.REFRESH, on_click=lambda e: asyncio.create_task(load(e)), icon_color=AppColors.TEXT_PRIMARY)
    )
    
    async def initial_load_delayed():
        try:
            await asyncio.sleep(0.5) 
            await load_async()
        except Exception as e:
            try:
                log_error(f"Init Load Error: {e}")
            except Exception:
                pass  # Logging failed

    async def realtime_handler():
        print(f"DEBUG_CAL: Handler started for CID={channel_id}, UID={current_user_id}")
        log_info("CALENDAR_SYNC: Handler started.")
        
        async def polling_loop():
            print("DEBUG_CAL: Polling loop started.")
            log_info("CALENDAR_SYNC: Polling loop started.")
            while state["is_active"]:
                try:
                    await asyncio.sleep(5)
                    if state["is_active"]:
                        # print("DEBUG_CAL: Polling tick.")
                        # [FIX] Disable polling to prevent Event Loop Starvation
                        # asyncio.create_task(load_async())
                        pass
                except Exception as e:
                    print(f"DEBUG_CAL: Polling error: {e}")
                    await asyncio.sleep(10)

        async def connection_loop():
            log_info("CALENDAR_SYNC: Connection loop started.")
            while state["is_active"]:
                try:
                    rt = supabase.get_realtime_client()
                    if not rt:
                        log_error("CALENDAR_SYNC: Realtime client not available.")
                        await asyncio.sleep(60)
                        continue
                    
                    await rt.connect()
                    # Use a generic channel name for now to ensure connectivity
                    chan_name = f"cal_realtime_{channel_id}"
                    channel = rt.channel(chan_name)
                    
                    async def on_change(payload):
                        log_info(f"CALENDAR_SYNC [RT]: {payload.get('eventType')} detected! Reloading UI.")
                        asyncio.create_task(load_async())

                    channel.on_postgres_changes(
                        event="*",
                        schema="public",
                        table="calendar_events",
                        # Removing filter temporarily for maximum compatibility
                        callback=on_change
                    )
                    
                    await channel.subscribe()
                    print(f"DEBUG_CAL: Subscribed successfully to {chan_name}")
                    log_info(f"CALENDAR_SYNC [RT]: Subscribed to {chan_name}")
                    
                    while state["is_active"]:
                        if hasattr(page, "is_running") and not page.is_running:
                            state["is_active"] = False
                            break
                        await asyncio.sleep(10)
                except Exception as e:
                    print(f"DEBUG_CAL: RT ERROR: {e}")
                    log_error(f"CALENDAR_SYNC [RT] ERROR: {e}")
                    await asyncio.sleep(30)
                finally:
                    try: 
                        if rt: await rt.disconnect()
                    except: pass
        
        # Run both for maximum reliability
        await asyncio.gather(polling_loop(), connection_loop())

    def on_nav_away(e):
        log_info("CALENDAR: Navigating away, stopping realtime.")
        state["is_active"] = False

    # Since there is no direct "on_close" for a view, we hook into the page's route change if we could, 
    # but more simply we rely on the loop check for page.is_running.

    asyncio.create_task(initial_load_delayed())
    # Register the realtime task properly
    rt_task = asyncio.create_task(realtime_handler())

    # Simple cleanup logic when view is logically destroyed
    def cleanup():
        log_info("CALENDAR: Performing cleanup...")
        state["is_active"] = False
    
    # We can't easily hook into view destruction in Flet without complex route logic, 
    # but the loop in realtime_handler checks page.is_running.

    print("DEBUG_CAL: Building main UI layout")
    # [FAUX STACK WRAPPER]
    main_layout = ft.Column([
        header,
        ft.Container(
            expand=True,
            padding=ft.padding.only(left=5, right=5, bottom=0, top=0),
            content=ft.GestureDetector(
                on_horizontal_drag_end=on_swipe,
                expand=True,
                content=ft.Column([
                    # Weekday header row
                    ft.Row([
                        ft.Container(content=ft.Text("월", color="black", size=13, text_align="center", weight="bold"), expand=True, alignment=ft.Alignment(0, 0), padding=5),
                        ft.Container(content=ft.Text("화", color="black", size=13, text_align="center", weight="bold"), expand=True, alignment=ft.Alignment(0, 0), padding=5),
                        ft.Container(content=ft.Text("수", color="black", size=13, text_align="center", weight="bold"), expand=True, alignment=ft.Alignment(0, 0), padding=5),
                        ft.Container(content=ft.Text("목", color="black", size=13, text_align="center", weight="bold"), expand=True, alignment=ft.Alignment(0, 0), padding=5),
                        ft.Container(content=ft.Text("금", color="black", size=13, text_align="center", weight="bold"), expand=True, alignment=ft.Alignment(0, 0), padding=5),
                        ft.Container(content=ft.Text("토", color="blue", size=13, text_align="center", weight="bold"), expand=True, alignment=ft.Alignment(0, 0), padding=5),
                        ft.Container(content=ft.Text("일", color="red", size=13, text_align="center", weight="bold"), expand=True, alignment=ft.Alignment(0, 0), padding=5),
                    ], spacing=0),
                    calendar_container
                ], spacing=0, expand=True)
            )
        )
    ], expand=True, spacing=0)

    final_stack = ft.Stack([ft.SafeArea(expand=True, content=main_layout), overlay], expand=True)
    return [final_stack]
