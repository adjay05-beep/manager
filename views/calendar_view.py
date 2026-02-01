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

def get_calendar_controls(page: ft.Page, navigate_to):
    now = datetime.now()
    view_state = {"year": now.year, "month": now.month, "today": now.day, "events": []}
    
    # [FIX] Multi-Channel
    log_debug("Entering get_calendar_controls")
    channel_id = page.session.get("channel_id")
    log_debug(f"Channel ID: {channel_id}")
    
    state = ThreadSafeState()
    state["cid"] = channel_id

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
    calendar_container = ft.Column(
        expand=True,
        spacing=0,
        alignment=ft.MainAxisAlignment.START,
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

            o_res = await asyncio.to_thread(lambda: client.from_("calendar_events")
                                           .select("*")
                                           .eq("is_work_schedule", True)
                                           .gte("start_date", start_iso)
                                           .lte("start_date", end_iso)
                                           .eq("channel_id", channel_id)
                                           .execute())
            overrides = o_res.data or []
        except Exception as ex:
            print(f"Calendar Staff Fetch Error: {ex}")
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
    current_user_id = page.session.get("user_id")
    # For robust MVP, allow view but require login
    def load():
        log_debug("load() called - scheduling load_async")
        page.run_task(load_async)
        
    async def load_async():
        log_debug(f"load_async start. User: {current_user_id}, Channel: {channel_id}, Type: {current_cal_type}")
        if not current_user_id: 
            log_debug("No current_user_id")
            return
            
        try:
            if current_cal_type == "store":
                log_debug("Fetching store events...")
                view_state["events"] = await calendar_service.get_all_events(current_user_id, channel_id)
                log_debug(f"Store events fetched: {len(view_state['events'])}")
            elif current_cal_type == "staff":
                log_debug("Fetching staff events...")
                view_state["events"] = await generate_staff_events(view_state["year"], view_state["month"])
                log_debug(f"Staff events fetched: {len(view_state['events'])}")
            
            log_debug("Calling build()...")
            build()
            
            print(f"DEBUG_CAL: Load success. Events: {len(view_state['events'])}")
            
            log_debug("Calling page.update() inside load_async")
            if page: page.update()
            
        except Exception as e: 
            import traceback
            err = traceback.format_exc()
            log_error(f"Calendar Load Error: {err}")
            print(f"Calendar Load Error: {err}")
            # debug_text removed
            if page: page.update()
            build()

    def build():
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
                        alignment=ft.alignment.center
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
                    day_content_col.controls.append(ft.Container(content=day_label, alignment=ft.alignment.center, padding=ft.padding.only(bottom=2)))
                    
                    def handle_day_click(d):
                        if current_cal_type == "staff":
                            open_staff_day_ledger(d)
                        else:
                            open_day_agenda_dialog(d)

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
                            alignment=ft.alignment.center_left,
                            padding=ft.padding.only(left=5, right=5),
                            margin=ft.margin.only(
                                left=(-4 if not is_start and weekday != 0 else 0), 
                                right=(-4 if not is_end and weekday != 6 else 0)
                            ),
                            on_click=lambda e, d=day: handle_day_click(d),
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
                            on_click=lambda e, d=day: handle_day_click(d),
                            alignment=ft.alignment.top_center
                        )
                    )
                
                calendar_container.controls.append(week_row)

            if page: page.update()
        except Exception as build_err:
            print(f"Calendar Build Error: {build_err}")
            import traceback
            traceback.print_exc()
            # debug_text removed
            if page: page.update()

    def open_day_agenda_dialog(day):
        y, m = view_state["year"], view_state["month"]
        # Find events for this day
        day_str = f"{y}-{m:02d}-{day:02d}"
        day_events = [ev for ev in view_state["events"] if not ev.get('is_virtual') and str(ev.get('start_date', '')).startswith(day_str)]
        day_events.sort(key=lambda x: x.get('start_date', ''))

        # Get weekday name
        weekday_map = ["월", "화", "수", "목", "금", "토", "일"]
        d_obj = datetime(y, m, day)
        wd = weekday_map[d_obj.weekday()]

        agenda_items = []
        for ev in day_events:
            start_time = ev.get('start_date', '')[11:16]
            end_time = ev.get('end_date', '')[11:16]
            time_display = f"{start_time}-{end_time}" if start_time else "종일"
            
            agenda_items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(time_display, size=12, color=AppColors.TEXT_SECONDARY, width=80),
                        ft.VerticalDivider(width=1, color=AppColors.PRIMARY),
                        ft.Text(ev['title'], size=15, weight="bold", color=AppColors.TEXT_PRIMARY, expand=True),
                        ft.Icon(ft.Icons.ARROW_FORWARD_IOS, size=12, color=AppColors.BORDER)
                    ], spacing=10),
                    padding=15,
                    bgcolor=AppColors.SURFACE_VARIANT,
                    border_radius=10,
                    on_click=lambda e, ev=ev: (page.close(agenda_dlg), open_event_detail_dialog(ev, day))
                )
            )

        if not agenda_items:
            agenda_items.append(
                ft.Container(
                    content=ft.Text("오늘 등록된 일정이 없습니다.", color=AppColors.TEXT_SECONDARY),
                    alignment=ft.alignment.center,
                    expand=True,
                    padding=40
                )
            )

        agenda_dlg = ft.AlertDialog(
            content=ft.Container(
                bgcolor=AppColors.SURFACE,
                padding=10,
                width=400,
                height=500,
                content=ft.Column([
                    ft.Row([
                        ft.Text(f"{m}월 {day}일 {wd}요일", size=22, weight="bold", color=AppColors.TEXT_PRIMARY),
                        ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color=AppColors.PRIMARY, icon_size=32, 
                                      on_click=lambda _: (page.close(agenda_dlg), open_event_editor_dialog(day))),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=10, color="transparent"),
                    ft.Column(agenda_items, spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
                ])
            ),
            actions=[ft.TextButton("닫기", on_click=lambda _: page.close(agenda_dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=20),
        )
        page.open(agenda_dlg)
        page.update()

    def open_event_detail_dialog(ev, day):
        # [NEW] Helper for pretty date formatting
        def format_pretty_date(date_str):
            if not date_str: return "-"
            try:
                # Flexible parsing for both YYYY-MM-DD HH:MM and YYYY-MM-DDTHH:MM
                clean_str = date_str.replace("T", " ")[:16]
                dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M")
                wd_map = ["일", "월", "화", "수", "목", "금", "토"] # wd starts from 0=Sun in some contexts, but dt.weekday() is 0=Mon
                wd_map = ["월", "화", "수", "목", "금", "토", "일"]
                wd = wd_map[dt.weekday()]
                return f"{dt.year}년 {dt.month}월 {dt.day}일 ({wd})"
            except Exception as e:
                log_debug(f"Date format err: {e}")
                return date_str

        def delete_ev(e):
            async def _del():
                try:
                    await calendar_service.delete_event(ev['id'], current_user_id)
                    page.snack_bar = ft.SnackBar(ft.Text("삭제되었습니다."), bgcolor="green"); page.snack_bar.open=True
                    page.close(dlg_det)
                    load()
                    page.update()
                except PermissionError as perm_err:
                    page.snack_bar = ft.SnackBar(ft.Text(str(perm_err)), bgcolor="red"); page.snack_bar.open=True
                    page.update()
                except Exception as ex:
                    log_error(f"Delete Error: {ex}")
                    page.snack_bar = ft.SnackBar(ft.Text(f"삭제 실패: {ex}"), bgcolor="red"); page.snack_bar.open=True
                    page.update()
            page.run_task(_del)

        creator_name = ev.get('profiles', {}).get('full_name', '알 수 없음')
        initials = creator_name[0] if creator_name else "?"
        
        # Header (Standard navigation feel)
        header_row = ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.close(dlg_det), icon_color=AppColors.TEXT_PRIMARY),
            ft.Container(expand=True),
            ft.TextButton("수정", icon=ft.Icons.EDIT, icon_color=AppColors.PRIMARY,
                         on_click=lambda _: (page.close(dlg_det), open_event_editor_dialog(day, existing_event=ev)))
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        # Avatar & Summary
        summary_section = ft.Column([
            ft.Container(
                content=ft.Text(initials, color="white", weight="bold", size=14),
                width=36, height=36, bgcolor="#D81B60", border_radius=18, alignment=ft.alignment.center
            ),
            ft.Text(ev['title'], size=22, weight="bold", color="#2E7D32", text_align=ft.TextAlign.CENTER),
            ft.Row([
                ft.Column([
                    ft.Text(str(ev['start_date'][:4]), size=14, color=AppColors.TEXT_SECONDARY),
                    ft.Text(format_pretty_date(ev['start_date'])[5:], size=18, weight="bold"),
                ], horizontal_alignment="center"),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, size=24, color=AppColors.BORDER),
                ft.Column([
                    ft.Text(str(ev['end_date'][:4]), size=14, color=AppColors.TEXT_SECONDARY),
                    ft.Text(format_pretty_date(ev['end_date'])[5:], size=18, weight="bold"),
                ], horizontal_alignment="center"),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)

        # Info Rows (Only Location/Label for now)
        info_rows = ft.Column([
            ft.Divider(height=1, color=AppColors.BORDER_LIGHT),
        ], spacing=0)

        if ev.get('location'):
            info_rows.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.LABEL_OUTLINE, color="#2E7D32", size=20),
                    title=ft.Text(ev.get('location'), size=15, color=AppColors.TEXT_PRIMARY),
                    dense=True
                )
            )
        
        # Memo Section
        memo_section = ft.Container()
        if ev.get('description'):
            memo_section = ft.Container(
                padding=ft.padding.symmetric(horizontal=15, vertical=10),
                content=ft.Column([
                    ft.Text("상세 메모", size=12, color=AppColors.TEXT_SECONDARY, weight="bold"),
                    ft.Text(ev.get('description'), size=15, color=AppColors.TEXT_PRIMARY),
                ], spacing=5)
            )

        # History Section (Simple)
        history_section = ft.Container(
            padding=ft.padding.only(top=20, bottom=20),
            content=ft.Column([
                ft.Divider(height=1, color=AppColors.BORDER_LIGHT),
                ft.Container(height=20),
                ft.Row([
                    ft.Container(content=ft.Text(initials, color="white", size=10), width=24, height=24, bgcolor="#D81B60", border_radius=12, alignment=ft.alignment.center),
                    ft.Text(f"{creator_name}님이 일정을 등록했습니다", size=14, color=AppColors.TEXT_SECONDARY),
                ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

        # [NEW] Sophisticated Delete Button inside the card
        delete_button_container = ft.Container(
            content=ft.TextButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.DELETE_OUTLINE, size=16, color="#FF5252"),
                    ft.Text("이 일정 삭제하기", size=13, color="#FF5252", weight="w500"),
                ], tight=True, alignment=ft.MainAxisAlignment.CENTER),
                on_click=delete_ev,
            ),
            visible=str(ev.get('created_by')) == str(current_user_id),
            alignment=ft.alignment.center,
            margin=ft.margin.only(top=10, bottom=20)
        )

        # Main Layout (Simplified without social bar)
        detail_card = ft.Container(
            width=400,
            height=500,
            bgcolor=AppColors.SURFACE,
            padding=20,
            content=ft.Column([
                header_row,
                ft.Container(height=20),
                summary_section,
                ft.Container(height=30),
                info_rows,
                memo_section,
                history_section,
                delete_button_container,
                ft.Container(expand=True),
            ], scroll=ft.ScrollMode.AUTO, spacing=0)
        )

        # RBAC Check: Only show Edit button if it's the owner
        is_owner = str(ev.get('created_by')) == str(current_user_id)
        if not is_owner:
            # Hide the edit button if not owner
            header_row.controls[2].visible = False

        dlg_det = ft.AlertDialog(
            content=detail_card,
            shape=ft.RoundedRectangleBorder(radius=20),
            actions=[
                ft.TextButton("닫기", on_click=lambda _: page.close(dlg_det))
            ]
        )
        page.open(dlg_det)
        page.update()

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

    def open_staff_day_ledger(day):
        y, m = view_state["year"], view_state["month"]
        current_day_evs = [ev for ev in view_state["events"] if not ev.get('is_virtual') and str(ev.get('start_date', '')).startswith(f"{y}-{m:02d}-{day:02d}")]
        
        # 1. Controls
        staff_dd = ft.Dropdown(label="직원 선택", width=160)
        substitute_tf = ft.TextField(label="기타 성함 (대타)", width=150, hint_text="이름 직접 입력")
        
        type_dd = ft.Dropdown(
            label="유형", width=120,
            options=[
                ft.dropdown.Option("absence", "결근"),
                ft.dropdown.Option("overtime", "연장"),
                ft.dropdown.Option("additional", "추가")
            ], value="absence"
        )
        
        # Time controls for 'Additional'
        tf_start = ft.TextField(label="시작", value="09:00", width=80, visible=False)
        tf_end = ft.TextField(label="종료", value="18:00", width=80, visible=False)
        
        # Duration for 'Overtime'
        ext_options = [ft.dropdown.Option(str(x/2), f"{x/2}시간") for x in range(1, 21)]
        extension_dd = ft.Dropdown(label="연장 시간", width=100, options=ext_options, visible=False, value="1.0")

        def on_type_change(e):
            val = type_dd.value
            tf_start.visible = (val == "additional")
            tf_end.visible = (val == "additional")
            extension_dd.visible = (val == "overtime")
            page.update()
        type_dd.on_change = on_type_change

        # 2. Existing Records List
        existing_list = ft.Column(spacing=5)
        def refresh_existing():
            existing_list.controls.clear()
            for ev in current_day_evs:
                existing_list.controls.append(
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color="green" if "결근" not in ev['title'] else "red", size=14),
                        ft.Text(ev['title'], size=14, expand=True),
                        ft.IconButton(ft.Icons.DELETE, icon_color="red", icon_size=16, on_click=lambda e, eid=ev['id']: page.run_task(delete_and_refresh, eid))
                    ])
                )
            if not current_day_evs:
                existing_list.controls.append(ft.Text("확정된 기록 없음", size=12, color="grey"))
            page.update()

        async def delete_and_refresh(eid):
            await delete_staff_event(eid)
            nonlocal current_day_evs
            current_day_evs = [ev for ev in current_day_evs if ev['id'] != eid]
            refresh_existing()
            load()

        async def add_record():
            name = ""
            eid = None
            if staff_dd.value:
                eid = staff_dd.value
                name = next((opt.text for opt in staff_dd.options if opt.key == eid), "Unknown")
            elif substitute_tf.value:
                name = substitute_tf.value.strip()
                # eid stays None for substitutes
            else:
                page.open(ft.SnackBar(ft.Text("직원을 선택하거나 이름을 입력하세요."), bgcolor="red"))
                return

            t_val = type_dd.value
            st_time, et_time = "09:00", "18:00"
            prefix, color = "🟢", "green"
            title_suffix = ""

            if t_val == "absence":
                st_time, et_time = "00:00", "00:00"
                prefix, color = "❌", "red"
                title_suffix = "결근"
            elif t_val == "additional":
                st_time, et_time = tf_start.value, tf_end.value
                prefix, color = "⭐", "blue"
                title_suffix = f"({st_time}~{et_time})"
            elif t_val == "overtime":
                prefix, color = "🔥", "green"
                # Find baseline for eid on this day
                if not eid:
                    page.open(ft.SnackBar(ft.Text("연장은 기존 직원에 대해서만 가능합니다."), bgcolor="red"))
                    return
                # Look for virtual event in state
                baseline = None
                for ev in view_state["events"]:
                    if ev.get('is_virtual') and ev.get('employee_id') == eid and ev.get('start_date', '').startswith(f"{y}-{m:02d}-{day:02d}"):
                        baseline = ev; break
                
                if not baseline:
                    page.open(ft.SnackBar(ft.Text("해당 직원의 기본 스케줄을 찾을 수 없습니다."), bgcolor="red"))
                    return
                
                try:
                    st_time = baseline['start_date'].split('T')[1][:5]
                    et_base = baseline['end_date'].split('T')[1][:5]
                    ext_h = float(extension_dd.value)
                    bh, bm = map(int, et_base.split(':'))
                    # Calculate new end
                    total_m = bh * 60 + bm + int(ext_h * 60)
                    nh, nm = divmod(total_m, 60)
                    if nh >= 24: nh -= 24 # Simplified wrap around
                    et_time = f"{nh:02d}:{nm:02d}"
                    title_suffix = f"({ext_h}h 연장 / {st_time}~{et_time})"
                except Exception as calc_err:
                    log_error(f"Overtime calculation error: {calc_err}")
                    page.open(ft.SnackBar(ft.Text("연장 시간 계산 오류"), bgcolor="red"))
                    return

            title = f"{prefix} {name} {title_suffix}".strip()

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

                payload = {
                    "title": title,
                    "start_date": f"{y}-{m:02d}-{day:02d}T{st_time}:00",
                    "end_date": f"{y}-{m:02d}-{day:02d}T{et_time}:00",
                    "color": color,
                    "employee_id": eid,
                    "is_work_schedule": True,
                    "created_by": page.session.get("user_id"),
                    "channel_id": channel_id
                }
                res = await asyncio.to_thread(lambda: client.from_("calendar_events").insert(payload).execute())
                if res.data:
                    current_day_evs.append(res.data[0])
                    refresh_existing()
                    load()
                    page.open(ft.SnackBar(ft.Text("기록되었습니다."), bgcolor="green"))
            finally:
                if client:
                    try:
                        client.session.close()
                    except Exception:
                        pass

        async def fetch_staff():
            from services.auth_service import auth_service
            from postgrest import SyncPostgrestClient
            client = None
            try:
                headers = auth_service.get_auth_headers()
                if not headers: return
                url = os.environ.get("SUPABASE_URL")
                if not url: return
                client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public", timeout=20)
                res = await asyncio.to_thread(lambda: client.from_("labor_contracts").select("id, employee_name, contract_end_date").eq("user_id", current_user_id).order("created_at", desc=True).execute())
                data = res.data or []
                unique_staff = {}
                for d in data:
                    nm = d['employee_name'].strip()
                    if nm in unique_staff: continue
                    ed = d.get('contract_end_date')
                    if ed:
                        try:
                            if datetime.strptime(ed, "%Y-%m-%d").date() < datetime.now().date(): continue
                        except ValueError:
                            pass  # Invalid date format
                    unique_staff[nm] = d['id']
                staff_dd.options = [ft.dropdown.Option(eid, nm) for nm, eid in unique_staff.items()]
                page.update()
            finally:
                if client:
                    try:
                        client.session.close()
                    except Exception:
                        pass

        dlg = ft.AlertDialog(
            title=ft.Text(f"{y}/{m}/{day} 일일 근무 장부"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("확정된 기록 (수정/삭제)", size=12, weight="bold"),
                    existing_list,
                    ft.Divider(),
                    ft.Text("기록 추가", size=12, weight="bold"),
                    ft.Row([staff_dd, ft.Text("또는"), substitute_tf], vertical_alignment="center"),
                    ft.Row([type_dd, extension_dd, tf_start, ft.Text("~", visible=False), tf_end], vertical_alignment="center"),
                    ft.Row([ft.ElevatedButton("기록하기", on_click=lambda e: page.run_task(add_record), expand=True)], alignment="center"),
                ], tight=True, scroll=ft.ScrollMode.AUTO, spacing=10),
                width=450, height=500
            ),
            actions=[ft.TextButton("닫기", on_click=lambda _: page.close(dlg))]
        )
        
        # Link start/end visibility to tilde
        tilde_txt = dlg.content.content.controls[5].controls[3]
        def on_type_change_sync(e):
            on_type_change(e)
            tilde_txt.visible = tf_start.visible
            page.update()
        type_dd.on_change = on_type_change_sync

        page.open(dlg)
        refresh_existing()
        page.run_task(fetch_staff)

    def open_event_editor_dialog(day, init_title="", existing_event=None):
        try:
            target_date = datetime(view_state['year'], view_state['month'], day)
        except: target_date = datetime.now()

        # If editing, use existing data
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
        
        status_msg = ft.Text("", size=11, color="orange", italic=True)
        saved_fname = None
        
        link_tf = ft.TextField(
            label="파일 업로드", 
            icon=ft.Icons.ATTACH_FILE, 
            read_only=True, 
            expand=True,
            value=existing_event.get("link", "") if existing_event else "",
            suffix=ft.IconButton(
                icon=ft.Icons.UPLOAD_FILE,
                icon_color=AppColors.PRIMARY,
                icon_size=20,
                on_click=lambda _: page.file_picker.pick_files(),
                tooltip="파일 업로드"
            )
        )
        
        title_tf = ft.TextField(label="제목", value=existing_event.get("title", init_title) if existing_event else init_title, autofocus=True)
        loc_tf = ft.TextField(label="장소", icon=ft.Icons.LOCATION_ON,
                             value=existing_event.get("location", "") if existing_event else "")
        memo_tf = ft.TextField(label="메모", multiline=True, min_lines=2, icon=ft.Icons.NOTE,
                              value=existing_event.get("description", "") if existing_event else "")
        
        # Simple stack for link field and status
        link_section = ft.Column([
            link_tf,
            status_msg
        ], spacing=2)

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

                # [CLEAN] Use async do_upload function
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
            profiles = await calendar_service.load_profiles(channel_id)
            
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
                "description": memo_tf.value,
                "participant_ids": evt_state["participants"],
                "created_by": current_user_id,
                # Legacy compatibility or extra tracking
                "user_id": current_user_id,
                "channel_id": channel_id
            }
            
            async def _save_async():
                try:
                    if existing_event:
                        await calendar_service.update_event(existing_event["id"], data, current_user_id)
                    else:
                        await calendar_service.create_event(data)
                    page.snack_bar = ft.SnackBar(ft.Text("저장 완료!"))
                    page.snack_bar.open=True
                    page.close(dlg_edit)
                    load()
                    page.update()
                except PermissionError as perm_err:
                    page.snack_bar = ft.SnackBar(ft.Text(str(perm_err)), bgcolor="red"); page.snack_bar.open=True; page.update()
                except Exception as ex:
                    print(f"Save Error: {ex}")
                    page.snack_bar = ft.SnackBar(ft.Text(f"오류: {ex}"), bgcolor="red"); page.snack_bar.open=True; page.update()
            
            page.run_task(_save_async)



        dlg_edit = ft.AlertDialog(
            title=ft.Text("일정 수정" if existing_event else "새 일정"),
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

    def on_swipe(e: ft.DragEndEvent):
        # Velocity-based horizontal swipe detection
        if e.primary_velocity is not None:
            if e.primary_velocity > 400: # Swiping Right -> Prev Month
                change_m(-1)
            elif e.primary_velocity < -400: # Swiping Left -> Next Month
                change_m(1)

    month_label = ft.Text(f"{view_state['year']}년 {view_state['month']}월", size=20, weight="bold", color="#0A1929")

    def go_today():
        now = datetime.now()
        view_state["year"] = now.year
        view_state["month"] = now.month
        load()

    def open_event_dialog():
        open_event_editor_dialog(datetime.now().day)

    # [NEW] Drawer & Channel Switching
    def switch_channel(ch):
        page.session.set("channel_id", ch["id"])
        page.session.set("channel_name", ch["name"])
        page.session.set("user_role", ch["role"])
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
        u_name = page.session.get("display_name") or "User"
        
        # Fetch Channels
        from services.auth_service import auth_service
        from services.channel_service import channel_service
        token = auth_service.get_access_token()
        channels = channel_service.get_user_channels(current_user_id, token)
        
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
                on_click=lambda _: page.snack_bar.open_snack_bar(ft.SnackBar(ft.Text("다중 캘린더 기능은 준비 중입니다!"), open=True)) or page.update()
            )
        )
        return drawer

    # Apply Drawer
    drawer = build_drawer()
    page.drawer = drawer
    page.update()

    # [Standardized Header]
    header = AppHeader(
        title_text=ft.Row([
            ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda _: change_m(-1), icon_color=AppColors.TEXT_PRIMARY), 
            month_label, 
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda _: change_m(1), icon_color=AppColors.TEXT_PRIMARY)
        ], alignment=ft.MainAxisAlignment.CENTER),
        left_button=ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW, icon_color=AppColors.TEXT_PRIMARY, on_click=lambda _: page.go_back(), tooltip="뒤로"),
            ft.IconButton(ft.Icons.MENU, icon_color=AppColors.TEXT_PRIMARY, on_click=lambda _: page.open(drawer), tooltip="메뉴"),
        ], spacing=0),
        action_button=ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: load(), icon_color=AppColors.TEXT_PRIMARY)
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
                        page.run_task(load_async)
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
                        page.run_task(load_async)

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

    page.run_task(initial_load_delayed)
    # Register the realtime task properly
    rt_task = page.run_task(realtime_handler)

    # Simple cleanup logic when view is logically destroyed
    def cleanup():
        log_info("CALENDAR: Performing cleanup...")
        state["is_active"] = False
    
    # We can't easily hook into view destruction in Flet without complex route logic, 
    # but the loop in realtime_handler checks page.is_running.

    log_debug("Exiting get_calendar_controls (Returning UI)")
    
    # [FIX] Return layout without NavigationRail
    return [
        ft.SafeArea(expand=True, content=
            ft.Column([
                header,
                # debug_text removed
                ft.Container(
                    expand=True,
                    padding=ft.padding.only(left=5, right=5, bottom=0, top=0),
                    content=ft.GestureDetector(
                        on_horizontal_drag_end=on_swipe,
                        expand=True,
                        content=ft.Column([
                            # Weekday header row
                            ft.Row([
                                ft.Container(content=ft.Text("월", color="black", size=13, text_align="center", weight="bold"), expand=True, alignment=ft.alignment.center, padding=5),
                                ft.Container(content=ft.Text("화", color="black", size=13, text_align="center", weight="bold"), expand=True, alignment=ft.alignment.center, padding=5),
                                ft.Container(content=ft.Text("수", color="black", size=13, text_align="center", weight="bold"), expand=True, alignment=ft.alignment.center, padding=5),
                                ft.Container(content=ft.Text("목", color="black", size=13, text_align="center", weight="bold"), expand=True, alignment=ft.alignment.center, padding=5),
                                ft.Container(content=ft.Text("금", color="black", size=13, text_align="center", weight="bold"), expand=True, alignment=ft.alignment.center, padding=5),
                                ft.Container(content=ft.Text("토", color="blue", size=13, text_align="center", weight="bold"), expand=True, alignment=ft.alignment.center, padding=5),
                                ft.Container(content=ft.Text("일", color="red", size=13, text_align="center", weight="bold"), expand=True, alignment=ft.alignment.center, padding=5),
                            ], spacing=0),
                            # Grid
                            calendar_container
                        ], spacing=0, expand=True)
                    )
                )
            ], expand=True, spacing=0)
        )
    ]
