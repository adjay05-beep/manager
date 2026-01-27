import flet as ft
import datetime
from datetime import datetime as dt_class, timezone
import asyncio
import threading
from services import chat_service
from db import supabase, service_supabase, app_logs, log_info

DEBUG_MODE = True

def get_chat_controls(page: ft.Page, navigate_to):
    # [FIX] Stability: Use Global FilePicker and Robust Lifecycle Management
    
    state = {
        "current_topic_id": None, 
        "edit_mode": False, 
        "view_mode": "list", 
        "pending_image_url": None,
        "pending_file_name": None,
        "is_active": True # Flag to control infinite loops
    }
    # [RBAC] Get User from Session
    current_user_id = page.session.get("user_id")
    
    # [CRITICAL FIX] If no user session, show error UI instead of silently failing
    if not current_user_id:
        log_info("CRITICAL: No User Session in Chat View - Showing Error UI")
        error_view = ft.Container(
            expand=True,
            content=ft.Column([
                ft.Icon(ft.Icons.ERROR_OUTLINE, size=64, color="red"),
                ft.Text("세션이 만료되었습니다", size=20, weight="bold", color="red"),
                ft.Text("다시 로그인해 주세요", size=14, color="grey"),
                ft.ElevatedButton(
                    "로그인 화면으로", 
                    on_click=lambda _: navigate_to("login"),
                    bgcolor="blue",
                    color="white"
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
            alignment=ft.alignment.center,
            padding=40
        )
        return [error_view]
    
    log_info(f"Chat View initialized for user: {current_user_id}")
    
    # Initialize UI Controls
    topic_list_container = ft.Column(expand=True, spacing=0)
    message_list_view = ft.ListView(expand=True, spacing=5, padding=10)
    chat_header_title = ft.Text("", weight="bold", size=18)
    msg_input = ft.TextField(hint_text="메시지를 입력하세요...", expand=True, multiline=True, max_lines=3)
    root_view = ft.Column(expand=True, spacing=0)

    async def load_topics_thread(update_ui=True, show_all=False):
        if not state["is_active"]: return
        if not current_user_id:
            log_info("Chat ERROR: No user session found - cannot load topics")
            page.snack_bar = ft.SnackBar(
                ft.Text("세션이 만료되었습니다. 다시 로그인해 주세요.", color="white"),
                bgcolor="red",
                open=True
            )
            page.update()
            return
            
        try:
            log_info(f"Loading topics (Mode: {'ALL' if show_all else 'Members Only'}) for {current_user_id}")
            
            # [DIAGNOSTIC] Log database connection status
            log_info(f"Database URL: {service_supabase.url[:30]}...")
            
            categories_data = chat_service.get_categories()
            log_info(f"Categories loaded: {len(categories_data) if categories_data else 0}")
            categories = [c['name'] for c in categories_data] if categories_data else ["공지", "일반", "중요", "개별 업무"]

            if show_all:
                topics = chat_service.get_all_topics()
            else:
                topics = chat_service.get_topics(current_user_id)
                
            log_info(f"Topics fetched: {len(topics)} topics for user {current_user_id}")
            if len(topics) == 0:
                log_info("WARNING: No topics returned from database - user may need to create one or check membership")
            sorted_topics = sorted(topics, key=lambda x: (x.get('display_order', 0) or 0, x.get('created_at', '')), reverse=True)
            
            reading_map = chat_service.get_user_read_status(current_user_id)
            default_old = "1970-01-01T00:00:00Z"
            earliest_read = min(reading_map.values()) if reading_map else default_old
            
            recent_msgs = chat_service.get_recent_messages(earliest_read)
            
            unread_counts = {}
            for m in recent_msgs:
                tid_m = m['topic_id']; lr_m = reading_map.get(tid_m, default_old)
                if m['created_at'] > lr_m: unread_counts[tid_m] = unread_counts.get(tid_m, 0) + 1

            new_controls = []
            if state["edit_mode"]:
                edit_list_ctrls = []
                grouped = {}
                for t in sorted_topics:
                    cat = t.get('category', '일반')
                    if cat not in grouped: grouped[cat] = []
                    grouped[cat].append(t)
                
                for cat_name in [c for c in categories if c in grouped]:
                    # Find category ID for rename
                    cat_id = next((c['id'] for c in categories_data if c['name'] == cat_name), None)
                    
                    # Category Header in Edit Mode
                    edit_list_ctrls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Row([
                                    ft.Text(f"• {cat_name}", size=12, weight="bold", color="#757575"),
                                    ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_size=16, icon_color="#757575", padding=0, 
                                                 on_click=lambda e, cid=cat_id, cn=cat_name: open_rename_cat_dialog(cid, cn))
                                ], spacing=5),
                                ft.Text(str(len(grouped[cat_name])), size=10, color="#BDBDBD")
                            ], alignment="spaceBetween"),
                            padding=ft.padding.only(left=20, right=20, top=10, bottom=5),
                            bgcolor="#FAFAFA",
                            data={"type": "category", "id": cat_id} # Tag for Reorder
                        )
                    )
                    
                    for t in grouped[cat_name]:
                        tid = t['id']
                        delete_btn = ft.IconButton(
                            ft.Icons.REMOVE_CIRCLE, icon_color="red", icon_size=20,
                            on_click=lambda e, tid=tid: confirm_delete_topic(tid)
                        )
                        edit_topic_btn = ft.IconButton(
                            ft.Icons.EDIT_OUTLINED, icon_color="#757575", icon_size=20,
                            on_click=lambda e, topic=t: open_rename_topic_dialog(topic)
                        )
                        
                        item = ft.Container(
                            content=ft.Row([
                                ft.Row([delete_btn, ft.Text(t['name'], size=16, weight="bold", color="#424242")], spacing=5),
                                ft.Row([
                                    edit_topic_btn, 
                                    ft.Icon(ft.Icons.DRAG_HANDLE, size=24, color=ft.Colors.BLUE)
                                ], spacing=0)
                            ], alignment="spaceBetween"),
                            padding=ft.padding.symmetric(horizontal=15, vertical=12),
                            bgcolor="white", border=ft.border.only(bottom=ft.border.BorderSide(1, "#F5F5F5")),
                            data={"type": "topic", "id": tid} # Crucial for reorder
                        )
                        edit_list_ctrls.append(item)
                
                list_view = ft.ReorderableListView(
                    expand=True, 
                    on_reorder=on_topic_reorder, 
                    show_default_drag_handles=False, # Disable system gray handle
                    padding=0,
                    controls=edit_list_ctrls
                )
                new_controls = [list_view]
            else:
                list_view_ctrls = []
                grouped = {}
                for t in sorted_topics:
                    cat = t.get('category', '일반')
                    if cat not in grouped: grouped[cat] = []
                    grouped[cat].append(t)
                
                for cat_name in [c for c in categories if c in grouped]:
                    list_view_ctrls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text(f"• {cat_name}", size=12, weight="bold", color="#757575"),
                                ft.Text(str(len(grouped[cat_name])), size=10, color="#BDBDBD")
                            ], alignment="spaceBetween"),
                            padding=ft.padding.only(left=20, right=20, top=10, bottom=5),
                            bgcolor="#FAFAFA"
                        )
                    )
                    for t in grouped[cat_name]:
                        tid = t['id']; is_priority = t.get('is_priority', False); unread_count = unread_counts.get(tid, 0)
                        badge = ft.Container(
                            content=ft.Text(str(unread_count), size=10, color="white", weight="bold"),
                            bgcolor="#FF5252", padding=ft.padding.symmetric(horizontal=8, vertical=4), border_radius=10
                        ) if unread_count > 0 else ft.Container()
                        prio_icon = ft.Icon(ft.Icons.ERROR_OUTLINE, size=20, color="#FF5252") if is_priority else ft.Container()

                        list_view_ctrls.append(
                            ft.Container(
                                content=ft.Row([
                                    ft.Row([prio_icon, ft.Text(t['name'], size=16, weight="bold", color="#424242")], spacing=10),
                                    ft.Row([badge, ft.Icon(ft.Icons.ARROW_FORWARD_IOS, size=14, color="#BDBDBD")], spacing=5)
                                ], alignment="spaceBetween"),
                                padding=ft.padding.symmetric(horizontal=20, vertical=12),
                                bgcolor="white", border=ft.border.only(bottom=ft.border.BorderSide(1, "#F5F5F5")),
                                on_click=lambda e, topic=t: select_topic(topic)
                            )
                        )
                
                # [FIX] Show empty state UI if no topics exist
                if len(list_view_ctrls) == 0:
                    log_info("No topics found - showing empty state UI")
                    list_view_ctrls.append(
                        ft.Container(
                            expand=True,
                            content=ft.Column([
                                ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE, size=80, color="#BDBDBD"),
                                ft.Text("아직 스레드가 없습니다", size=18, weight="bold", color="#757575"),
                                ft.Text("우측 상단 + 버튼을 눌러", size=14, color="#BDBDBD"),
                                ft.Text("새 스레드를 만들어보세요", size=14, color="#BDBDBD"),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                            alignment=ft.alignment.center,
                            padding=40
                        )
                    )
                
                list_view = ft.ListView(expand=True, spacing=0, padding=0, controls=list_view_ctrls)
                new_controls = [list_view]
            
            topic_list_container.controls = new_controls
            if update_ui: page.update()
        except Exception as ex:
            log_info(f"Load Topics Critical Error: {ex}")
            try:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"데이터 로딩 오류: {ex}", color="white"),
                    bgcolor="red",
                    open=True
                )
                page.update()
            except: pass

    def load_topics(update_ui=True, show_all=False):
        # Fire and forget task to keep UI responsive
        page.run_task(load_topics_thread, update_ui=update_ui, show_all=show_all)

    def on_topic_reorder(e):
        try:
            list_ctrl = topic_list_container.controls[0]
            controls = list_ctrl.controls
            moved_item = controls.pop(e.old_index)
            controls.insert(e.new_index, moved_item)
            
            # Fire and forget update
            def _update_order():
                # Process topics in the list based on their new visual index
                # We iterate backwards so items at the top have higher display_order
                current_order = len(controls)
                for ctrl in controls:
                    data = ctrl.data
                    if isinstance(data, dict) and data.get("type") == "topic":
                        chat_service.update_topic_order(data["id"], current_order)
                    current_order -= 1
                load_topics(True)
            threading.Thread(target=_update_order, daemon=True).start()
        except Exception as ex:
            log_info(f"Reorder Error: {ex}")

    def toggle_priority(tid, current_val):
        threading.Thread(target=lambda: (chat_service.toggle_topic_priority(tid, current_val), load_topics(True)), daemon=True).start()

    def open_manage_categories_dialog(e):
        cat_list = ft.Column(spacing=5)
        new_cat_input = ft.TextField(hint_text="새 주제 이름", expand=True)
        
        def refresh_cats():
            def _refresh():
                cats = chat_service.get_categories()
                items = []
                for c in cats:
                    items.append(ft.Row([
                        ft.Text(c['name'], weight="bold", expand=True),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="red", on_click=lambda e, cid=c['id']: delete_cat(cid))
                    ]))
                cat_list.controls = items
                page.update()
            threading.Thread(target=_refresh, daemon=True).start()

        def add_cat(e):
            if new_cat_input.value:
                threading.Thread(target=lambda: (
                    chat_service.create_category(new_cat_input.value),
                    refresh_cats(), 
                    load_topics(True)
                ), daemon=True).start()
                new_cat_input.value = ""

        def delete_cat(cid):
            threading.Thread(target=lambda: (chat_service.delete_category(cid), refresh_cats(), load_topics(True)), daemon=True).start()

        refresh_cats()
        dlg = ft.AlertDialog(
            title=ft.Text("주제(그룹) 관리"),
            content=ft.Column([
                ft.Row([new_cat_input, ft.IconButton(ft.Icons.ADD, on_click=add_cat)]),
                ft.Divider(),
                cat_list
            ], tight=True, scroll=ft.ScrollMode.AUTO, width=300),
            actions=[ft.TextButton("닫기", on_click=lambda _: page.close(dlg))]
        )
        page.open(dlg)

    
    def load_messages_thread():
        if not state["current_topic_id"] or not state["is_active"]: return
        try:
            messages = chat_service.get_messages(state["current_topic_id"])
            
            new_controls = []
            for m in messages:
                is_me = str(m['user_id']) == current_user_id
                prof_data = m.get('profiles')
                if isinstance(prof_data, list) and prof_data: prof_data = prof_data[0]
                user_name = prof_data.get('full_name', '익명') if prof_data else "익명"
                
                try:
                    created_dt = dt_class.fromisoformat(m['created_at'].replace("Z", "+00:00"))
                except:
                    created_dt = datetime.datetime.now()

                ampm = "오후" if created_dt.hour >= 12 else "오전"
                h = created_dt.hour % 12
                if h == 0: h = 12
                time_str = f"{ampm} {h}:{created_dt.minute:02d}"
                
                content_elements = []
                img_url = m.get('image_url')
                if img_url:
                    content_elements.append(ft.Image(src=img_url, width=240, border_radius=8))
                
                if m.get('content') and m['content'] != "[이미지 파일]":
                    content_elements.append(ft.Text(m['content'], size=14, color="black"))
                
                bubble_bg = "#FFFFFF" if is_me else "#E3F2FD"
                content_box = ft.Container(
                    content=ft.Column(content_elements, spacing=5, tight=True),
                    bgcolor=bubble_bg, padding=12, border_radius=15, 
                    border=ft.border.all(1, "#E0E0E0"),
                    # Dynamic width: no fixed width, content determines size
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
                        ft.Text(user_name, size=11, weight="bold", color="#666666"),  # Always show name
                        bubble_row
                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.START if not is_me else ft.CrossAxisAlignment.END),
                    padding=ft.padding.symmetric(vertical=4)
                ))
            
            message_list_view.controls = new_controls
            page.update()
        except Exception as e:
            print(f"Load Msg Error: {e}")

    def select_topic(topic):
        state["current_topic_id"] = topic['id']
        chat_header_title.value = topic['name']
        msg_input.disabled = False
        state["view_mode"] = "chat"
        update_layer_view()
        
        message_list_view.controls = [ft.Container(ft.ProgressRing(color="#2E7D32"), alignment=ft.alignment.center, padding=50)]
        page.update()

        threading.Thread(target=lambda: (chat_service.update_last_read(topic['id'], current_user_id), load_messages_thread()), daemon=True).start()

    def load_messages():
        threading.Thread(target=load_messages_thread, daemon=True).start()

    def send_message(content=None, image_url=None):
        final_image_url = image_url or state.get("pending_image_url")
        final_content = content or msg_input.value
        
        if not final_content and not final_image_url: return
        if not state["current_topic_id"]: return
        
        def _do_send():
            try:
                chat_service.send_message(state["current_topic_id"], final_content, final_image_url, current_user_id)
                msg_input.value = ""
                state["pending_image_url"] = None
                pending_container.visible = False
                pending_container.content = ft.Container()
                page.update()
                load_messages_thread()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"전송 실패: {ex}"), bgcolor="red", open=True); page.update()
        
        threading.Thread(target=_do_send, daemon=True).start()

    pending_container = ft.Container(visible=False, padding=10, bgcolor="#3D4446", border_radius=10)
    
    # [FIX] Use Global Picker event handler connection
    def on_chat_file_result(e: ft.FilePickerResultEvent):
        print(f"DEBUG: on_chat_file_result called. files={e.files}")
        # [REFACTOR] Use Unified Storage Service
        if e.files and state["current_topic_id"]:
            f = e.files[0]
            def _run_upload():
                try:
                    import asyncio
                    from services import storage_service
                    
                    # Update UI helper
                    def update_snack(msg):
                        print(f"DEBUG: upload_status: {msg}")
                        page.snack_bar = ft.SnackBar(ft.Text(msg), open=True)
                        page.update()

                    update_snack(f"'{f.name}' 준비 중...")

                    # Execute Upload (Run the async function in a new loop or the page loop)
                    # For stability in Sync 앱, we can use run_task if available or just execute logic.
                    # Since handle_file_upload is async, we need a loop.
                    
                    # Simplified: if it's already in a thread, we can use a new loop but 
                    # better to use page.run_task if picker.upload is involved.
                    
                    async def _async_logic():
                        result = await storage_service.handle_file_upload(page, f, update_snack, picker_ref=page.chat_file_picker)
                        
                        # Set pending state from result
                        if "public_url" in result:
                            state["pending_image_url"] = result["public_url"]
                            update_pending_ui(state["pending_image_url"])
                            update_snack("파일 준비 완료!")
                        else:
                            print(f"DEBUG: No public_url in result: {result}")

                    # Use page logic to run async
                    page.run_task(_async_logic)

                except Exception as ex:
                    print(f"ERROR in file upload: {ex}")
                    import traceback
                    traceback.print_exc()
                    page.snack_bar = ft.SnackBar(ft.Text(f"오류: {ex}"), bgcolor="red", open=True)
                    page.update()
            
            # Run the logic
            _run_upload()
        else:
            print(f"DEBUG: File selection skipped or no current topic (files={e.files}, topic={state['current_topic_id']})")

    def on_chat_upload_progress(e: ft.FilePickerUploadEvent):
        if e.error:
            page.snack_bar = ft.SnackBar(ft.Text(f"업로드 실패: {e.file_name}"), bgcolor="red", open=True); page.update()
        elif e.progress == 1.0:
            update_pending_ui(state.get("pending_image_url"))
            page.snack_bar = ft.SnackBar(ft.Text("이미지 로드 완료!"), bgcolor="green", open=True)
            page.update()

    def update_pending_ui(public_url):
        if not public_url: return
        pending_container.content = ft.Row([
            ft.Image(src=public_url, width=50, height=50, border_radius=5, fit=ft.ImageFit.COVER),
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
    
    # Bind Helper handlers only when needed (idempotent?)
    # Flet Event Handlers are multicast, but rewriting them is okay.
    page.chat_file_picker.on_result = on_chat_file_result
    page.chat_file_picker.on_upload = on_chat_upload_progress

    def confirm_delete_topic(tid):
        def delete_it(e):
            threading.Thread(target=lambda: (chat_service.delete_topic(tid), load_topics(True)), daemon=True).start()
            page.close(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text("스레드 삭제"),
            content=ft.Text("이 스레드와 모든 메시지가 삭제됩니다."),
            actions=[ft.TextButton("취소", on_click=lambda _: page.close(dlg)), ft.TextButton("삭제", on_click=delete_it, color="red")]
        )
        page.open(dlg)

    def open_create_topic_dialog(e):
        new_name = ft.TextField(label="새 스레드 이름", autofocus=True)
        cat_dropdown = ft.Dropdown(label="주제 분류", value="일반", options=[])
        
        def _load_cats_for_dlg():
            cats = chat_service.get_categories()
            cat_dropdown.options = [ft.dropdown.Option(c['name']) for c in cats or [{"name": "일반"}]]
            if not cat_dropdown.options: cat_dropdown.options = [ft.dropdown.Option("일반")]
            cat_dropdown.value = cat_dropdown.options[0].key
            page.update()
        
        threading.Thread(target=_load_cats_for_dlg, daemon=True).start()

        def create_it(e):
            print(f"DEBUG: create_it called, name='{new_name.value}', category='{cat_dropdown.value}'")
            if new_name.value:
                async def _do_create():
                    try:
                        log_info(f"Creating topic: {new_name.value} ({cat_dropdown.value})")
                        
                        # [EMERGENCY FIX] Ensure profile exists before creating topic
                        try:
                            profile_check = service_supabase.table("profiles").select("id").eq("id", current_user_id).execute()
                            if not profile_check.data:
                                # Create profile on the spot
                                user_email = page.session.get("user_email")
                                full_name = user_email.split("@")[0] if user_email else "Unknown"
                                service_supabase.table("profiles").insert({
                                    "id": current_user_id,
                                    "full_name": full_name,
                                    "role": "staff"
                                }).execute()
                                log_info(f"Auto-created profile for {current_user_id}")
                        except Exception as profile_err:
                            log_info(f"Profile check failed: {profile_err}")
                        
                        result = chat_service.create_topic(new_name.value, cat_dropdown.value, current_user_id)
                        log_info(f"Topic creation success: {new_name.value}")
                        
                        # [FIX] Proper Flet dialog close
                        dlg.open = False
                        page.update()
                        load_topics(True)
                    except Exception as ex:
                        error_msg = str(ex)
                        log_info(f"Creation ERROR: {ex}")
                        
                        # Give user-friendly error message with technical detail for debugging
                        user_msg = f"토픽 생성 실패: {error_msg}"
                        
                        page.snack_bar = ft.SnackBar(
                            ft.Text(user_msg, color="white"),
                            bgcolor="red",
                            open=True,
                            duration=10000 # Longer duration for debug
                        )
                        page.update()
                page.run_task(_do_create)
            else:
                print("DEBUG: create_it - no name provided")
        
        def close_it(e):
            dlg.open = False
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("새 스레드 만들기"),
            content=ft.Column([new_name, cat_dropdown], tight=True, spacing=15),
            actions=[ft.TextButton("취소", on_click=close_it), ft.TextButton("만들기", on_click=create_it)]
        )
        # [FIX] Proper Flet dialog open
        page.dialog = dlg
        dlg.open = True
        page.update()

    def open_rename_topic_dialog(topic):
        topic_id = topic['id']
        name_input = ft.TextField(value=topic['name'], label="스레드 이름", expand=True)
        
        async def do_rename(e):
            if name_input.value:
                try:
                    chat_service.rename_topic(topic_id, name_input.value)
                    page.close(dlg)
                    load_topics(True)
                except Exception as ex:
                    log_info(f"Rename Topic Error: {ex}")
        
        dlg = ft.AlertDialog(
            title=ft.Text("스레드 이름 수정"),
            content=name_input,
            actions=[
                ft.TextButton("취소", on_click=lambda _: page.close(dlg)),
                ft.ElevatedButton("저장", on_click=do_rename, bgcolor="#2E7D32", color="white")
            ]
        )
        page.open(dlg)

    def open_rename_cat_dialog(cat_id, old_name):
        if not cat_id: return # Cannot rename system default if missing ID
        name_input = ft.TextField(value=old_name, label="주제 그룹 이름", expand=True)
        
        async def do_rename(e):
            if name_input.value:
                try:
                    chat_service.update_category(cat_id, old_name, name_input.value)
                    page.close(dlg)
                    load_topics(True)
                except Exception as ex:
                    log_info(f"Rename Category Error: {ex}")
        
        dlg = ft.AlertDialog(
            title=ft.Text("주제 그룹 이름 수정"),
            content=name_input,
            actions=[
                ft.TextButton("취소", on_click=lambda _: page.close(dlg)),
                ft.ElevatedButton("저장", on_click=do_rename, bgcolor="#2E7D32", color="white")
            ]
        )
        page.open(dlg)

    edit_btn_ref = ft.Ref[ft.OutlinedButton]()
    def toggle_edit_mode():
        state["edit_mode"] = not state["edit_mode"]
        if edit_btn_ref.current:
            edit_btn_ref.current.text = "완료" if state["edit_mode"] else "편집"
            edit_btn_ref.current.style = ft.ButtonStyle(
                color="white" if state["edit_mode"] else "#424242",
                bgcolor="#2E7D32" if state["edit_mode"] else "transparent",
                shape=ft.RoundedRectangleBorder(radius=8),
                side=ft.BorderSide(1, "#2E7D32" if state["edit_mode"] else "#E0E0E0"),
                padding=ft.padding.symmetric(horizontal=12, vertical=0)
            )
            edit_btn_ref.current.update()
        load_topics(True)

    # [DIAGNOSTIC] Debug Panel
    debug_log_col = ft.Column(spacing=2, scroll=ft.ScrollMode.ALWAYS, expand=True)
    
    def refresh_debug(_=None):
        debug_log_col.controls = [ft.Text(log, size=10, color="green" if "Established" in log else "white") for log in app_logs]
        if page: page.update()

    debug_panel = ft.ExpansionTile(
        title=ft.Text("Debug Console (Alpha)", size=12, color="orange", weight="bold"),
        subtitle=ft.Text("Tap to see logs & Force Load", size=10, color="white70"),
        bgcolor=ft.Colors.with_opacity(0.9, "black"),
        collapsed_bgcolor=ft.Colors.with_opacity(0.8, "black"),
        on_change=refresh_debug,
        controls=[
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.ElevatedButton("Force All Topics", on_click=lambda _: load_topics(show_all=True), bgcolor="blue", color="white"),
                        ft.ElevatedButton("Refresh Logs", on_click=refresh_debug, bgcolor="grey", color="white"),
                    ], spacing=10),
                    ft.Divider(color="white24"),
                    ft.Container(content=debug_log_col, height=150, padding=5)
                ]),
                padding=10
            )
        ]
    )

    list_page = ft.Container(
        expand=True, bgcolor="white",
        content=ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW, icon_color="#212121", on_click=lambda _: navigate_to("home")),
                    ft.Text("팀 스레드", weight="bold", size=20, color="#212121"),
                    ft.Row([
                        ft.IconButton(ft.Icons.SETTINGS_OUTLINED, icon_color="#757575", on_click=open_manage_categories_dialog, tooltip="분류 관리"),
                        ft.OutlinedButton(
                            ref=edit_btn_ref, 
                            text="편집", 
                            style=ft.ButtonStyle(color="#424242", shape=ft.RoundedRectangleBorder(radius=8), side=ft.BorderSide(1, "#E0E0E0"), padding=ft.padding.symmetric(horizontal=12, vertical=0)), 
                            on_click=lambda _: toggle_edit_mode()
                        ),
                        ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, icon_color="#2E7D32", on_click=open_create_topic_dialog)
                    ], spacing=0)
                ], alignment="spaceBetween"),
                padding=ft.padding.only(left=10, right=10, top=40, bottom=0),
                border=ft.border.only(bottom=ft.border.BorderSide(1, "#F0F0F0"))
            ),
            ft.Container(content=topic_list_container, expand=True, padding=0)
            # debug_panel (Hidden for production)
        ], spacing=0) 
    )

    chat_page = ft.Container(
        expand=True, bgcolor="white",
        content=ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW, icon_color="#212121", 
                                  on_click=lambda _: back_to_list()),
                    chat_header_title,
                    ft.IconButton(ft.Icons.REFRESH_ROUNDED, icon_color="#BDBDBD", on_click=lambda _: load_messages())
                ], alignment="spaceBetween"),
                padding=ft.padding.only(left=10, right=10, top=50, bottom=5),
                border=ft.border.only(bottom=ft.border.BorderSide(1, "#F0F0F0"))
            ),
            ft.Container(content=message_list_view, expand=True, bgcolor="#F5F5F5"),
            ft.Container(
                content=ft.Column([
                    pending_container,
                    ft.Row([
                        ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED, icon_color="#757575", on_click=lambda _: page.chat_file_picker.pick_files()),
                        msg_input, 
                        ft.IconButton(ft.Icons.SEND_ROUNDED, icon_color="#2E7D32", icon_size=32, on_click=lambda _: send_message())
                    ], spacing=10)
                ]), 
                padding=12, bgcolor="white", border=ft.border.only(top=ft.border.BorderSide(1, "#EEEEEE"))
            )
        ])
    )

    def back_to_list():
        state["view_mode"] = "list"
        update_layer_view()

    def update_layer_view():
        root_view.controls = [list_page] if state["view_mode"] == "list" else [chat_page]
        page.update()

    chat_header_title.color = "#212121"
    msg_input.bgcolor = "#FAFAFA"
    msg_input.color = "black"
    msg_input.border_color = "#E0E0E0"
    msg_input.border_width = 1

    # [FIX] Robust Realtime Task
    async def realtime_task():
        await asyncio.sleep(2)
        try:
            rt_client = supabase.get_realtime_client()
            if not rt_client: return
            
            msg_channel = rt_client.channel("realtime-msgs")
            def handle_new_msg(payload):
                if state["edit_mode"]: return
                load_topics(True)
                new_tid = payload.get('record', {}).get('topic_id')
                if str(new_tid) == str(state["current_topic_id"]):
                    load_messages()
            msg_channel.on("postgres_changes", {"event": "INSERT", "schema": "public", "table": "chat_messages"}, handle_new_msg)
            
            topic_channel = rt_client.channel("realtime-topics")
            def handle_topic_change(payload):
                if state["edit_mode"]: return
                load_topics(True)
            topic_channel.on("postgres_changes", {"event": "*", "schema": "public", "table": "chat_topics"}, handle_topic_change)

            await rt_client.connect()
            await msg_channel.subscribe()
            await topic_channel.subscribe()
            
            # [FIX] Loop Check
            while state["is_active"]:
                # Check if view is still mounted
                if not root_view.page:
                    state["is_active"] = False
                    break
                await asyncio.sleep(2)
        except Exception as e:
            print(f"REALTIME ERROR: {e}")
        finally:
            print("Chat Realtime Disconnected")
            try: await rt_client.disconnect()
            except: pass

    def init_chat():
        update_layer_view()
        load_topics(True)
        page.run_task(realtime_task)

    init_chat()
    
    return [root_view]
