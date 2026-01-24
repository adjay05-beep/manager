import flet as ft
import datetime
from datetime import datetime as dt_class, time as time_class # Alias to avoid conflict if needed, or just standard
# Actually, simpler:
from datetime import datetime, time, timezone
import urllib.parse
import calendar
import tempfile
import os
import threading
import asyncio
import time as sleep_module # use to avoid name conflict with datetime.time
from db import supabase
from voice_service import transcribe_audio

# Set to True/False for debugging
DEBUG_MODE = True

# --- [4] 채팅 화면 (Jandi Style) ---
def get_chat_controls(page: ft.Page, navigate_to):
    state = {"current_topic_id": None, "edit_mode": False}
    current_user_id = "00000000-0000-0000-0000-000000000001"
    
    def on_topic_reorder(e: ft.ReorderableListViewReorderEvent):
        # Sync to DB
        # Note: In ReorderableListView mode, we get controls from the list within container
        controls = topic_list_container.content.controls
        moved_control = controls.pop(e.old_index)
        controls.insert(e.new_index, moved_control)
        
        # Update display_order for all visible topics
        # Lower index = higher priority/top (or vice-versa, let's go with top-to-bottom)
        try:
            for idx, ctrl in enumerate(controls):
                tid = ctrl.data # Storing ID in data attribute
                supabase.table("chat_topics").update({"display_order": 1000 - idx}).eq("id", tid).execute()
        except Exception as ex:
            print(f"Reorder DB Sync Error: {ex}")
        
        page.update()

    topic_list_container = ft.Container(expand=True)
    message_list_view = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=15)
    
    msg_input = ft.TextField(
        hint_text="메시지 입력...", 
        expand=True, 
        border_radius=10, 
        bgcolor="white", 
        border_color="#E0E0E0",
        on_submit=lambda e: send_message()
    )
    
    chat_header_title = ft.Text("스레드를 선택하세요", weight="bold", size=18, color="#333333")
    
    def load_topics(update_ui=True):
        try:
            res = supabase.table("chat_topics").select("*").execute()
            topics = res.data or []
            
            # Reorder handles are only needed in Edit Mode.
            # Normal Mode: Column (clean, no handles). Edit Mode: ReorderableListView.
            if state["edit_mode"]:
                list_view = ft.ReorderableListView(
                    expand=True, 
                    on_reorder=on_topic_reorder,
                    show_default_drag_handles=False # Hide the right-side handle
                )
            else:
                list_view = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=0)

            # Sort
            sorted_topics = sorted(topics, key=lambda x: (x.get('is_priority', False), x.get('display_order', 0) or 0, x.get('created_at', '')), reverse=True)

            # [OPTIMIZATION] Batch Fetch Reading Status
            read_res = supabase.table("chat_user_reading").select("topic_id, last_read_at").eq("user_id", current_user_id).execute()
            reading_map = {r['topic_id']: r['last_read_at'] for r in read_res.data} if read_res.data else {}
            
            # [OPTIMIZATION] Batch Fetch Recent Messages to count unreads in memory
            # Get the earliest last_read_at to fetch only necessary messages
            default_old = "1970-01-01T00:00:00Z"
            earliest_read = min(reading_map.values()) if reading_map else default_old
            
            # Limit message fetch to a reasonable window or just since earliest_read
            msg_res = supabase.table("chat_messages").select("topic_id, created_at").gt("created_at", earliest_read).execute()
            recent_msgs = msg_res.data or []
            
            # Pre-group counts
            unread_counts = {}
            for m in recent_msgs:
                tid_m = m['topic_id']
                lr_m = reading_map.get(tid_m, default_old)
                if m['created_at'] > lr_m:
                    unread_counts[tid_m] = unread_counts.get(tid_m, 0) + 1

            for t in sorted_topics:
                tid = t['id']
                is_selected = tid == state["current_topic_id"]
                is_priority = t.get('is_priority', False)
                unread_count = unread_counts.get(tid, 0)

                # Row construction
                row_items = []
                if state["edit_mode"]:
                    # Visual handle on the left (since ft.DragHandle is missing in this version)
                    row_items.append(ft.Icon(ft.Icons.DRAG_HANDLE_ROUNDED, size=20, color="#BDBDBD"))
                else:
                    row_items.append(ft.IconButton(
                        ft.Icons.PRIORITY_HIGH_ROUNDED, 
                        icon_color="#FF5252" if is_priority else "#BDBDBD", 
                        icon_size=16,
                        on_click=lambda e, tid=tid, p=is_priority: toggle_priority(tid, p)
                    ))
                
                row_items.append(ft.Text(t['name'], size=14, weight="bold" if is_selected else "normal", color="#1A1A1A", expand=True))
                
                if not state["edit_mode"] and unread_count > 0:
                    row_items.append(ft.Container(
                        content=ft.Text(str(unread_count), size=10, color="white", weight="bold"),
                        bgcolor="#FF5252",
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        border_radius=10
                    ))

                item = ft.Container(
                    key=str(tid),
                    data=tid,
                    content=ft.Row(row_items, spacing=5),
                    padding=ft.padding.symmetric(horizontal=10, vertical=8),
                    border_radius=8,
                    bgcolor="#F0F7FF" if is_selected else "transparent",
                    on_click=lambda e, topic=t: select_topic(topic),
                    ink=True
                )
                
                if state["edit_mode"]:
                    # Wrap the item in a draggable that doesn't add forced right handles
                    list_view.controls.append(
                        ft.ReorderableDraggable(
                            index=sorted_topics.index(t),
                            content=item
                        )
                    )
                else:
                    list_view.controls.append(item)
            
            topic_list_container.content = list_view
            if DEBUG_MODE: print(f"DEBUG: Setting container content to {type(list_view).__name__} with {len(list_view.controls)} items")
            if update_ui: page.update()
        except Exception as e:
            print(f"Load Topics Fail: {e}")
            import traceback
            traceback.print_exc()

    def toggle_priority(tid, current_val):
        try:
            supabase.table("chat_topics").update({"is_priority": not current_val}).eq("id", tid).execute()
            load_topics(True)
        except Exception as e:
            print(f"Priority Error: {e}")

    def select_topic(topic):
        state["current_topic_id"] = topic['id']
        chat_header_title.value = topic['name']
        msg_input.disabled = False
        
        # [NEW] Show Loading Indicator to prevent freeze
        message_list_view.controls = [
            ft.Container(
                content=ft.Column([
                    ft.ProgressRing(color="#00C73C"),
                    ft.Text("메시지를 불러오는 중...", color="#666666", size=12)
                ], horizontal_alignment="center", spacing=10),
                alignment=ft.alignment.center,
                expand=True
            )
        ]
        page.update()

        # Mark as read
        try:
            now_utc = datetime.now(timezone.utc).isoformat()
            supabase.table("chat_user_reading").upsert({
                "topic_id": topic['id'],
                "user_id": current_user_id,
                "last_read_at": now_utc
            }).execute()
        except: pass
            
        load_topics(True) 
        # [NEW] Run loading as a non-blocking task
        page.run_task(load_messages_async)

    async def load_messages_async():
        if not state["current_topic_id"]: return
        try:
            # Fetch data in background
            res = supabase.table("chat_messages").select("id, topic_id, user_id, content, image_url, created_at, profiles(username, full_name)").eq("topic_id", state["current_topic_id"]).order("created_at", desc=True).limit(50).execute()
            messages = res.data or []
            messages.reverse() # Show oldest at top
            
            new_controls = []

            def open_preview(url):
                preview_dlg = ft.AlertDialog(
                    content=ft.Image(src=url, fit=ft.ImageFit.CONTAIN),
                    actions=[ft.TextButton("닫기", on_click=lambda _: page.close(preview_dlg))]
                )
                page.open(preview_dlg)
            
            for m in messages:
                is_me = str(m['user_id']) == current_user_id
                prof_data = m.get('profiles')
                if isinstance(prof_data, list) and prof_data: prof_data = prof_data[0]
                user_name = prof_data.get('full_name', '익명') if prof_data else "익명"
                
                created_dt = dt_class.fromisoformat(m['created_at'].replace("Z", "+00:00"))
                ampm = "오후" if created_dt.hour >= 12 else "오전"
                h = created_dt.hour % 12
                if h == 0: h = 12
                time_str = f"{ampm} {h}:{created_dt.minute:02d}"
                
                content_elements = []
                img_url = m.get('image_url')
                if img_url:
                    content_elements.append(
                        ft.Container(
                            content=ft.Image(src=img_url, width=250, height=250, fit=ft.ImageFit.CONTAIN, border_radius=10),
                            padding=5, border=ft.border.all(1, "#DDDDDD"), border_radius=10, bgcolor="white",
                            on_click=lambda e, u=img_url: open_preview(u)
                        )
                    )
                
                if m.get('content') and m['content'] != "[이미지 파일]":
                    content_elements.append(ft.Text(m['content'], size=14, color="black"))
                
                bubble_bg = "#FFFFFF" if is_me else "#F1F1F1"
                content_box = ft.Container(
                    content=ft.Column(content_elements, spacing=5),
                    bgcolor=bubble_bg, padding=12, border_radius=15, width=260,
                    border=ft.border.all(1, "#E0E0E0") if is_me else None
                )
                
                time_text = ft.Text(time_str, size=10, color="#999999")
                
                if is_me:
                    bubble_row = ft.Row([time_text, content_box], alignment=ft.MainAxisAlignment.END, vertical_alignment=ft.CrossAxisAlignment.END, spacing=5)
                else:
                    bubble_row = ft.Row([
                        ft.CircleAvatar(content=ft.Text(user_name[0], size=12), radius=15, bgcolor="#EEEEEE", color="black"),
                        content_box, time_text
                    ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.END, spacing=5)
                
                new_controls.append(ft.Container(
                    content=ft.Column([
                        ft.Text(user_name, size=11, weight="bold", color="#666666") if not is_me else ft.Container(),
                        bubble_row
                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.START if not is_me else ft.CrossAxisAlignment.END),
                    padding=ft.padding.symmetric(vertical=5)
                ))
            
            message_list_view.controls = new_controls
            page.update()
        except Exception as e:
            print(f"Async Load Error: {e}")
            message_list_view.controls = [ft.Text(f"로드 실패: {e}", color="red")]
            page.update()

    # Maintain old load_messages for compatibility with realtime callback if needed
    def load_messages():
        page.run_task(load_messages_async)

    def send_message(content=None, image_url=None):
        # Use pending URL if not provided explicitly
        final_image_url = image_url or state.get("pending_image_url")
        final_content = content or msg_input.value
        
        # [Debug] Print state before insert
        print(f"DEBUG: Attempting to send message. Content='{final_content}', Image='{final_image_url}'")
        
        if not final_content and not final_image_url: return
        if not state["current_topic_id"]: return
        
        # If we have an image but no content, use default label
        if final_image_url and not final_content:
            final_content = "[이미지 파일]"

        try:
            res = supabase.table("chat_messages").insert({
                "topic_id": state["current_topic_id"],
                "content": final_content,
                "image_url": final_image_url,
                "user_id": "00000000-0000-0000-0000-000000000001"
            }).execute()
            
            print(f"DEBUG: Insert Success -> {res.data}")
            
            # Reset
            msg_input.value = ""
            state["pending_image_url"] = None
            pending_container.visible = False
            pending_container.content = ft.Container() # Clear
            load_messages()
        except Exception as e:
            import traceback
            print(f"Send Error: {e}\n{traceback.format_exc()}")
            page.snack_bar = ft.SnackBar(ft.Text(f"전송 실패: {e}"), bgcolor="red", open=True); page.update()

    # Pending Attachment UI
    pending_container = ft.Container(visible=False, padding=10, bgcolor="#3D4446", border_radius=10)
    
    # Local FilePicker to avoid global conflict
    chat_file_picker = ft.FilePicker()
    page.overlay.append(chat_file_picker)
    # [FIX] Do not call page.update() here, it causes transition freeze.
    # navigate_to() will call update() after adding all controls.

    def on_chat_file_result(e: ft.FilePickerResultEvent):
        if e.files and state["current_topic_id"]:
            f = e.files[0]
            try:
                import urllib.parse
                safe_name = urllib.parse.quote(f.name.replace(" ", "_"))
                fname = f"chat_{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_name}"
                state["pending_file_name"] = fname # Store for on_upload
                
                snack = ft.SnackBar(ft.Text("이미지 전송 준비 중..."), open=True)
                page.snack_bar = snack; page.update()
                
                # [STRATEGY] Use Signed URL for Web compatibility
                try:
                    signed_url = supabase.storage.from_("uploads").create_signed_upload_url(fname)
                    print(f"DEBUG: Signed URL -> {signed_url}")
                    
                    state["pending_image_url"] = f"{supabase.url}/storage/v1/object/public/uploads/{fname}"
                    
                    # Tell local picker to upload
                    chat_file_picker.upload(
                        files=[
                            ft.FilePickerUploadFile(
                                name=f.name,
                                upload_url=signed_url,
                                method="PUT"
                            )
                        ]
                    )
                except Exception as storage_ex:
                    print(f"DEBUG: Fallback to direct upload... ({storage_ex})")
                    if f.path:
                        with open(f.path, "rb") as file_data:
                            supabase.storage.from_("uploads").upload(fname, file_data.read())
                        update_pending_ui(state["pending_image_url"])
                    else:
                        raise storage_ex
                
                page.update()
            except Exception as ex:
                import traceback
                print(f"Chat Upload Error Detail ->\n{traceback.format_exc()}")
                page.snack_bar = ft.SnackBar(ft.Text(f"오류: {str(ex)}"), bgcolor="red", open=True)
                page.update()

    def on_chat_upload_progress(e: ft.FilePickerUploadEvent):
        # [FIX] Avoid e.status (AttributeError). Use e.error and progress.
        print(f"DEBUG: Upload Progress -> {e.file_name}: {e.progress}")
        if e.error:
            print(f"DEBUG: Upload Error -> {e.error}")
            page.snack_bar = ft.SnackBar(ft.Text(f"업로드 실패: {e.file_name}"), bgcolor="red", open=True); page.update()
        elif e.progress == 1.0:
            # Upload finished
            update_pending_ui(state.get("pending_image_url"))
            page.snack_bar = ft.SnackBar(ft.Text("이미지 로드 완료!"), bgcolor="green", open=True)
            page.update()

    def update_pending_ui(public_url):
        if not public_url: return
        pending_container.content = ft.Row([
            ft.Image(
                src=public_url, 
                width=50, 
                height=50, 
                border_radius=5, 
                fit=ft.ImageFit.COVER,
                error_content=ft.Icon(ft.Icons.BROKEN_IMAGE, color="red")
            ),
            ft.Column([
                ft.Text("이미지 준비 완료", size=12, weight="bold", color="white"),
                ft.Text("전송 버튼을 눌러 발송하세요.", size=10, color="white70"),
            ], spacing=2, tight=True),
            ft.IconButton(ft.Icons.CANCEL, icon_color="red", on_click=lambda _: clear_pending())
        ], spacing=10)
        pending_container.visible = True
        page.update()

    def clear_pending():
        state["pending_image_url"] = None
        pending_container.visible = False
        page.update()
    
    # Bind local picker events
    chat_file_picker.on_result = on_chat_file_result
    chat_file_picker.on_upload = on_chat_upload_progress

    def toggle_edit_mode():
        if DEBUG_MODE: print(f"DEBUG: toggle_edit_mode triggered. Current: {state['edit_mode']}")
        state["edit_mode"] = not state["edit_mode"]
        # Update button text manually since it's already rendered
        if edit_btn_ref.current:
            edit_btn_ref.current.text = "완료" if state["edit_mode"] else "편집"
            edit_btn_ref.current.update()
        
        load_topics(True)
        # Ensure the whole sidebar knows about the change if needed
        if sidebar_content_ref.current:
            sidebar_content_ref.current.update()
        if DEBUG_MODE: print(f"DEBUG: toggle_edit_mode done. New: {state['edit_mode']}")

    def open_create_topic_dialog(e):
        new_name = ft.TextField(label="새 스레드 이름", autofocus=True)
        def create_it(e):
            if new_name.value:
                try:
                    supabase.table("chat_topics").insert({"name": new_name.value, "display_order": 0}).execute()
                    page.close(dlg)
                    load_topics(True)
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(ft.Text(f"오류: {ex}"), bgcolor="red", open=True); page.update()
        dlg = ft.AlertDialog(
            title=ft.Text("새 스레드 만들기"),
            content=new_name,
            actions=[ft.TextButton("취소", on_click=lambda _: page.close(dlg)), ft.TextButton("만들기", on_click=create_it)]
        )
        page.open(dlg)

    sidebar_content_ref = ft.Ref[ft.Column]()
    edit_btn_ref = ft.Ref[ft.TextButton]()
    sidebar = ft.Container(
        width=240, bgcolor="white",
        border=ft.border.only(right=ft.border.BorderSide(1, "#EEEEEE")),
        content=ft.Column(
            ref=sidebar_content_ref,
            controls=[
                ft.Container(
                    ft.Text("THE MANAGER", size=18, weight="bold", color="#1A1A1A", style=ft.TextStyle(letter_spacing=1)), 
                    padding=25, alignment=ft.alignment.center
                ),
                ft.Divider(height=1, color="#F0F0F0"),
                ft.Container(
                    content=ft.Row([
                        ft.Text("스레드 목록", weight="bold", size=13, color="#666666"), 
                        ft.Row([
                            ft.TextButton(
                                ref=edit_btn_ref,
                                text="완료" if state["edit_mode"] else "편집",
                                style=ft.ButtonStyle(color="#00C73C"),
                                on_click=lambda _: toggle_edit_mode()
                            ),
                            ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, icon_color="#00C73C", icon_size=20, on_click=open_create_topic_dialog)
                        ], spacing=0)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
                    padding=ft.padding.only(left=20, right=10, top=15, bottom=5)
                ),
                ft.Container(content=topic_list_container, expand=True, padding=ft.padding.only(left=8, right=8)),
                ft.Container(
                    content=ft.TextButton("🏠 홈으로 가기", style=ft.ButtonStyle(color="#666666"), on_click=lambda _: navigate_to("home")), 
                    padding=15, alignment=ft.alignment.center
                )
            ]
        )
    )

    main_area = ft.Container(
        expand=True, bgcolor="white",
        content=ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Row([
                        ft.Icon(ft.Icons.CHAT_BUBBLE_ROUNDED, color="#00C73C", size=20),
                        chat_header_title
                    ], spacing=10),
                    ft.IconButton(ft.Icons.REFRESH_ROUNDED, icon_color="#666666", on_click=lambda _: load_topics(True))
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
                padding=ft.padding.symmetric(horizontal=20, vertical=15), 
                border=ft.border.only(bottom=ft.border.BorderSide(1, "#EEEEEE"))
            ),
            ft.Divider(height=1, color="#EEEEEE"), # [FIX] Clear line separation
            ft.Container(content=message_list_view, expand=True, padding=ft.padding.symmetric(horizontal=20, vertical=10), bgcolor="#F9F9F9"),
            ft.Divider(height=1, color="#EEEEEE"), # [FIX] Clear line separation
            ft.Container(
                content=ft.Column([
                    pending_container,
                    ft.Row([
                        ft.IconButton(ft.Icons.ADD_LINK_ROUNDED, icon_color="#666666", on_click=lambda _: chat_file_picker.pick_files()),
                        msg_input, 
                        ft.IconButton(ft.Icons.SEND_ROUNDED, icon_color="#00C73C", icon_size=28, on_click=lambda _: send_message())
                    ], spacing=10)
                ]), 
                padding=15, 
                bgcolor="white"
            )
        ])
    )
    # Update state for light theme
    # Update state for light theme
    chat_header_title.color = "#1A1A1A"
    msg_input.bgcolor = "#F5F5F5"
    msg_input.color = "black"
    msg_input.border_color = "transparent"
    msg_input.hint_style = ft.TextStyle(color="#999999")

    # --- [NEW] REALTIME INTEGRATION (Zero Latency) ---
    async def realtime_task():
        # [OPTIMIZATION] Lazy start: Wait for UI to stabilize
        await asyncio.sleep(2)
        if DEBUG_MODE: print("REALTIME: Engine starting...")
        
        try:
            rt_client = supabase.get_realtime_client()
            if not rt_client: 
                if DEBUG_MODE: print("REALTIME: Client init failed")
                return
            
            # 1. Listen for new messages
            msg_channel = rt_client.channel("realtime-msgs")
            
            def handle_new_msg(payload):
                if DEBUG_MODE: print(f"REALTIME: New message -> {payload}")
                load_topics(True)
                new_tid = payload.get('record', {}).get('topic_id')
                if str(new_tid) == str(state["current_topic_id"]):
                    load_messages()

            msg_channel.on("postgres_changes", {"event": "INSERT", "schema": "public", "table": "chat_messages"}, handle_new_msg)
            
            # 2. Listen for topic changes
            topic_channel = rt_client.channel("realtime-topics")
            def handle_topic_change(payload):
                if DEBUG_MODE: print(f"REALTIME: Topic change -> {payload}")
                load_topics(True)

            topic_channel.on("postgres_changes", {"event": "*", "schema": "public", "table": "chat_topics"}, handle_topic_change)

            await rt_client.connect()
            await msg_channel.subscribe()
            await topic_channel.subscribe()
            
            if DEBUG_MODE: print("REALTIME: Engine connected and subscribed")
            
            while not page.is_disconnected:
                await asyncio.sleep(2)
                
        except Exception as e:
            print(f"REALTIME CRITICAL ERROR: {e}")
            # Do not show snackbar here as it might cause infinite loop or flicker on retry
        finally:
            try: await rt_client.disconnect()
            except: pass

    # Start the realtime bridge with a slight safety delay
    page.run_task(realtime_task)

    load_topics(False)
    # [FIX] Force a quick update to ensure UI is interactive before bridge starts
    if page: page.update()
    
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
            ft.Text("THE MANAGER", size=32, weight="bold", color="white", style=ft.TextStyle(letter_spacing=2)),
            ft.Text("Restaurant Management OS", size=14, color="white70"),
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
        # [STABILITY FIX] Blur removed. Using higher opacity for glass feel.
        bgcolor=ft.Colors.with_opacity(0.2, "white"),
        border=ft.border.all(1, ft.Colors.with_opacity(0.2, "white")),
    )
    
    return [
        ft.Stack([
            # 1. 배경색 (Backup)
            ft.Container(expand=True, bgcolor="#0A1929"),
            
            # 2. 배경 이미지
            ft.Image(
                src="images/login_bg.png",
                fit=ft.ImageFit.COVER,
                opacity=0.7,
                expand=True
            ),
            
            # 3. 로그인 카드 오버레이
            ft.Container(
                content=login_card, 
                alignment=ft.alignment.center, 
                expand=True,
                bgcolor=ft.Colors.with_opacity(0.3, "black")
            )
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
            # [STABILITY FIX] Blur removed
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
            action_btn("팀 스레드", "images/icon_chat.png", "chat"),
            action_btn("마감 점검", "images/icon_check.png", "closing"),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
        ft.Row([
            action_btn("음성 메모", "images/icon_voice.png", "order"),
            action_btn("근무 캘린더", "images/icon_calendar.png", "calendar"),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
    ], spacing=15)

    # 홈 화면 진입 시 배경 이미지 제거 (그라데이션 사용을 위해)
    page.decoration_image = None
    page.update()

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
    # [Refactor] Page Navigation Logic
    # Dialog Conflict Avoidance -> Full Page Switching
    
    now = datetime.now()
    view_state = {"year": now.year, "month": now.month, "today": now.day, "events": []}
    
    # Overlay Management (FilePicker)
    def ensure_overlay(ctrl):
        if ctrl not in page.overlay.controls:
            page.overlay.append(ctrl)

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
                        ev_stack.controls.append(
                            ft.Container(content=ft.Text(display_text, size=8, color="white", no_wrap=True), bgcolor=ev.get('color', '#1DDB16'), padding=2, border_radius=3)
                        )
                    
                    # [Refactor] Navigate to Day View
                    def make_day_click(d_val):
                        return lambda e: show_day_details_dialog(d_val)

                    grid.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Container(date_box, padding=4), 
                                ft.Container(ev_stack, padding=1, height=60, clip_behavior=ft.ClipBehavior.HARD_EDGE) # [FIX] Prevent overflow
                            ], spacing=2, tight=True),
                            border=ft.border.all(0.5, "#EEEEEE"), 
                            bgcolor="white", 
                            height=100, # [FIX] Fixed height for grid cells
                            ink=True, 
                            on_click=make_day_click(day)
                        )
                    )
        page.update()

    # Using global page.file_picker defined in main.py

    def show_day_details_dialog(day):
        d_str = f"{view_state['year']}-{view_state['month']:02d}-{day:02d}"
        evs = [e for e in view_state["events"] if e['start_date'].startswith(d_str)]
        
        detail_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, height=300)
        
        # Dialog Reference for closing
        dlg_day = None

        if not evs:
            detail_list.controls.append(ft.Container(content=ft.Text("등록된 일정이 없습니다.", color="grey", text_align="center"), alignment=ft.alignment.center, padding=20))
        else:
            for ev in evs:
                prof = ev.get('profiles')
                if isinstance(prof, list) and prof: prof = prof[0]
                un = prof.get('full_name', '익명') if prof else '익명'
                
                def make_go_detail(event_data):
                    return lambda e: open_event_detail_dialog(event_data, day) # Dialog over Dialog

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
             print("DEBUG: Clicking Add Event...")
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
        # ... (Previous logic for open_event_detail_dialog kept same) ...
        # [Abbreviated for brevity, assuming replace_file_content context handles it]
        # Wait, I cannot abbreviate in replace_file_content.
        # I will only target the loop part for color.
        
        pass # Placeholder for thought process.

    # Actual Replacement Strategy:
    # 1. Target lines 425-433 for Color Fix.
    # 2. Check FilePicker logic at 553.
    
    # Let's do Color Fix First.

        def go_editor(e):
             # Close current dialog first to avoid stack issues if desired, 
             # OR keep it open. User said "Popup" so overlay is okay.
             # But Flet sometimes dislikes multi-dialogs. Let's close DayDialog then Open Editor.
             print("DEBUG: Clicking Add Event...")
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
        # We might need to close the day dialog first or stack it.
        # Let's stack it (page.open adds to stack).
        
        def delete_ev(e):
            try:
                supabase.table("calendar_events").delete().eq("id", ev['id']).execute()
                page.snack_bar = ft.SnackBar(ft.Text("삭제되었습니다."))
                page.snack_bar.open=True
                page.close(dlg_det) # Close Detail
                # Refresh Day View? We need to reload data.
                load() 
                # Re-open Day View not easy without callback. 
                # Just close and let user click day again.
                page.update()
            except Exception as ex: print(f"Del Error: {ex}")

        def open_map(e):
            if ev.get('location'):
                try:
                    query = urllib.parse.quote(ev['location'])
                    page.launch_url(f"https://map.naver.com/p/search/{query}")
                except: pass

        def open_file(e):
            link = ev.get('link')
            if not link: return
            
            # [Fix] Preview Popup
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
        print(f"DEBUG: Opening Editor for day {day}")
        dlg_edit = None  # [Fix] Initialize to avoid NameError
        try:
            target_date = datetime(view_state['year'], view_state['month'], day)
        except: target_date = datetime.now()

        # ... (State definition omitted, kept same) ...
        # State
        evt_state = {
            "all_day": False,
            "start_date": target_date.replace(hour=9,minute=0,second=0,microsecond=0),
            "end_date": target_date.replace(hour=10,minute=0,second=0,microsecond=0),
            "start_time": time(9,0),
            "end_time": time(10,0),
            "color": "#1DDB16",
            "participants": []
        }
        
        # Pickers (Hoisted)
        def on_d_s(e): 
            if e.control.value: evt_state["start_date"] = e.control.value; update_ui()
        def on_d_e(e): 
            if e.control.value: evt_state["end_date"] = e.control.value; update_ui()
        def on_t_s(e): 
            if e.control.value: evt_state["start_time"] = e.control.value; update_ui()
        def on_t_e(e): 
            if e.control.value: evt_state["end_time"] = e.control.value; update_ui()
        
        # Create fresh pickers for this dialog session
        dp_s = ft.DatePicker(on_change=on_d_s); dp_e = ft.DatePicker(on_change=on_d_e)
        tp_s = ft.TimePicker(on_change=on_t_s, time_picker_entry_mode=ft.TimePickerEntryMode.DIAL_ONLY)
        tp_e = ft.TimePicker(on_change=on_t_e, time_picker_entry_mode=ft.TimePickerEntryMode.DIAL_ONLY)
        
        page.overlay.extend([dp_s, dp_e, tp_s, tp_e])
        
        # UI Controls declared before handlers to avoid NameError
        status_msg = ft.Text("", size=12, color="orange", visible=False)
        saved_fname = None
        link_tf = ft.TextField(label="클라우드 파일 링크", icon=ft.Icons.CLOUD_UPLOAD, read_only=True, expand=True)
        title_tf = ft.TextField(label="제목", value=init, autofocus=True)
        loc_tf = ft.TextField(label="장소", icon=ft.Icons.LOCATION_ON)
        btn_file = ft.TextButton("클라우드 업로드", icon=ft.Icons.UPLOAD_FILE, on_click=lambda _: page.file_picker.pick_files())
        
        # [Fix] Change to Column to avoid horizontal overlap
        link_section = ft.Column([
            link_tf,
            ft.Row([btn_file, status_msg], alignment="spaceBetween")
        ], spacing=5)

        # [Commercial Grade] Cloud Upload Logic via Signed URLs
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
                page.update() # [Fix] Use page.update() instead of direct control update to avoid NameError
                
                try:
                    saved_fname = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{f.name}"
                    public_url = f"{supabase.url}/storage/v1/object/public/uploads/{saved_fname}"
                    link_tf.value = public_url
                    
                    # Desktop Fallback: Upload from Server side if f.path is accessible
                    if f.path:
                        print(f"DEBUG: Desktop mode detected. Uploading from server side: {f.path}")
                        with open(f.path, "rb") as file_data:
                            content = file_data.read()
                            supabase.storage.from_("uploads").upload(saved_fname, content)
                        status_msg.value = "업로드 완료 (Desktop)"; status_msg.color = "green"
                    else:
                        # Web Standard: Use Signed URL and browser-side upload
                        print("DEBUG: Web mode detected. Using Signed URL.")
                        signed_url = supabase.storage.from_("uploads").create_signed_upload_url(saved_fname)
                        page.file_picker.upload([
                            ft.FilePickerUploadFile(name=f.name, upload_url=signed_url, method="PUT")
                        ])
                except Exception as ex:
                    import traceback
                    print(f"DEBUG: Detailed Upload Error ->\n{traceback.format_exc()}")
                    status_msg.value = f"설정 오류: {str(ex)[:50]}"
                status_msg.visible = True
                page.update()

        def on_upload_complete(e: ft.FilePickerUploadEvent):
             status_msg.value = "업로드 완료"
             status_msg.color = "green"
             page.update()
        
        page.file_picker.on_result = on_file_result
        page.file_picker.on_upload = on_upload_progress
        
        # Time Buttons
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
        
        # Colors
        colors = ["#1DDB16", "#FF9800", "#448AFF", "#E91E63", "#9C27B0", "#000000"]
        color_row = ft.Row(spacing=10)
        def set_color(c):
            evt_state["color"] = c
            for btn in color_row.controls:
                btn.content.visible = (btn.data == c)
            if dlg_edit and dlg_edit.open: dlg_edit.update()
        for c in colors:
            color_row.controls.append(ft.Container(width=30, height=30, bgcolor=c, border_radius=15, data=c, on_click=lambda e: set_color(e.control.data), content=ft.Icon(ft.Icons.CHECK, color="white", size=20, visible=(c==evt_state["color"])), alignment=ft.alignment.center))

        # Participants
        participant_chips = ft.Row(wrap=True)
        try:
            res = supabase.table("profiles").select("id, full_name").execute()
            profiles = res.data or []
        except: profiles = []
        
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
            try:
                supabase.table("calendar_events").insert(data).execute()
                page.snack_bar = ft.SnackBar(ft.Text("저장 완료!"))
                page.snack_bar.open=True
                page.close(dlg_edit)
                load() # Refresh
                page.update()
            except Exception as ex:
                print(f"Save Error: {ex}")
                page.snack_bar = ft.SnackBar(ft.Text(f"오류: {ex}"), bgcolor="red"); page.snack_bar.open=True; page.update()

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
    if audio_recorder not in page.overlay: 
        page.overlay.append(audio_recorder)
    page.update()

    def load_memos():
        try:
            res = supabase.table("order_memos").select("*").order("created_at", desc=True).execute()
            state["memos"] = res.data or []; render_memos()
        except: pass

    def render_memos():
        memo_list_view.controls = []
        if not state["memos"]:
            memo_list_view.controls.append(ft.Container(content=ft.Text("저장된 음성 메모가 없습니다.", italic=True, color="grey"), padding=20, alignment=ft.alignment.center))
        
        ed_id = state.get("edit_id")
        for m in state["memos"]:
            time_str = m['created_at'][5:16].replace('T', ' ')
            is_ed = (ed_id == m['id'])
            if is_ed:
                fld = ft.TextField(value=m['content'], multiline=True, expand=True, autofocus=True, text_size=15, border_color="#00C73C")
                memo_content = ft.Row([fld, ft.Column([ft.IconButton(ft.Icons.CHECK_CIRCLE, icon_color="#00C73C", on_click=lambda e, mid=m['id'], f=fld: save_inline(mid, f)), ft.IconButton(ft.Icons.CANCEL, icon_color="red", on_click=lambda _: cancel_ed())], spacing=0)], alignment="spaceBetween")
            else:
                memo_content = ft.Row([
                    ft.Column([
                        ft.Row([ft.Icon(ft.Icons.RECEIPT_LONG, size=16, color="#448AFF"), ft.Text(time_str, size=11, color="grey")], spacing=5), 
                        ft.Text(m['content'], size=15, weight="w500", color="black")
                    ], spacing=5, expand=True), 
                    ft.Row([
                        ft.IconButton(ft.Icons.CALENDAR_TODAY, icon_size=18, icon_color="#FF9800", tooltip="일정 등록", on_click=lambda e, t=m['content']: pkr(t)), 
                        ft.IconButton(ft.Icons.COPY, icon_size=18, tooltip="복사", on_click=lambda e, t=m['content']: copy(t)), 
                        ft.IconButton(ft.Icons.EDIT, icon_size=18, tooltip="수정", on_click=lambda e, mid=m['id']: enter_ed(mid)),
                        ft.IconButton(ft.Icons.DELETE, icon_size=18, icon_color="red", tooltip="삭제", on_click=lambda e, mid=m['id']: delete_memo(mid))
                    ], spacing=0)
                ], alignment="spaceBetween")
            memo_list_view.controls.append(ft.Container(content=memo_content, padding=15, bgcolor="#F8F9FA", border_radius=10, border=ft.border.all(1, "#EEEEEE")))
        page.update()

    def pkr(txt=""):
        # 1. 상태 변수 및 다이얼로그 참조 초기화
        dlg_evt = None
        
        import datetime
        now = datetime.datetime.now()
        tomorrow = now + datetime.timedelta(days=1)
        
        evt_state = {
            "all_day": False,
            "start_date": tomorrow,
            "start_time": datetime.time(9, 0),
            "end_date": tomorrow,
            "end_time": datetime.time(10, 0),
            "color": "#1DDB16", # Default Green
            "participants": []
        }

        # 2. UI 컴포넌트 사전 선언
        # [Refactor] 제목은 비워두고, 내용은 메모(description)로 이동
        title_tf = ft.TextField(label="제목", value="", expand=True, autofocus=True)
        loc_tf = ft.TextField(label="장소", icon=ft.Icons.LOCATION_ON, text_size=14)
        link_tf = ft.TextField(label="링크", icon=ft.Icons.LINK, text_size=14, expand=True, read_only=True)
        memo_tf = ft.TextField(label="메모", value=txt, multiline=True, min_lines=3, icon=ft.Icons.NOTE)

        status_msg = ft.Text("", size=12, color="orange", visible=False)
        def on_f_res(e: ft.FilePickerResultEvent):
            if e.files:
                f = e.files[0]
                status_msg.visible = True
                status_msg.value = "준비 중..."
                page.update()
                try:
                    fname = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{f.name}"
                    public_url = f"{supabase.url}/storage/v1/object/public/uploads/{fname}"
                    link_tf.value = public_url
                    
                    if f.path:
                        print(f"DEBUG: pkr Desktop mode. Server-side upload.")
                        with open(f.path, "rb") as file_data:
                            content = file_data.read()
                            supabase.storage.from_("uploads").upload(fname, content)
                        status_msg.value = "완료 (D)"; status_msg.color = "green"
                    else:
                        print("DEBUG: pkr Web mode. Signed URL.")
                        signed_url = supabase.storage.from_("uploads").create_signed_upload_url(fname)
                        def on_f_up(up_e: ft.FilePickerUploadEvent):
                            status_msg.value = f"업로딩 ({int(up_e.progress * 100)}%)"
                            if up_e.progress == 1:
                                status_msg.value = "완료"; status_msg.color = "green"
                            page.update()
                        page.file_picker.on_upload = on_f_up
                        page.file_picker.upload([ft.FilePickerUploadFile(name=f.name, upload_url=signed_url, method="PUT")])
                except Exception as ex:
                    import traceback
                    print(f"DEBUG: pkr Detailed Upload Error ->\n{traceback.format_exc()}")
                    status_msg.value = f"에러: {str(ex)[:15]}"
                    status_msg.visible = True
                page.update()
        
        page.file_picker.on_result = on_f_res
        
        btn_file = ft.TextButton("클라우드 업로드", icon=ft.Icons.UPLOAD_FILE, on_click=lambda _: page.file_picker.pick_files())
        link_section = ft.Column([
            link_tf,
            ft.Row([btn_file, status_msg], alignment="spaceBetween")
        ], spacing=5)

        # 시간 표시용 버튼 텍스트 업데이트 함수
        def update_time_btns():
            s_dt_str = evt_state["start_date"].strftime("%Y년 %m월 %d일")
            e_dt_str = evt_state["end_date"].strftime("%Y년 %m월 %d일")
            s_tm_str = evt_state["start_time"].strftime("%p %I:%M").replace("AM", "오전").replace("PM", "오후")
            e_tm_str = evt_state["end_time"].strftime("%p %I:%M").replace("AM", "오전").replace("PM", "오후")
            
            btn_start_date.text = s_dt_str
            btn_end_date.text = e_dt_str
            btn_start_time.text = s_tm_str
            btn_end_time.text = e_tm_str
            
            # 종일 설정 시 시간 버튼 숨김
            btn_start_time.visible = not evt_state["all_day"]
            btn_end_time.visible = not evt_state["all_day"]
            
            if dlg_evt and dlg_evt.open: dlg_evt.update()

        # 3. 날짜/시간 피커 핸들러
        def on_date_change(e, is_start):
            if not e.control.value: return
            if is_start: evt_state["start_date"] = e.control.value
            else: evt_state["end_date"] = e.control.value
            update_time_btns()
            
        def on_time_change(e, is_start):
            if not e.control.value: return
            if is_start: evt_state["start_time"] = e.control.value
            else: evt_state["end_time"] = e.control.value
            update_time_btns()

        date_picker_start = ft.DatePicker(on_change=lambda e: on_date_change(e, True))
        date_picker_end = ft.DatePicker(on_change=lambda e: on_date_change(e, False))
        time_picker_start = ft.TimePicker(on_change=lambda e: on_time_change(e, True), time_picker_entry_mode=ft.TimePickerEntryMode.DIAL_ONLY)
        time_picker_end = ft.TimePicker(on_change=lambda e: on_time_change(e, False), time_picker_entry_mode=ft.TimePickerEntryMode.DIAL_ONLY)
        
        # 페이지에 오버레이 추가 (다이얼로그 열기 전 필수)
        page.overlay.extend([date_picker_start, date_picker_end, time_picker_start, time_picker_end])

        # 4. 버튼 컴포넌트
        btn_start_date = ft.OutlinedButton(on_click=lambda _: page.open(date_picker_start))
        btn_end_date = ft.OutlinedButton(on_click=lambda _: page.open(date_picker_end))
        btn_start_time = ft.OutlinedButton(on_click=lambda _: page.open(time_picker_start))
        btn_end_time = ft.OutlinedButton(on_click=lambda _: page.open(time_picker_end))
        
        # 종일 스위치 핸들러
        def toggle_all_day(e):
            evt_state["all_day"] = e.control.value
            update_time_btns()

        sw_all_day = ft.Switch(label="종일", value=False, on_change=toggle_all_day)

        # 5. 색상 선택 (Midnight Black 테마 포함)
        colors = ["#1DDB16", "#FF9800", "#448AFF", "#E91E63", "#9C27B0", "#000000"]
        color_row = ft.Row(spacing=10)
        
        def set_color(c):
            evt_state["color"] = c
            for btn in color_row.controls:
                btn.content.visible = (btn.data == c)
            if dlg_evt and dlg_evt.open: dlg_evt.update()

        for c in colors:
            color_row.controls.append(
                ft.Container(
                    width=30, height=30, bgcolor=c, border_radius=15, 
                    data=c,
                    on_click=lambda e: set_color(e.control.data),
                    content=ft.Icon(ft.Icons.CHECK, color="white", size=20, visible=(c==evt_state["color"])),
                    alignment=ft.alignment.center
                )
            )

        # 6. 참석자 선택 (프로필 로드)
        participant_chips = ft.Row(wrap=True)
        try:
            # 프로필 가져오기
            res = supabase.table("profiles").select("id, full_name").execute()
            profiles = res.data or []
        except: profiles = []

        def toggle_part(pid):
            if pid in evt_state["participants"]: evt_state["participants"].remove(pid)
            else: evt_state["participants"].append(pid)
            render_parts()

        def render_parts():
            participant_chips.controls = []
            for p in profiles:
                is_sel = p['id'] in evt_state["participants"]
                participant_chips.controls.append(
                    ft.Chip(
                        label=ft.Text(p.get('full_name', 'Unknown')),
                        selected=is_sel,
                        on_select=lambda e, pid=p['id']: toggle_part(pid)
                    )
                )
            if dlg_evt and dlg_evt.open: dlg_evt.update()

        render_parts()

        # 7. 저장 로직
        def save_event(e):
            if not title_tf.value:
                title_tf.error_text = "제목을 입력하세요"
                title_tf.update()
                return

            # 날짜+시간 병합 (ISO 포맷)
            if evt_state["all_day"]:
                cols_s = evt_state["start_date"].strftime("%Y-%m-%d 00:00:00")
                cols_e = evt_state["end_date"].strftime("%Y-%m-%d 23:59:59")
            else:
                cols_s = f"{evt_state['start_date'].strftime('%Y-%m-%d')} {evt_state['start_time'].strftime('%H:%M:%S')}"
                cols_e = f"{evt_state['end_date'].strftime('%Y-%m-%d')} {evt_state['end_time'].strftime('%H:%M:%S')}"


            data = {
                "title": title_tf.value,
                "start_date": cols_s,
                "end_date": cols_e,
                "is_all_day": evt_state["all_day"],
                "color": evt_state["color"],
                "location": loc_tf.value,
                "link": link_tf.value,
                "description": memo_tf.value, # DB insert (Requires Migration)
                "participant_ids": evt_state["participants"],
                "user_id": "00000000-0000-0000-0000-000000000001"
            }
            # data.pop("description") # 주석 해제하여 description 전송 시도

            try:
                supabase.table("calendar_events").insert(data).execute()
                page.snack_bar = ft.SnackBar(ft.Text("일정이 등록되었습니다! 🎉"))
                page.snack_bar.open = True
                page.close(dlg_evt)
                page.update()
                navigate_to("calendar") # 캘린더 새로고침
            except Exception as ex:
                print(f"Save Event Error: {ex}")
                page.snack_bar = ft.SnackBar(ft.Text(f"저장 실패: {ex}"), bgcolor="red")
                page.snack_bar.open = True
                page.update()

        # 8. 다이얼로그 조립
        dlg_evt = ft.AlertDialog(
            title=ft.Text("새 일정"),
            content=ft.Container(
                width=400,
                content=ft.Column([
                    title_tf,
                    ft.Row([ft.Icon(ft.Icons.ACCESS_TIME), sw_all_day], alignment="spaceBetween"),
                    ft.Row([ft.Text("시작"), btn_start_date, btn_start_time], alignment="spaceBetween"),
                    ft.Row([ft.Text("종료"), btn_end_date, btn_end_time], alignment="spaceBetween"),
                    ft.Divider(),
                    ft.Text("색상"),
                    color_row,
                    ft.Divider(),
                    ft.Text("참석자"),
                    ft.Divider(),
                    loc_tf,
                    link_section,
                    memo_tf
                ], scroll=ft.ScrollMode.AUTO, height=500, tight=True)
            ),
            actions=[
                ft.TextButton("취소", on_click=lambda _: page.close(dlg_evt)),
                ft.ElevatedButton("저장", on_click=save_event, bgcolor="#00C73C", color="white")
            ]
        )
        
        update_time_btns() # 초기값 설정
        page.open(dlg_evt)

    def enter_ed(mid): state["edit_id"] = mid; render_memos()
    def cancel_ed(): state["edit_id"] = None; render_memos()
    def save_inline(mid, f):
        supabase.table("order_memos").update({"content": f.value}).eq("id", mid).execute()
        state["edit_id"] = None; load_memos()

    def copy(t):
        page.set_clipboard(t); page.snack_bar = ft.SnackBar(ft.Text("복사되었습니다!")); page.snack_bar.open = True; page.update()

    def delete_memo(mid):
        try:
            supabase.table("order_memos").delete().eq("id", mid).execute()
            load_memos()
            page.snack_bar = ft.SnackBar(ft.Text("삭제되었습니다.")); page.snack_bar.open = True; page.update()
        except Exception as ex:
            print(f"Delete Error: {ex}")

    def delete_all_memos():
        try:
            # Note: Normally we should use 'delete().neq("id", 0)' or similar to delete all, 
            # but supabase-py delete() requires a filter unless explicitly allowed.
            # We will use user_id filter to delete all for this user.
            supabase.table("order_memos").delete().eq("user_id", "00000000-0000-0000-0000-000000000001").execute()
            load_memos()
            page.snack_bar = ft.SnackBar(ft.Text("모든 메모가 삭제되었습니다.")); page.snack_bar.open = True; page.update()
        except Exception as ex:
            print(f"Delete All Error: {ex}")

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
            try:
                path = audio_recorder.stop_recording()
                if not path or "blob" in path:
                    status_text.value = "모바일 앱 환경 필요"
                    status_text.color = "red"
                    page.snack_bar = ft.SnackBar(ft.Text("브라우저에서는 녹음이 제한됩니다. 앱을 사용하거나 PC에서 사용해 주세요."), open=True)
                    page.update()
                    return
            except Exception as ex:
                status_text.value = "마이크 종료 에러"
                page.update()
                return

            def proc():
                try:
                    # Get keywords for prompt
                    prompts_res = supabase.table("voice_prompts").select("keyword").execute()
                    keywords = [p['keyword'] for p in prompts_res.data or []]
                    prompt_str = ", ".join(keywords) if keywords else None
                    
                    t = transcribe_audio(path, prompt=prompt_str)
                    if t:
                        supabase.table("order_memos").insert({"content": t, "user_id": "00000000-0000-0000-0000-000000000001"}).execute()
                        status_text.value = f"결과: {t[:10]}..."
                        status_text.color = "green"
                        load_memos()
                    else:
                        status_text.value = "인식 실패 (빈 내용)"
                        status_text.color = "orange"
                except Exception as ex:
                    print(f"Proc Error: {ex}")
                    status_text.value = f"AI 에러: {str(ex)[:20]}"
                    status_text.color = "red"
                finally:
                    page.update()
            
            threading.Thread(target=proc, daemon=True).start()
            page.update()

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
    
    header = ft.Container(
        content=ft.Row([
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to("home")), 
                ft.Text("음성 메모", size=20, weight="bold")
            ]), 
            ft.Row([
                ft.IconButton(ft.Icons.BOOKMARK_ADDED, tooltip="단어장", on_click=open_dictionary),
                ft.IconButton(ft.Icons.DELETE_SWEEP, tooltip="전체 삭제", icon_color="red", on_click=lambda e: delete_all_memos())
            ])
        ], alignment="spaceBetween"), 
        padding=10, 
        border=ft.border.only(bottom=ft.border.BorderSide(1, "#EEEEEE"))
    )
    
    load_memos()
    return [ft.Container(expand=True, bgcolor="white", content=ft.Column([header, ft.Container(memo_list_view, expand=True, padding=20), ft.Container(content=ft.Column([status_text, recording_timer, mic_btn, ft.Container(height=10)], horizontal_alignment="center", spacing=10), padding=20, bgcolor="#F8F9FA", border_radius=ft.border_radius.only(top_left=30, top_right=30))], spacing=0))]
