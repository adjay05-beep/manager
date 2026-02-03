import flet as ft
import datetime
from datetime import datetime as dt_class, timezone
import threading
import asyncio
from services import storage_service
from services import chat_service
from db import supabase, service_supabase, app_logs, log_info
from views.styles import AppColors, AppTextStyles, AppLayout
from views.components.app_header import AppHeader


from utils.logger import log_info as file_log_info
from views.components.modal_overlay import ModalOverlay

class ThreadSafeState:
    """[SECURITY] Thread-safe state management to prevent race conditions."""

    def __init__(self):
        self._lock = threading.Lock()
        self._data = {
            "current_topic_id": None,
            "edit_mode": False,
            "view_mode": "list",
            "pending_image_url": None,
            "pending_file_name": None,
            "is_active": True,
            "selection_mode": False,
            "selected_ids": set(),
            "last_read_at": None,
            "is_near_bottom": True,
            "scrolled_to_unread": False,
            "topic_id_for_unread": None,
            "last_loaded_msg_id": None,
            "is_loading_messages": False,
            "is_loading_topics": False
        }

    def get(self, key, default=None):
        with self._lock:
            return self._data.get(key, default)

    def set(self, key, value):
        with self._lock:
            self._data[key] = value

    def __getitem__(self, key):
        with self._lock:
            return self._data[key]

    def __setitem__(self, key, value):
        with self._lock:
            self._data[key] = value

    def add_selected(self, item_id):
        with self._lock:
            self._data["selected_ids"].add(str(item_id))

    def remove_selected(self, item_id):
        with self._lock:
            str_id = str(item_id)
            if str_id in self._data["selected_ids"]:
                self._data["selected_ids"].remove(str_id)

    def clear_selected(self):
        with self._lock:
            self._data["selected_ids"] = set()

    def get_selected_copy(self):
        with self._lock:
            return self._data["selected_ids"].copy()


async def get_chat_controls(page: ft.Page, navigate_to):
    # [UI] Header Title Ref
    chat_title_ref = ft.Ref[ft.Text]()
    
    file_log_info("Entering Chat View (get_chat_controls)")
    # [FIX] Stability: Use Global FilePicker and Robust Lifecycle Management
    from views.components.chat_bubble import ChatBubble

    # [SECURITY] Thread-safe state management
    state = ThreadSafeState()
    # [RBAC] Get User from Session
    current_user_id = page.app_session.get("user_id")
    current_channel_id = page.app_session.get("channel_id")
    
    # [FIX] State-Based Context: Store for background reliability
    state["uid"] = current_user_id
    state["cid"] = current_channel_id
    
    # [FAUX DIALOG]
    overlay = ModalOverlay(page)
    
    # [CRITICAL FIX] If no user session, show error UI instead of silently failing
    if not current_user_id:
        log_info("CRITICAL: No User Session in Chat View - Showing Error UI")
        error_view = ft.Container(
            expand=True,
            content=ft.Column([
                ft.Icon(ft.Icons.ERROR_OUTLINE, size=64, color="red"),
                ft.Text("세션이 만료되었습니다", size=18, weight="bold", color="red"),
                ft.Text("다시 로그인해 주세요", size=14, color="grey"),
                ft.ElevatedButton(
                    "로그인 화면으로",
                    on_click=lambda _: asyncio.create_task(navigate_to("login")),
                    bgcolor="blue",
                    color="white"
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
            alignment=ft.Alignment(0, 0),
            padding=40
        )

        return [error_view]
    
    log_info(f"Chat View initialized for user: {current_user_id}")
    
    # Initialize UI Controls
    topic_list_container = ft.Column(expand=True, spacing=0)
    # [FIX] Helper to atomic update read status and refresh UI
    async def mark_read_and_refresh(tid, uid):
        log_info(f"DEBUG_READ: mark_read_and_refresh called for TID={tid}, UID={uid}")
        await asyncio.to_thread(chat_service.update_last_read, tid, uid)
        # Refresh topic list to update badges immediately
        log_info(f"DEBUG_READ: Refreshing topics...")
        asyncio.create_task(load_topics_async(update_ui=True))

    async def scroll_to_bottom_manual(e):
        try:
            await message_list_view.scroll_to_async(offset=-1, duration=500) if hasattr(message_list_view, "scroll_to_async") else message_list_view.scroll_to(offset=-1, duration=500)
            floating_new_msg_container.visible = False
            floating_new_msg_container.update()
            
            # [Iteration 20] Explicitly mark as read when user clicks "New Message" alarm
            tid = state.get("current_topic_id")
            if tid:
                 # Ensure we run this task or await it if possible. 
                 # Since we are in an async handler running in a task, await is fine.
                 await mark_read_and_refresh(tid, current_user_id)
        except Exception:
            pass

    async def on_chat_scroll(e: ft.OnScrollEvent):
        # If user is within 50px of bottom, consider "near bottom" (More precise)
        is_bottom = (e.max_scroll_extent - e.pixels) < 50
        if is_bottom != state.get("is_near_bottom"):
            state["is_near_bottom"] = is_bottom
            # [Iteration 20] Mark as read ONLY when user reaches bottom (Honest Read)
            if is_bottom:
                tid = state.get("current_topic_id")
                uid = current_user_id
                log_info(f"DEBUG_READ: Scroll Bottom Triggered. TID={tid}")
                if tid and uid:
                    # file_log_info(f"SCROLL: Reached bottom of {tid}. Marking as read.")
                    asyncio.create_task(mark_read_and_refresh(tid, uid))
            
        # If user reached bottom, hide floating button
        if state["is_near_bottom"] and floating_new_msg_container.visible:
            floating_new_msg_container.visible = False
            if floating_new_msg_container.page:
                floating_new_msg_container.update()

    message_list_view = ft.ListView(
        expand=True, 
        spacing=5, 
        padding=10, 
        auto_scroll=False, 
        on_scroll=on_chat_scroll
    )
    
    floating_new_msg_container = ft.Container(
        content=ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.ARROW_DOWNWARD, size=16, color="white"),
                ft.Text("새 메시지", size=12, weight="bold", color="white"),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
            bgcolor="#2E7D32", # Green
            padding=ft.padding.symmetric(horizontal=15, vertical=8),
            border_radius=20,
            on_click=lambda e: asyncio.create_task(scroll_to_bottom_manual(e)),
            shadow=ft.BoxShadow(blur_radius=5, spread_radius=1, color="#33000000")
        ),
        alignment=ft.Alignment(0, 1),
        padding=ft.padding.only(bottom=20),
        visible=False
    )
    # chat_header_title removed (Refactored to AppHeader)

    # ... inside load topics ...
    # chat_header_title.controls[1].value = f"Topics: {len(topics)}"
    msg_input = ft.TextField(hint_text="메시지를 입력하세요...", expand=True, multiline=True, max_lines=3)
    
    # [NEW] Image Viewer Overlay
    image_viewer = ft.Stack(visible=False, expand=True)

    async def close_image_viewer(e):
        image_viewer.visible = False
        image_viewer.controls.clear()
        page.update()

    async def show_image_viewer(src):
        image_viewer.controls = [
            ft.Container(
                expand=True,
                bgcolor="black",
                content=ft.Stack([
                    ft.Container(
                        content=ft.Image(src=src, fit=ft.ImageFit.CONTAIN),
                        alignment=ft.Alignment(0, 0),
                        on_click=lambda e: asyncio.create_task(close_image_viewer(e)), # Click background to close
                        expand=True
                    ),
                    ft.Container(
                        content=ft.IconButton(ft.Icons.CLOSE, icon_color="white", icon_size=30, on_click=lambda e: asyncio.create_task(close_image_viewer(e))),
                        top=50, right=20,
                    )
                ], expand=True)
            )
        ]
        image_viewer.visible = True
        page.update()

    # Original Layout
    chat_main_layout = ft.Column(expand=True, spacing=0)
    root_view = ft.Stack([chat_main_layout, image_viewer], expand=True)

    async def load_topics_async(update_ui=True, show_all=False):
        # [FIX] Thread Synchronization: prevent overlapping reloads
        if state.get("is_loading_topics"): return
        state["is_loading_topics"] = True

        if not state.get("is_active"): 
            state["is_loading_topics"] = False
            return
            
        try:
            # [FIX] Absolute Session Data: Use closure-scoped variables for reliability
            uid = page.app_session.get("user_id") if (hasattr(page, "session") and page.app_session) else current_user_id
            cid = page.app_session.get("channel_id") if (hasattr(page, "session") and page.app_session) else current_channel_id
            
            if not uid or not cid:
                log_info(f"Chat WARNING: load_topics_thread skipped (Missing IDs). UID={uid}, CID={cid}")
                return
            
            if update_ui: 
                try: page.update()
                except: pass
            
            log_info(f"Loading topics for {uid} in {cid}")
            
            # [TIMEOUT SAFETY] 10s limit for network ops
            categories_data = await asyncio.wait_for(asyncio.to_thread(chat_service.get_categories, cid), timeout=10)
            log_info(f"Categories loaded: {len(categories_data) if categories_data else 0}")
            categories = [c['name'] for c in categories_data] if categories_data else ["공지", "일반", "중요", "개별 업무"]

            if update_ui: 
                try: page.update()
                except: pass

            if show_all:
                topics = await asyncio.wait_for(asyncio.to_thread(chat_service.get_all_topics, cid), timeout=10)
            else:
                topics = await asyncio.wait_for(asyncio.to_thread(chat_service.get_topics, uid, cid), timeout=10)
                
            log_info(f"Topics fetched: {len(topics)}")
            # file_log_info(f"DEBUG_TOPICS: Topic IDs: {[t['id'] for t in topics]}")
            if len(topics) == 0:
                log_info("WARNING: No topics returned from database - user may need to create one or check membership")
            sorted_topics = sorted(topics, key=lambda x: (x.get('display_order', 0) or 0, x.get('created_at', '')), reverse=True)
            
            # [FIX] Efficient Unread Count Fetching
            unread_counts = await asyncio.wait_for(asyncio.to_thread(chat_service.get_unread_counts, uid, topics), timeout=10)
            log_info(f"Unreads for {uid}: {sum(unread_counts.values()) if unread_counts else 0}")

            new_controls = []
            if state["edit_mode"]:
                edit_list_ctrls = []
                grouped = {c: [] for c in categories}
                orphaned = []  # Topics without category or with deleted category
                
                for t in sorted_topics:
                    cat = t.get('category')
                    if cat and cat in categories:
                        if cat not in grouped: grouped[cat] = []
                        grouped[cat].append(t)
                    else:
                        # Topic has no category OR category was deleted
                        orphaned.append(t)
                
                # Show orphaned topics first if any exist
                if orphaned:
                    edit_list_ctrls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text("• 미분류", size=12, weight="bold", color="#FF9800"),
                                ft.Text(str(len(orphaned)), size=10, color="#BDBDBD")
                            ], alignment="spaceBetween"),
                            padding=ft.padding.only(left=20, right=20, top=10, bottom=5),
                            bgcolor="#FFF3E0",
                        )
                    )
                    
                    for t in orphaned:
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
                                delete_btn,
                                ft.Text(t['name'], size=14, color="#212121"),
                                edit_topic_btn
                            ], alignment=ft.MainAxisAlignment.START),
                            padding=ft.padding.symmetric(horizontal=20, vertical=12),
                            bgcolor="white",
                            data={"type": "topic", "id": tid, "topic_name": t['name']}
                        )
                        edit_list_ctrls.append(item)
                
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
                                                 on_click=lambda e, cid=cat_id, cn=cat_name: asyncio.create_task(open_rename_cat_dialog(cid, cn)))
                                ], spacing=5),
                                ft.Text(str(len(grouped[cat_name])), size=10, color="#BDBDBD")
                            ], alignment="spaceBetween"),
                            padding=ft.padding.only(left=20, right=20, top=10, bottom=5),
                            bgcolor="#FAFAFA",
                            data={"type": "category", "id": cat_id, "name": cat_name} # Tag for Reorder
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
                                delete_btn,
                                ft.Text(t['name'], size=16, weight="bold", color="#424242"),
                                edit_topic_btn
                            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=ft.padding.symmetric(horizontal=15, vertical=12),
                            bgcolor="white", border=ft.border.only(bottom=ft.border.BorderSide(1, "#F5F5F5")),
                            data={"type": "topic", "id": tid, "topic_name": t['name']} 
                        )
                        edit_list_ctrls.append(item)
                
                list_view = ft.ReorderableListView(
                    expand=True, 
                    on_reorder=on_topic_reorder, 
                    show_default_drag_handles=True, # Enable default handles
                    padding=0,
                    controls=edit_list_ctrls
                )
                new_controls = [list_view]
            else:
                list_view_ctrls = []
                grouped = {c: [] for c in categories}
                for t in sorted_topics:
                    cat = t.get('category') # Default to None (Uncategorized)
                    if cat not in grouped: grouped[cat] = []
                    grouped[cat].append(t)
                


                # 2. Show Categories
                # Handle "None" (Uncategorized) as "일반"
                if None in grouped:
                    general_items = grouped.pop(None)
                    if "일반" in grouped:
                        grouped["일반"].extend(general_items)
                    else:
                        grouped["일반"] = general_items
                        if "일반" not in categories:
                            categories.insert(0, "일반") # Add to front if missing

                # Prioritize 'categories' order
                known_cats = [c for c in categories if c in grouped]
                unknown_cats = [k for k in grouped.keys() if k not in known_cats] # Keys are strings now
                
                for cat_name in known_cats + unknown_cats:
                    # Render Header
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
                        tid = t['id']; is_priority = t.get('is_priority', False); 
                        # [Iteration 21] Robust lookup (handles both int and str keys)
                        unread_count = unread_counts.get(tid, unread_counts.get(str(tid), 0))
                        badge = ft.Container(
                            content=ft.Text(str(unread_count), size=11, color="white", weight="bold"),
                            bgcolor="#FF5252", 
                            padding=ft.padding.symmetric(horizontal=8, vertical=4), 
                            border_radius=12,
                            alignment=ft.Alignment(0, 0)
                        ) if unread_count > 0 else ft.Container()
                        
                        prio_icon = ft.Icon(ft.Icons.ERROR_OUTLINE, size=20, color="#FF5252") if is_priority else ft.Container()

                        list_view_ctrls.append(
                            ft.Container(
                                content=ft.Row([
                                    ft.Row([prio_icon, ft.Text(t['name'], size=16, weight="bold", color="#424242")], spacing=10),
                                    ft.Row([
                                        badge, # [SYNC CHECK] Badge must be visible here
                                        ft.Icon(ft.Icons.ARROW_FORWARD_IOS, size=14, color="#BDBDBD")
                                    ], spacing=10)
                                ], alignment="spaceBetween"),
                                padding=ft.padding.symmetric(horizontal=20, vertical=15),
                                bgcolor="white", 
                                border=ft.border.only(bottom=ft.border.BorderSide(1, "#F5F5F5")),
                                on_click=lambda e, topic=t: asyncio.create_task(select_topic(topic))
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
                                ft.Text("우측 상단 + 버튼을 눌러 만들어보세요", size=14, color="#BDBDBD"),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                            alignment=ft.Alignment(0, 0),
                            padding=40
                        )
                    )
                
                list_view = ft.ListView(expand=True, spacing=0, padding=0, controls=list_view_ctrls)
                new_controls = [list_view]
            
            topic_list_container.controls = new_controls
            
            # [DEBUG] Show detailed count
            if update_ui: 
                try:
                    if topic_list_container.page:
                        topic_list_container.update()
                        page.update()
                except Exception as update_ex:
                    # If update fails (e.g. user navigation), just log it
                    log_info(f"UI Update skipped: {update_ex}")

        except Exception as ex:
            log_info(f"Load Topics Critical Error: {ex}")
            # [FIX] Only show error if we are still on the page and it's not a detaching error
            if update_ui and "Control must be added" not in str(ex):
                try:
                     if topic_list_container.page:
                        page.open(ft.SnackBar(ft.Text(f"데이터 로딩 오류: {ex}"), bgcolor="red"))
                        page.update()
                except Exception:
                    pass  # Snackbar update failed
        finally:
            # [FIX] Always release lock
            state["is_loading_topics"] = False

    def load_topics(update_ui=True, show_all=False):
        # Fire and forget task to keep UI responsive
        asyncio.create_task(load_topics_async(update_ui=update_ui, show_all=show_all))

    def on_topic_reorder(e):
        async def _async_reorder():
            try:
                list_ctrl = topic_list_container.controls[0]
                if not list_ctrl: return
                controls = list_ctrl.controls
                moved_item = controls.pop(e.old_index)
                controls.insert(e.new_index, moved_item)
                
                current_cat_name = "일반" 
                max_score = len(controls) * 10
                
                for i, ctrl in enumerate(controls):
                    data = ctrl.data
                    if not data: continue
                    
                    dtype = data.get("type")
                    if dtype == "category":
                        current_cat_name = data.get("name")
                    elif dtype == "topic":
                        tid = data.get("id")
                        score = max_score - i
                        t_name = data.get("topic_name")
                        await asyncio.to_thread(chat_service.update_topic, tid, t_name, current_cat_name)
                        await asyncio.to_thread(chat_service.update_topic_order, tid, score, current_user_id)

                asyncio.create_task(load_topics_async(True))
            except Exception as ex:
                log_info(f"Reorder Error: {ex}")
                
        asyncio.create_task(_async_reorder())

    async def toggle_priority(tid, current_val):
        try:
            await asyncio.to_thread(chat_service.toggle_topic_priority, tid, current_val, current_user_id)
            asyncio.create_task(load_topics_async(True))
        except PermissionError as perm_err:
            page.open(ft.SnackBar(ft.Text(str(perm_err)), bgcolor="red"))
            page.update()
        except Exception as ex:
            log_info(f"Toggle priority error: {ex}")

    async def open_manage_categories_dialog(e):
        cat_list = ft.Column(spacing=5)
        new_cat_input = ft.TextField(hint_text="새 주제 이름", expand=True)
        
        async def refresh_cats():
            cid = page.app_session.get("channel_id")
            cats = await asyncio.to_thread(chat_service.get_categories, cid)
            items = []
            for c in cats:
                items.append(ft.Row([
                    ft.Text(c['name'], weight="bold", expand=True),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="red", on_click=lambda e, cid=c['id']: asyncio.create_task(delete_cat(cid)))
                ]))
            cat_list.controls = items
            page.update()

        async def add_cat(e):
            if new_cat_input.value:
                cid = page.app_session.get("channel_id")
                await asyncio.to_thread(chat_service.create_category, new_cat_input.value, cid)
                await refresh_cats()
                asyncio.create_task(load_topics_async(True))
                new_cat_input.value = ""
                new_cat_input.update()

        async def delete_cat(cid_to_del):
            await asyncio.to_thread(chat_service.delete_category, cid_to_del)
            await refresh_cats()
            asyncio.create_task(load_topics_async(True))

        asyncio.create_task(refresh_cats())
        asyncio.create_task(refresh_cats())
        
        # [FAUX DIALOG] Manage Categories
        manage_cat_card = ft.Container(
            width=min(400, (page.window_width or 400) * 0.94),
            padding=20,
            bgcolor=AppColors.SURFACE,
            border_radius=20,
            on_click=lambda e: e.control.page.update(),
            content=ft.Column([
                ft.Text("주제(그룹) 관리", size=20, weight="bold", color=AppColors.TEXT_PRIMARY),
                ft.Container(height=10),
                ft.Row([new_cat_input, ft.IconButton(ft.Icons.ADD, on_click=lambda e: asyncio.create_task(add_cat(e)))]),
                ft.Divider(),
                ft.Column([cat_list], scroll=ft.ScrollMode.AUTO, height=200) 
            ], tight=True)
        )
        # Add close button explicitly to content if needed or rely on overlay close
        # Here we add a close button at bottom
        manage_cat_card.content.controls.append(
             ft.Row([ft.TextButton("닫기", on_click=lambda _: overlay.close())], alignment=ft.MainAxisAlignment.END)
        )
        
        overlay.open(manage_cat_card)
        page.update()

    async def open_topic_member_management_dialog(e):
        try:
            print(f"DEBUG: Opening Member Dialog. TopicID={state.get('current_topic_id')}")
            if not state.get("current_topic_id"): 
                page.open(ft.SnackBar(ft.Text("오류: 선택된 토픽이 없습니다."), bgcolor="red"))
                page.update()
                return
        
            # Load Data
            topic_id = state.get("current_topic_id")
            channel_id = page.app_session.get("channel_id")
            
            # [Iteration 25] Fetch Topic Creator
            try:
                topic_info = service_supabase.table("chat_topics").select("created_by").eq("id", topic_id).single().execute()
                creator_id = topic_info.data.get("created_by") if topic_info.data else None
            except:
                creator_id = None

            # UI Holders
            members_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
            invite_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
            
            # Views (initialized late)
            members_view = ft.Column(visible=True)
            invite_view = ft.Column(visible=False)

            def load_members():
                async def _load_members_async():
                    try:
                        members = await asyncio.to_thread(chat_service.get_topic_members, topic_id)
                        items = []
                        current_uid = page.app_session.get("user_id")
                        my_ch_role = page.app_session.get("user_role")

                        # [DIAGNOSTIC] Log member list to terminal
                        print(f"DEBUG: Topic Members for {topic_id}: {len(members)}", flush=True)
                        for m in members:
                             print(f"  - {m.get('full_name')} ({m.get('user_id')}) role={m.get('permission_level')}", flush=True)

                        for m in members:
                            is_me = m['user_id'] == current_uid

                            # [Iteration 24 Fix] User WANTS to see themselves in Member List.
                            # if is_me: continue

                            # [Fix] Delete button should appear only for non-owner members
                            # Owner (creator) should not have delete button
                            is_owner = (m['user_id'] == creator_id)
                            can_kick = (my_ch_role in ['owner', 'manager']) and not is_me and not is_owner

                            items.append(
                                ft.Container(
                                    padding=10,
                                    bgcolor="#F5F5F5",
                                    border_radius=8,
                                    content=ft.Row([
                                        ft.Row([
                                            ft.Icon(ft.Icons.PERSON, size=20, color="grey"),
                                            ft.Column([
                                                ft.Row([
                                                    ft.Text(f"{m['full_name']}", weight="bold"),
                                                    ft.Container(
                                                        content=ft.Text("👑 방장", size=10, color="orange", weight="bold"),
                                                        padding=ft.padding.symmetric(horizontal=4, vertical=2),
                                                        # Use Hex for opacity to avoid 'ft.Colors' attribute error. #1A = ~10% alpha, FF9800 = Orange
                                                        bgcolor="#1AFF9800",
                                                        border_radius=4,
                                                        visible=(m['user_id'] == creator_id)
                                                    )
                                                ], spacing=5),
                                                ft.Text(f"{m['email']} • {m['permission_level']}", size=12, color="grey")
                                            ], spacing=2)
                                        ]),
                                        ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, icon_color="red",
                                                    tooltip="내보내기",
                                                    on_click=lambda e, u=m['user_id']: asyncio.create_task(kick_member(u)),
                                                    visible=can_kick)
                                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                                )
                            )
                    
                        if not items:
                            items.append(
                                ft.Container(
                                    content=ft.Column([
                                        ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=40, color="grey"),
                                        ft.Text("참여 중인 멤버가 아무도 없습니다.", color="grey", size=14)
                                    ], horizontal_alignment="center", spacing=10),
                                    padding=20,
                                    alignment=ft.Alignment(0, 0)
                                )
                            )

                        members_col.controls = items
                        page.update()

                    except Exception as ex:
                        print(f"Load Members Error: {ex}")
                        members_col.controls = [
                            ft.Container(
                                content=ft.Column([
                                    ft.Icon(ft.Icons.ERROR_OUTLINE, color="red", size=30),
                                    ft.Text(f"멤버 정보를 불러오지 못했습니다:\n{str(ex)[:100]}", color="red", size=12, text_align="center")
                                ], horizontal_alignment="center"),
                                padding=20, alignment=ft.Alignment(0, 0)
                            )
                        ]
                        page.update()

                asyncio.create_task(_load_members_async())

            async def kick_member(target_id):
                try:
                    await asyncio.to_thread(chat_service.remove_topic_member, topic_id, target_id)
                    load_members()
                except Exception as ex:
                    page.open(ft.SnackBar(ft.Text(f"오류: {ex}"), bgcolor="red")); page.update()

            async def load_candidates():
                try:
                    current_uid = str(page.app_session.get("user_id")).strip()

                    # [Iteration 25 Fix] Pass current_uid to service to force-filter it out at source
                    candidates = await asyncio.to_thread(chat_service.get_channel_members_not_in_topic, channel_id, topic_id, current_uid)
                    items = []

                    for c in candidates:
                        # Double-check (though service handles it now)
                        if str(c['user_id']).strip() == current_uid: continue

                        # [Iteration 26] Disambiguation Logic
                        candidate_name = c['full_name']
                        disambig_info = ""
                        if c.get("username"):
                            disambig_info = f" (@{c['username']})"
                        else:
                            # Fallback to ID suffix if no unique username
                            try:
                                short_id = str(c['user_id']).strip()[-4:] # Last 4 chars
                                disambig_info = f" (#{short_id})"
                            except:
                                disambig_info = ""

                        items.append(
                            ft.Container(
                                padding=10, border=ft.border.all(1, "#EEEEEE"), border_radius=8,
                                content=ft.Row([
                                    ft.Row([
                                        ft.Icon(ft.Icons.PERSON_OUTLINE, size=20, color="grey"),
                                        ft.Column([
                                            ft.Row([
                                                ft.Text(f"{candidate_name}", weight="bold"),
                                                ft.Text(f"{disambig_info}", size=12, color="grey")
                                            ], spacing=5),
                                            # ft.Text(f"ID: {can_id}", size=10, color="grey") # Optional debug
                                        ], spacing=2)
                                    ]),
                                    ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color="green",
                                                tooltip="초대",
                                                on_click=lambda e, u=c['user_id']: asyncio.create_task(invite_user(u)))
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                            )
                        )
                    if not items:
                        items.append(ft.Container(content=ft.Text("초대할 수 있는 멤버가 없습니다.\n(모든 직원이 이미 참여 중입니다)", color="grey", text_align="center"), alignment=ft.Alignment(0, 0), padding=20))

                    invite_col.controls = items
                    # [DEBUG] Feedback
                    print(f"Candidates Loaded: {len(items)}")
                    page.update()

                except Exception as ex:
                    print(f"Load Candidates Error: {ex}")

            async def invite_user(target_id):
                try:
                    await asyncio.to_thread(chat_service.add_topic_member, topic_id, target_id)
                    # Toggle back
                    invite_view.visible = False
                    members_view.visible = True
                    load_members()
                    page.update()
                except Exception as ex:
                    page.open(ft.SnackBar(ft.Text(f"초대 실패: {ex}"), bgcolor="red")); page.update()

            def show_invite_view(e):
                members_view.visible = False
                invite_view.visible = True
                asyncio.create_task(load_candidates())
                page.update()
            
            def show_members_view(e):
                invite_view.visible = False
                members_view.visible = True
                page.update()

            members_view.controls = [
                ft.Text("현재 멤버", size=16, weight="bold"),
                # Removed invalid max_height. Use default wrapping behavior.
                ft.Container(content=members_col),
                ft.ElevatedButton("멤버 초대하기", on_click=show_invite_view, width=200, bgcolor=AppColors.PRIMARY, color="white")
            ]
            
            invite_view.controls = [
                ft.Row([
                    ft.IconButton(ft.Icons.ARROW_BACK, on_click=show_members_view),
                    ft.Text("멤버 초대", size=16, weight="bold")
                ]),
                ft.Container(content=invite_col, height=300)
            ]

            # [FAUX DIALOG] Member Management
            member_card = ft.Container(
                width=min(450, (page.window_width or 450) * 0.94),
                padding=20,
                bgcolor=AppColors.SURFACE,
                border_radius=20,
                on_click=lambda e: e.control.page.update(),
                content=ft.Column([
                    ft.Text("채팅방 멤버 관리", size=20, weight="bold", color=AppColors.TEXT_PRIMARY),
                    ft.Container(height=10),
                    ft.Column([members_view, invite_view], tight=True, scroll=ft.ScrollMode.AUTO),
                    ft.Row([ft.TextButton("닫기", on_click=lambda _: overlay.close())], alignment=ft.MainAxisAlignment.END)
                ], tight=True)
            )
            overlay.open(member_card)

            # Call load_members safely
            try:
                load_members()
            except Exception:
                pass  # Member list load failed

        except Exception as e:
            print(f"CRITICAL ERROR in Member Dialog: {e}")
            import traceback
            traceback.print_exc()
            page.open(ft.SnackBar(ft.Text(f"대화상자 열기 실패: {e}"), bgcolor="red"))
            page.update()
    # [FIX] Render ID to prevent race conditions in fast reloads
    render_context = {"last_id": 0}

    async def load_messages_async():
        # [FIX] Thread Synchronization: prevent overlapping reloads
        if state.get("is_loading_messages") or not state["current_topic_id"] or not state["is_active"]: return
        state["is_loading_messages"] = True
        
        # Increment Render ID
        render_context["last_id"] += 1
        my_id = render_context["last_id"]
        
        sel_mode = bool(state.get("selection_mode"))
        print(f"DEBUG_CHAT: load_messages_async starting with sel_mode={sel_mode}")
        render_user_id = page.app_session.get("user_id")
        tid = state["current_topic_id"]
        # print(f"DEBUG_CHAT: [Thread {my_id}] RenderStart. User={render_user_id}, Topic={tid}", flush=True)

        try:
            # [TIMEOUT SAFETY] 10s limit
            db_messages = await asyncio.wait_for(asyncio.to_thread(chat_service.get_messages, state["current_topic_id"]), timeout=10)
            
            # [OPTIMIZATION] Incremental Updates
            # Compare current controls with DB messages to only add new ones
            existing_controls = message_list_view.controls
            existing_count = len(existing_controls) if existing_controls else 0
            db_count = len(db_messages)
            
            def on_msg_select(mid, val):
                if val: state.add_selected(mid)
                else: state.remove_selected(mid)

            # Rebuild if: empty, smaller than before (deletions), or special mode (select/search)
            is_special = sel_mode or (existing_count > 0 and not isinstance(existing_controls[0], ChatBubble))
            should_rebuild = existing_count == 0 or db_count < existing_count or is_special
            
            if should_rebuild:
                new_controls = []
                for m in db_messages:
                    new_controls.append(ChatBubble(m, render_user_id, selection_mode=sel_mode, on_select=on_msg_select, on_image_click=show_image_viewer))
                
                if my_id == render_context["last_id"]:
                    message_list_view.controls = new_controls
                    # Auto-scroll on initial load if we were near bottom or it's a new room
                    if not state.get("scrolled_to_unread"):
                        await message_list_view.scroll_to_async(offset=-1, duration=300) if hasattr(message_list_view, "scroll_to_async") else message_list_view.scroll_to(offset=-1, duration=300)
                        state["scrolled_to_unread"] = True
            else:
                # Append only new messages
                last_loaded_id = state.get("last_loaded_msg_id")
                new_msgs_to_append = []
                found_last = (last_loaded_id is None)
                
                for m in db_messages:
                    if found_last:
                        new_msgs_to_append.append(m)
                    elif str(m.get("id")) == str(last_loaded_id):
                        found_last = True
                
                if new_msgs_to_append and my_id == render_context["last_id"]:
                    for m in new_msgs_to_append:
                        message_list_view.controls.append(ChatBubble(m, render_user_id, selection_mode=sel_mode, on_select=on_msg_select, on_image_click=show_image_viewer))
                    
                    # Scroll logic for new messages
                    # If it's my message, scroll. If others, show indicator.
                    is_me = (new_msgs_to_append[-1].get("user_id") == current_user_id)
                    if is_me:
                        await message_list_view.scroll_to_async(offset=-1, duration=200) if hasattr(message_list_view, "scroll_to_async") else message_list_view.scroll_to(offset=-1, duration=200)
                    else:
                        floating_new_msg_container.visible = True
                        floating_new_msg_container.update()
            
            # 5. Atomic Update UI (Only if we are the LATEST thread)
            if my_id == render_context["last_id"]:
                if db_messages:
                    state["last_loaded_msg_id"] = db_messages[-1].get("id")
                
                try: page.update()
                except: pass
            
        except asyncio.TimeoutError:
            log_info(f"DEBUG_CHAT: [Thread {my_id}] Timeout loading messages.")
            state["is_loading_messages"] = False
        except Exception as ex:
            log_info(f"DEBUG_CHAT: [Thread {my_id}] Error: {ex}")
            log_info(f"Load Messages Error: {ex}")
        finally:
            # Atomic Update state and UI
            if my_id == render_context["last_id"]:
                state["is_loading_messages"] = False # Unlock
    async def select_topic(topic):
        tid = topic['id']
        state["current_topic_id"] = tid
        state["scrolled_to_unread"] = False # Reset for new room entry
        state["last_loaded_msg_id"] = None  # [FIX] Clear for ghost scroll guard
        state["last_read_at"] = None        # [FIX] Clear to prevent stale entry scroll
        
        # [PRE-LOAD] Fetch last_read_at before we update it
        async def fetch_read_and_load():
            try:
                read_map = await asyncio.to_thread(chat_service.get_user_read_status, current_user_id)
                state["last_read_at"] = read_map.get(tid)
                
                # Trigger message load
                asyncio.create_task(load_messages_async())
                
                # We don't mark as read just by entering. User must scroll to bottom.
                
                # Background refresh topics so list gets updated (unread counts)
                asyncio.create_task(load_topics_async(update_ui=False))
            except Exception as ex:
                log_info(f"Select Topic Thread Error: {ex}")
                load_messages()

        if chat_title_ref.current:
            chat_title_ref.current.value = topic['name']
            # No update() here, page.update() below will handle it once the view switches
        msg_input.disabled = False
        state["view_mode"] = "chat"
        update_layer_view()
        
        message_list_view.controls = [ft.Container(ft.ProgressRing(color="#2E7D32"), alignment=ft.Alignment(0, 0), padding=50)]
        page.update()

        asyncio.create_task(fetch_read_and_load())

    def load_messages():
        asyncio.create_task(load_messages_async())

    async def send_message(content=None, image_url=None):
        final_image_url = image_url or state.get("pending_image_url")
        final_content = content or msg_input.value
        
        if not final_content and not final_image_url: return
        if not state["current_topic_id"]: return
        
        # [OPTIMISTIC UI] 1. Inject Local Message Immediately
        # from views.components.chat_bubble import ChatBubble
        from datetime import datetime
        import time
        
        # Construct Temporary Message
        temp_msg = {
            "id": f"temp_{time.time()}",
            "content": final_content,
            "image_url": final_image_url,
            "user_id": current_user_id,
            "created_at": datetime.now().isoformat(),
            "is_sending": True, # Flag for Bubble Opacity/Icon
            "profiles": {"full_name": "나", "username": "Me"} 
        }
        
        # Append to View
        if not message_list_view.controls:
            message_list_view.controls = []
        message_list_view.controls.append(ChatBubble(temp_msg, current_user_id))
        
        # Clear Inputs Immediately (Instant Feel)
        msg_input.value = ""
        msg_input.focus()
        state["pending_image_url"] = None
        pending_container.visible = False
        pending_container.content = ft.Container()
        page.update()
        
        # 2. Background Send
        async def _do_send():
            try:
                await asyncio.to_thread(chat_service.send_message, state["current_topic_id"], final_content, final_image_url, current_user_id)
                # Realtime will likely trigger update, but we call load just in case
                # The load_messages_thread will merge/remove the temp message once DB has it
                asyncio.create_task(load_messages_async())
            except Exception as ex:
                page.open(ft.SnackBar(ft.Text(f"전송 실패: {ex}"), bgcolor="red"))
                page.update()
        
        asyncio.create_task(_do_send())

    pending_container = ft.Container(visible=False, padding=10, bgcolor="#3D4446", border_radius=10)
    
    # [FIX] Local FilePicker Logic
    async def on_chat_file_result(e: ft.ControlEvent):
        if not e.files: return
        f = e.files[0]
        from utils.logger import log_info
        log_info(f"File Selected: {f.name}, Size: {f.size} bytes")
        # Immediate Feedback
        page.open(ft.SnackBar(ft.Text("파일 확인 중...")))
        page.update()

        if not state["current_topic_id"]:
            page.open(ft.SnackBar(ft.Text("대화방을 먼저 선택해주세요."), bgcolor="red"))
            page.update()
            return
            
        f = e.files[0]
        is_web_mode = page.web # Capture safely

        # [FIX] Main Thread Execution for Upload Trigger
        # Previously inside a thread, which caused reliable upload issues.
        async def update_snack(msg):
            try:
                page.open(ft.SnackBar(ft.Text(msg, size=12)))
                page.update()
            except Exception:
                pass  # Snackbar update failed

        async def show_error_ui(msg, color="red"):
             try:
                 pending_container.content = ft.Container(
                     ft.Text(msg, color="white", size=11),
                     bgcolor=color, padding=5, border_radius=5
                 )
                 pending_container.update()
                 await asyncio.sleep(5)
                 pending_container.visible = False
                 page.update()
             except Exception:
                 pass  # Error UI display failed

        try:
            update_snack(f"1/4. '{f.name}' 준비 중...")
            
            # [DEBUG] Immediate Upload (Main Thread)
            from utils.logger import log_info
            log_info(f"DEBUG: Calling handle_file_upload in Main Thread. Web={is_web_mode}")
            
            # [FIX] Use e.control to target the EXACT picker that triggered this event
            # addressing potential ID mismatch or instance staleness
            active_picker = e.control
            
            # Synchronous Call triggers Browser Command immediately
            result = await asyncio.to_thread(storage_service.handle_file_upload, is_web_mode, f, update_snack, picker_ref=active_picker)
            
            if result and "public_url" in result:
                 state["pending_image_url"] = result["public_url"]
            
            if result:
                 if result.get("type") == "proxy_upload_triggered":
                      s_name = result["storage_name"]
                      state["pending_storage_name"] = s_name
                      update_snack("2/4. 서버 전송 시작...")
                      
                      pending_container.content = ft.Row([
                            ft.Container(ft.ProgressRing(stroke_width=2, color="white"), width=40, height=40, alignment=ft.Alignment(0, 0), bgcolor="#424242", border_radius=5),
                            ft.Column([
                                ft.Text("서버 처리 중...", size=12, weight="bold", color="white"),
                                ft.Text("파일을 저장하고 있습니다.", size=10, color="white70"),
                            ], spacing=2, tight=True),
                         ], spacing=10)
                      pending_container.visible = True
                      page.update()

                      # [BACKGROUND WATCHER]
                      async def watch_server_file_target(target_name):
                            import time, os, traceback
                            try:
                                # [SCOPE FIX] Use Argument
                                current_storage_name = target_name
                                target_path = os.path.join("uploads", current_storage_name)
                                log_info(f"Server Watcher Started: {target_path}")
                                
                                # [SMART WATCHER] Snapshot existing files
                                initial_snapshot = set()
                                if os.path.exists("uploads"):
                                    initial_snapshot = set(os.listdir("uploads"))
                                log_info(f"Watcher Snapshot: {len(initial_snapshot)} ignored.")

                                # Wait up to 60 seconds
                                for i in range(60):
                                    await asyncio.sleep(1.0)
                                    if not os.path.exists("uploads"): continue

                                    # Check for Target OR New Files
                                    found_new = False
                                    if os.path.exists(target_path):
                                        found_new = True
                                    else:
                                        try:
                                            # Check Candidates
                                            current_files = set(os.listdir("uploads"))
                                            new_candidates = current_files - initial_snapshot
                                            if new_candidates:
                                                detected_name = list(new_candidates)[0]
                                                log_info(f"SMART MATCH: New file detected: {detected_name}")
                                                current_storage_name = detected_name
                                                target_path = os.path.join("uploads", current_storage_name)
                                                found_new = True
                                        except Exception:
                                            pass  # File detection failed
                                    
                                    if found_new:
                                        # Stabilize
                                        try:
                                            size1 = os.path.getsize(target_path)
                                            await asyncio.sleep(1.0)
                                            if os.path.exists(target_path) and os.path.getsize(target_path) == size1:
                                                 log_info("File Stable. Finalizing.")
                                                 final_url = await asyncio.to_thread(storage_service.upload_proxy_file_to_supabase, current_storage_name)
                                                 state["pending_image_url"] = final_url
                                                 await update_pending_ui(final_url)
                                                 page.open(ft.SnackBar(ft.Text("🔒 보안 업로드 완료!"), bgcolor="green"))
                                                 page.update()
                                                 return
                                        except Exception as fin_ex:
                                             log_info(f"Finalize Error: {fin_ex}")
                                             await show_error_ui(f"업로드 실패: {fin_ex}")
                                             return
                                    
                                    # Feedback (Simplified)
                                    if i % 3 == 0:
                                        try:
                                            # Optional: Update text if container is valid
                                            pass
                                        except Exception:
                                            pass  # UI feedback update failed

                                log_info("Watcher Timeout")
                                await show_error_ui("시간 초과: 파일을 찾을 수 없습니다.")
                            
                            except Exception as ex:
                                log_info(f"Watcher Crash: {ex}")
                                await show_error_ui(f"시스템 오류: {ex}")

                      asyncio.create_task(watch_server_file_target(s_name))

                 elif result.get("type") == "web_upload_triggered":
                      pass
                 else:
                      # Native
                      update_pending_ui(result.get("public_url"))
                      update_snack("4/4. 이미지 준비 완료")
            else:
                 update_snack("업로드 요청 실패")

        except Exception as logic_ex:
            print(f"Sync Logic Error: {logic_ex}")
            await update_snack(f"처리 중 오류: {logic_ex}")

    async def on_chat_upload_progress(e: ft.ControlEvent):
        from utils.logger import log_info
        log_info(f"Upload Progress: {e.progress:.2f}, Error: {e.error}")
        
        if e.error:
            log_info(f"CRITICAL: Upload Event Error: {e.error}")
            page.open(ft.SnackBar(ft.Text(f"업로드 실패: {e.error}"), bgcolor="red"))
            page.update()
            pending_container.visible = False
            page.update()
        else:
            # Update Progress Text
            try:
                if pending_container.visible and isinstance(pending_container.content, ft.Row):
                    prog_txt = pending_container.content.controls[1].controls[1]
                    prog_txt.value = f"{int(e.progress * 100)}% 서버 도착"
                    page.update()
            except Exception:
                pass  # Progress UI update failed

            if e.progress == 1.0:
                s_name = state.get("pending_storage_name")
                if s_name:
                    # [PROXY FINALIZATION]
                    state["pending_storage_name"] = None # Reset
                    
                    async def finalize_step():
                        try:
                             final_url = await asyncio.to_thread(storage_service.upload_proxy_file_to_supabase, s_name)
                             state["pending_image_url"] = final_url
                             
                             # Success UI
                             asyncio.create_task(update_pending_ui(final_url))
                             page.open(ft.SnackBar(ft.Text("🔒 보안 업로드 완료!"), bgcolor="green"))
                             page.update()
                        except Exception as fin_ex:
                             print(f"Proxy Finalize Error: {fin_ex}")
                             page.open(ft.SnackBar(ft.Text(f"처리 실패: {fin_ex}"), bgcolor="red"))
                             page.update()
                             
                    asyncio.create_task(finalize_step())
                
                else:
                    asyncio.create_task(update_pending_ui(state.get("pending_image_url")))
                    page.open(ft.SnackBar(ft.Text("이미지 로드 완료!"), bgcolor="green"))
                    page.update()

    # [Flet 0.80+] FilePicker disabled due to compatibility issues
    local_file_picker = None

    async def update_pending_ui(public_url):
        if not public_url: return
        
        # [FIX] Robust File Type Detection
        clean_url = public_url.split("?")[0]
        ext = clean_url.split(".")[-1].lower() if "." in clean_url else ""
        
        image_exts = ["jpg", "jpeg", "png", "gif", "webp", "ico", "bmp"]
        video_exts = ["mp4", "mov", "avi", "wmv", "mkv", "webm"]
        
        preview_content = None
        status_text = "파일 준비 완료"
        
        if ext in image_exts:
             preview_content = ft.Image(
                src=public_url, 
                fit=ft.ImageFit.COVER,
                error_content=ft.Icon(ft.Icons.BROKEN_IMAGE, color="white") 
            )
             status_text = "이미지 준비 완료"
        elif ext in video_exts:
             preview_content = ft.Icon(ft.Icons.VIDEO_FILE, color="white", size=30)
             status_text = "동영상 준비 완료"
        else:
             preview_content = ft.Icon(ft.Icons.INSERT_DRIVE_FILE, color="white", size=30)

        pending_container.content = ft.Row([
            # Wrap Image/Icon in Container
            ft.Container(
                content=preview_content,
                width=50, 
                height=50, 
                border_radius=5, 
                bgcolor="#424242", # Dark grey placeholder
                border=ft.border.all(1, "#616161"),
                alignment=ft.Alignment(0, 0)
            ),
            ft.Column([
                ft.Text(status_text, size=12, weight="bold", color="white"),
                ft.Text("전송 버튼을 눌러 발송하세요.", size=10, color="white70"),
            ], spacing=2, tight=True),
            ft.IconButton(ft.Icons.CANCEL, icon_color="red", on_click=lambda _: asyncio.create_task(clear_pending()))
        ], spacing=10)
        pending_container.visible = True
        page.update()

    async def clear_pending():
        state["pending_image_url"] = None
        pending_container.visible = False
        page.update()
    
    # Note: FilePicker handlers are bound in get_or_create_file_picker()

    def confirm_delete_topic(tid):
        print(f"DEBUG: confirm_delete_topic requested for tid={tid}")
        def delete_it(e):
            print("DEBUG: Delete confirmed by user in dialog")
            async def _do_delete():
                print("DEBUG: Starting _do_delete async task")
                try:
                    print(f"DEBUG: Calling chat_service.delete_topic for {tid}")
                    await asyncio.to_thread(chat_service.delete_topic, tid, current_user_id)
                    print("DEBUG: Delete service call success. Reloading topics...")
                    # Force a slight delay to ensure DB propagation
                    await asyncio.sleep(0.5)
                    await load_topics_async(True) # Call directly to ensure it runs
                    print("DEBUG: Topics reloaded")
                except PermissionError as perm_err:
                    print(f"DEBUG: Permission Error: {perm_err}")
                    page.open(ft.SnackBar(ft.Text(str(perm_err)), bgcolor="red"))
                    page.update()
                except Exception as ex:
                    print(f"DEBUG: Critical Delete Error: {ex}")
                    log_info(f"Delete topic error: {ex}")
                    page.open(ft.SnackBar(ft.Text(f"삭제 실패: {ex}"), bgcolor="red"))
                    page.update()
            
            asyncio.create_task(_do_delete())
            dlg.open = False
            page.update()

        def close_dlg(_):
            overlay.close()

        # [FAUX DIALOG] Delete Confirmation
        delete_card = ft.Container(
            width=min(400, (page.window_width or 400) * 0.94),
            padding=20,
            bgcolor=AppColors.SURFACE,
            border_radius=20,
            on_click=lambda e: e.control.page.update(),
            content=ft.Column([
                ft.Text("스레드 삭제", size=20, weight="bold", color=AppColors.TEXT_PRIMARY),
                ft.Container(height=10),
                ft.Text("이 스레드와 모든 메시지가 삭제됩니다.\n(삭제 후 복구할 수 없습니다)"),
                ft.Container(height=20),
                ft.Row([
                    ft.TextButton("취소", on_click=close_dlg),
                    ft.TextButton(content=ft.Text("삭제", color="red"), on_click=delete_it)
                ], alignment=ft.MainAxisAlignment.END)
            ], tight=True)
        )
        overlay.open(delete_card)

    async def show_create_modal(e):
        log_info("Showing create modal (Faux)")
        modal_name_field.value = ""
        
        # [FAUX DIALOG] Create Topic
        create_card = ft.Container(
             width=min(400, (page.window_width or 400) * 0.94),
             bgcolor="white",
             border_radius=15,
             padding=30,
             on_click=lambda e: e.control.page.update(),
             content=ft.Column([
                ft.Row([
                    ft.Text("새 스레드 만들기", size=20, weight="bold", color="#212121"),
                    ft.IconButton(icon=ft.Icons.CLOSE, icon_color="#757575", on_click=lambda e: overlay.close())
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                modal_name_field,
                ft.Container(height=20),
                ft.Row([
                    ft.OutlinedButton(content=ft.Text("취소"), on_click=lambda e: overlay.close(), expand=1),
                    ft.ElevatedButton(content=ft.Text("만들기"), on_click=lambda e: asyncio.create_task(create_from_modal(e)), bgcolor="#2E7D32", color="white", expand=1)
                ], spacing=10)
            ], tight=True, spacing=15)
        )
        overlay.open(create_card)
        page.update()
    
    async def hide_create_modal(e):
        log_info("Hiding create modal")
        overlay.close()
    
    modal_name_field = ft.TextField(label="새 스레드 이름", autofocus=True, width=300)
    
    async def create_from_modal(e):
        # [CRITICAL DEBUG] Immediate feedback to verify click detection
        page.open(ft.SnackBar(
            ft.Text(f"🔍 버튼 클릭 감지됨! 값: '{modal_name_field.value}'", color="white"),
            bgcolor="purple",
            duration=5000
        ))
        page.update()
        
        log_info(f"Create from modal clicked, name='{modal_name_field.value}'")
        if not modal_name_field.value:
            log_info("ERROR: Name field is empty!")
            page.open(ft.SnackBar(
                ft.Text("스레드 이름을 입력해주세요", color="white"),
                bgcolor="orange"
            ))
            page.update()
            return
        
        async def _do_create():
            try:
                log_info(f"Creating topic from modal: {modal_name_field.value}")
                cid = page.app_session.get("channel_id")
                result = await asyncio.to_thread(chat_service.create_topic, modal_name_field.value, None, current_user_id, cid)  # None = no category
                log_info(f"Topic creation success: {modal_name_field.value}")
                
                # Hide modal and show success
                overlay.close()
                modal_name_field.value = ""  # Clear input for next time
                page.open(ft.SnackBar(
                    ft.Text("스레드가 생성되었습니다!", color="white"),
                    bgcolor="green"
                ))
                page.update()
                
                # [FIX] Reload topics immediately and await completion
                log_info("Reloading topics after creation...")
                try:
                    # Directly call the async version to ensure it completes
                    await load_topics_async(update_ui=True, show_all=False)
                    log_info("Topic list refreshed successfully")
                except Exception as reload_ex:
                    log_info(f"Reload error: {reload_ex}")
            except Exception as ex:
                log_info(f"Creation ERROR: {ex}")
                import traceback
                traceback.print_exc()
                page.open(ft.SnackBar(
                    ft.Text(f"생성 실패: {ex}", color="white"),
                    bgcolor="red"
                ))
                page.update()
        
        asyncio.create_task(_do_create())

    def open_rename_topic_dialog(topic):
        topic_id = topic['id']
        current_cat = topic.get('category')

        name_input = ft.TextField(value=topic['name'], label="스레드 이름", expand=True)
        cat_dropdown = ft.Dropdown(
            label="카테고리 이동",
            options=[],
            value=current_cat,
            expand=True
        )

        async def load_cats_for_dialog():
             cid = page.app_session.get("channel_id")
             cats = await asyncio.to_thread(chat_service.get_categories, cid)
             opts = [ft.dropdown.Option(c['name']) for c in cats]
             # Add Option for "Uncategorized"
             opts.insert(0, ft.dropdown.Option(key="none_val", text="미분류")) # We'll handle "none_val" -> None
             cat_dropdown.options = opts
             cat_dropdown.value = current_cat if current_cat else "none_val"
             page.update()

        asyncio.create_task(load_cats_for_dialog())
        
        async def do_update(e):
            if name_input.value:
                try:
                    new_cat = cat_dropdown.value
                    if new_cat == "none_val": new_cat = None
                    
                    await asyncio.to_thread(chat_service.update_topic, topic_id, name_input.value, new_cat)
                    overlay.close()
                    page.update()
                    load_topics(True)
                except Exception as ex:
                    log_info(f"Update Topic Error: {ex}")
                    page.open(ft.SnackBar(ft.Text(f"수정 실패: {ex}"), bgcolor="red")); page.update()
        
        # [FAUX DIALOG] Rename Topic
        rename_topic_card = ft.Container(
            width=min(400, (page.window_width or 400) * 0.94),
            padding=20,
            bgcolor=AppColors.SURFACE,
            border_radius=20,
            on_click=lambda e: e.control.page.update(),
            content=ft.Column([
                ft.Text("스레드 이름 수정", size=20, weight="bold", color=AppColors.TEXT_PRIMARY),
                ft.Container(height=10),
                name_input,
                ft.Container(height=10),
                cat_dropdown,
                ft.Container(height=20),
                ft.Row([
                    ft.TextButton("취소", on_click=lambda _: overlay.close()),
                    ft.ElevatedButton("저장", on_click=lambda e: asyncio.create_task(do_update(e)), bgcolor="#2E7D32", color="white")
                ], alignment=ft.MainAxisAlignment.END)
            ], tight=True)
        )
        overlay.open(rename_topic_card)

    def open_rename_cat_dialog(cat_id, old_name):
        if not cat_id: return # Cannot rename system default if missing ID
        name_input = ft.TextField(value=old_name, label="주제 그룹 이름", expand=True)
        
        async def do_rename(e):
            if name_input.value:
                try:
                    await asyncio.to_thread(chat_service.update_category, cat_id, old_name, name_input.value)
                    overlay.close()
                    page.update()
                    load_topics(True)
                except Exception as ex:
                    log_info(f"Rename Category Error: {ex}")

        # [FAUX DIALOG] Rename Category
        rename_cat_card = ft.Container(
            width=350,
            padding=20,
            bgcolor=AppColors.SURFACE,
            border_radius=20,
            on_click=lambda e: e.control.page.update(),
            content=ft.Column([
                ft.Text("주제 그룹 이름 수정", size=20, weight="bold", color=AppColors.TEXT_PRIMARY),
                ft.Container(height=10),
                name_input,
                ft.Container(height=20),
                ft.Row([
                    ft.TextButton("취소", on_click=lambda _: overlay.close()),
                    ft.ElevatedButton("저장", on_click=lambda e: asyncio.create_task(do_rename(e)), bgcolor="#2E7D32", color="white")
                ], alignment=ft.MainAxisAlignment.END)
            ], tight=True),
            alignment=ft.Alignment(0, 0)
        )
        overlay.open(rename_cat_card)

    edit_btn_ref = ft.Ref[ft.OutlinedButton]()
    async def toggle_edit_mode(e=None):
        state["edit_mode"] = not state["edit_mode"]
        if edit_btn_ref.current:
            edit_btn_ref.current.content = ft.Text("완료" if state["edit_mode"] else "편집")
            edit_btn_ref.current.style = ft.ButtonStyle(
                color="white" if state["edit_mode"] else "#424242",
                bgcolor="#2E7D32" if state["edit_mode"] else "transparent",
                shape=ft.RoundedRectangleBorder(radius=8),
                side=ft.BorderSide(1, "#2E7D32" if state["edit_mode"] else "#E0E0E0"),
                padding=ft.padding.symmetric(horizontal=12, vertical=0)
            )
            edit_btn_ref.current.update()
        await load_topics_async(True)

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

    # [SEARCH] Global Search Logic - Hoisted definitions to fix UnboundLocalError
    search_results_col = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, height=300)
    search_input = ft.TextField(hint_text="검색어 입력...", autofocus=True, expand=True)

    async def do_search(e=None):
        query = search_input.value
        if not query or len(query) < 2:
            page.open(ft.SnackBar(ft.Text("2글자 이상 입력해주세요."), bgcolor="red")); page.update()
            return

        search_results_col.controls = [ft.Container(ft.ProgressRing(), alignment=ft.Alignment(0, 0), padding=20)]
        page.update()

        async def _search_task():
            try:
                cid = page.app_session.get("channel_id")
                results = await asyncio.wait_for(asyncio.to_thread(chat_service.search_messages_global, query, cid), timeout=10)
                
                items = []
                if not results:
                    items.append(ft.Container(ft.Text("검색 결과가 없습니다.", color="grey"), padding=20, alignment=ft.Alignment(0, 0)))
                else:
                    for r in results:
                        topic_name = r.get('chat_topics', {}).get('name', '알 수 없음')
                        sender = r.get('profiles', {}).get('full_name', '알 수 없음')
                        content = r.get('content', '')
                        time_str = r.get('created_at', '')[:16].replace('T', ' ')
                        
                        items.append(
                            ft.Container(
                                content=ft.Column([
                                    ft.Row([
                                        ft.Text(topic_name, weight="bold", size=12, color="#1565C0"),
                                        ft.Text(time_str, size=10, color="grey")
                                    ], alignment="spaceBetween"),
                                    ft.Text(f"{sender}: {content}", size=14, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, color="#424242")
                                ], spacing=3),
                                padding=12,
                                border=ft.border.only(bottom=ft.border.BorderSide(1, "#EEEEEE")),
                                on_click=lambda e, t={'id': r['topic_id'], 'name': topic_name}: (
                                    overlay.close(),
                                    page.update(),
                                    asyncio.create_task(select_topic(t))
                                ),
                                ink=True
                            )
                        )
                
                search_results_col.controls = items
                page.update()
            except Exception as ex:
                print(ex)
                search_results_col.controls = [ft.Text(f"검색 오류: {ex}", color="red")]
                page.update()

        asyncio.create_task(_search_task())

    # Assign handler after definition
    search_input.on_submit = do_search

    async def open_search_dialog(e):
        search_input.value = ""
        search_results_col.controls = [ft.Text("검색어를 입력하고 엔터를 누르세요.", color="grey", size=12)]
        
        # [FAUX DIALOG] Search Dialog
        search_card = ft.Container(
            width=400,
            height=400,
            padding=20,
            bgcolor=AppColors.SURFACE,
            border_radius=20,
            on_click=lambda e: e.control.page.update(),
            content=ft.Column([
                ft.Text("전체 대화 검색", size=20, weight="bold", color=AppColors.TEXT_PRIMARY),
                ft.Container(height=10),
                ft.Row([search_input, ft.IconButton(ft.Icons.SEARCH, on_click=do_search)]),
                ft.Divider(),
                search_results_col,
                ft.Container(height=10),
                ft.Row([ft.TextButton("닫기", on_click=lambda _: overlay.close())], alignment=ft.MainAxisAlignment.END)
            ], tight=True)
        )
        overlay.open(search_card)
        
        page.update()


    # [HANDLERS] Chat navigation and mode control functions - Hoisted to fix UnboundLocalError
    async def back_to_list(e=None):
        """Navigate back to topic list from chat view"""
        tid = state.get("current_topic_id")

        async def _do_back():
            if tid:
                try:
                    # Only update last_read on exit if user was actually at the bottom
                    if state.get("is_near_bottom"):
                        await asyncio.to_thread(chat_service.update_last_read, tid, current_user_id)
                except Exception:
                    pass  # Last read update failed

            state["view_mode"] = "list"
            state["current_topic_id"] = None
            state["last_loaded_msg_id"] = None
            update_layer_view()
            # Refresh topics to clear unread counts immediately
            await asyncio.sleep(0.1)  # Brief delay for DB propagation
            load_topics(True)

        asyncio.create_task(_do_back())

    def update_layer_view():
        """Update the main view layer based on current view mode"""
        # [FIX] Update chat_main_layout instead of root_view to preserve Stack layers (like image viewer)
        chat_main_layout.controls = [list_page] if state["view_mode"] == "list" else [chat_page]
        try:
            if chat_main_layout.page:
                chat_main_layout.update()
        except: pass

    async def toggle_selection_mode(active):
        """Toggle AI summary selection mode on/off"""
        print(f"DEBUG_CHAT: Toggling Selection Mode to {active}")
        state.set("selection_mode", active)
        
        # [NEW] If turning OFF selection mode, also cancel any active AI analysis
        if not active:
            state.set("ai_cancel_requested", True)
            
        print(f"DEBUG_CHAT: State after set: {state.get('selection_mode')}")
        state.clear_selected()
        
        # Update UI visibility
        selection_action_bar.visible = active
        input_row_container.visible = not active
        page.update()
        
        # [CRITICAL FIX] Reload messages on BOTH enter and exit to update checkboxes
        # This prevents cascading re-renders when exiting
        print(f"DEBUG_CHAT: Reloading messages for selection_mode={state.get('selection_mode')}")
        await load_messages_async()


    list_page_content = ft.Container(
        expand=True, bgcolor="white",
        content=ft.Column([
            AppHeader(
                title_text="메신저",
                on_back_click=lambda _: asyncio.create_task(navigate_to("home")),
                action_button=ft.Row([
                    ft.IconButton(ft.Icons.SEARCH, icon_color=AppColors.TEXT_SECONDARY, tooltip="전체 검색", on_click=lambda e: asyncio.create_task(open_search_dialog(e))),
                    ft.PopupMenuButton(
                        icon=ft.Icons.ADD,
                        icon_color=AppColors.PRIMARY,
                        tooltip="메뉴",
                        items=[
                            ft.PopupMenuItem(
                                content=ft.Text("새 스레드 생성"),
                                icon=ft.Icons.ADD_COMMENT_OUTLINED,
                                on_click=lambda e: asyncio.create_task(show_create_modal(e))
                            ),
                            ft.PopupMenuItem(
                                content=ft.Text("카테고리 관리"),
                                icon=ft.Icons.CATEGORY_OUTLINED,
                                on_click=lambda e: asyncio.create_task(open_manage_categories_dialog(e))
                            ),
                        ]
                    ),
                    ft.OutlinedButton(
                        ref=edit_btn_ref,
                        content=ft.Text("편집"),
                        style=ft.ButtonStyle(color=AppColors.TEXT_SECONDARY, shape=ft.RoundedRectangleBorder(radius=30), side=ft.BorderSide(1, AppColors.BORDER_LIGHT), padding=ft.padding.symmetric(horizontal=12, vertical=0)),
                        on_click=lambda e: asyncio.create_task(toggle_edit_mode(e))
                    )
                ], spacing=0)
            ),
            ft.Container(
                content=topic_list_container, 
                expand=True, 
                padding=0, 
                bgcolor="white" # Ensure background is white
            )
            # debug_panel (Hidden for production)
        ], spacing=0)
    )
    
    list_page = ft.Stack([
        list_page_content
        # modal_container removed (replaced by overlay)
    ], expand=True)

    # [AI Calendar Feature]
    async def open_ai_calendar_dialog(e):
        from views.styles import AppColors
        from utils.logger import log_error, log_info
        from services import ai_service, calendar_service
        from datetime import datetime, timedelta, time
        
        # [GUARD] Double click prevention
        if state.get("is_ai_processing") or not state.get("current_topic_id"):
             return
        state.set("is_ai_processing", True)
        state.set("ai_cancel_requested", False)
        
        loading_modal_container = None
        editor_modal_container = None

        try:
            # 1. Loading UI - Container-wrapped Stack (EXACT pattern from working create topic modal)
            loading_modal_container = ft.Container(
                visible=False,
                expand=True,
                content=ft.Stack([
                    # Semi-transparent background
                    ft.Container(expand=True, bgcolor="rgba(0,0,0,0.5)"),
                    # Loading content centered
                    ft.Container(
                        alignment=ft.Alignment(0, 0),
                        content=ft.Container(
                            width=min(300, (page.window_width or 300) * 0.94),
                            bgcolor="white",
                            border_radius=15,
                            padding=30,
                            content=ft.Column([
                                ft.Row([ft.ProgressRing(), ft.Text("AI 분석 중...", size=16)], alignment=ft.MainAxisAlignment.CENTER, spacing=20, wrap=True),
                                ft.Container(height=20),
                                ft.OutlinedButton(
                                    "취소",
                                    on_click=lambda e: (
                                        print("DEBUG_AI: Analysis Cancelled by user (modal)"),
                                        state.set("ai_cancel_requested", True),
                                        state.set("is_ai_processing", False),
                                        setattr(loading_modal_container, 'visible', False),
                                        page.update(),
                                        asyncio.create_task(toggle_selection_mode(False))
                                    ),
                                    # [FIX] Removed expand=True to prevent vertical stretching in tight column
                                    width=240 # Optional: fixed width instead
                                )
                            ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                        )
                    )
                ])
            )
            
            # Add to overlay ONCE, then toggle visibility
            page.overlay.append(loading_modal_container)
            loading_modal_container.visible = True
            page.update()

            # 2. Extract messages
            selected_ids = state.get_selected_copy()
            if state.get("selection_mode") and selected_ids:
                full_msgs = await asyncio.to_thread(chat_service.get_messages, state.get("current_topic_id"), 100)
                msgs = [m for m in full_msgs if str(m['id']) in selected_ids]
            else:
                msgs = await asyncio.to_thread(chat_service.get_messages, state.get("current_topic_id"), 50)

            # 3. Analyze
            result = await asyncio.to_thread(ai_service.analyze_chat_for_calendar, msgs)
            
            # [STRICT CANCEL CHECK] After AI operation - use state flag
            if state.get("ai_cancel_requested"):
                print("DEBUG_AI: Detected cancellation state, stopping flow.")
                state.set("is_ai_processing", False)
                # Modal already hidden by cancel button
                return 

            # 4. Prepare defaults
            summary = result.get("summary", "")
            description = result.get("description", "")
            d_str = result.get("date")
            t_str = result.get("time")

            default_date = datetime.now()
            if d_str:
                try: default_date = datetime.strptime(d_str, "%Y-%m-%d")
                except: pass
            default_time = time(9, 0)
            if t_str:
                try:
                    h, m = map(int, t_str.split(':'))
                    default_time = time(h, m)
                except: pass

            # 5. Build Editor
            loading_modal_container.visible = False
            page.update()
            
            tf_summary = ft.TextField(label="제목", value=summary, autofocus=True, filled=True, border_radius=8)
            tf_description = ft.TextField(label="상세 요약", value=description, multiline=True, min_lines=2, max_lines=4, filled=True, border_radius=8)
            tf_start_date = ft.TextField(label="시작 날짜", value=default_date.strftime("%Y-%m-%d"), read_only=True, expand=True, filled=True)
            tf_end_date = ft.TextField(label="마감 날짜", value=default_date.strftime("%Y-%m-%d"), read_only=True, expand=True, filled=True)
            tf_time = ft.TextField(label="시간", value=default_time.strftime("%H:%M"), read_only=True, expand=True, filled=True)

            dp_start = ft.DatePicker(on_change=lambda e: (setattr(tf_start_date, "value", e.control.value.strftime("%Y-%m-%d")), page.update()) if e.control.value else None)
            dp_end = ft.DatePicker(on_change=lambda e: (setattr(tf_end_date, "value", e.control.value.strftime("%Y-%m-%d")), page.update()) if e.control.value else None)
            tp = ft.TimePicker(on_change=lambda e: (setattr(tf_time, "value", e.control.value.strftime("%H:%M")), page.update()) if e.control.value else None)
            
            # Cleanup overlay from previous AI instances (In-place modification)
            to_remove = [c for c in page.overlay if isinstance(c, (ft.DatePicker, ft.TimePicker, ft.AlertDialog))]
            for c in to_remove:
                page.overlay.remove(c)
            
            page.overlay.extend([dp_start, dp_end, tp])

            # Close loading modal
            loading_modal_container.visible = False
            page.update()

            async def handle_register(e):
                if not tf_summary.value:
                    tf_summary.error_text = "제목을 입력하세요."; tf_summary.update(); return
                
                try:
                    from datetime import datetime as dt_class
                    d_start = dt_class.strptime(tf_start_date.value, "%Y-%m-%d")
                    d_end = dt_class.strptime(tf_end_date.value, "%Y-%m-%d")
                    t_val = dt_class.strptime(tf_time.value, "%H:%M").time()
                    dt_start_full = dt_class.combine(d_start.date(), t_val)
                    dt_end_full = dt_class.combine(d_end.date(), t_val) + timedelta(hours=1)

                    payload = {
                        "title": tf_summary.value,
                        "start_date": dt_start_full.strftime("%Y-%m-%d %H:%M:%S"),
                        "end_date": dt_end_full.strftime("%Y-%m-%d %H:%M:%S"),
                        "is_all_day": False, "color": "#448AFF",
                        "user_id": page.app_session.get("user_id"),
                        "channel_id": page.app_session.get("channel_id"),
                        "description": tf_description.value or "AI Generated"
                    }
                    
                    # [FIX] Call module function directly
                    await calendar_service.create_event(payload)
                    page.open(ft.SnackBar(ft.Text("일정 등록 완료!"), bgcolor="green"))
                    state.set("is_ai_processing", False)
                    editor_modal_container.visible = False
                    asyncio.create_task(toggle_selection_mode(False))
                    page.update()
                except Exception as ex:
                    state.set("is_ai_processing", False)
                    log_error(f"Save Event Failed: {ex}")
                    page.open(ft.SnackBar(ft.Text(f"등록 실패: {ex}"), bgcolor="red")); page.update()

            def handle_cancel_editor(e):
                print("DEBUG_AI: handle_cancel_editor FIRED!")
                state.set("is_ai_processing", False)
                editor_modal_container.visible = False
                asyncio.create_task(toggle_selection_mode(False))
                page.update()

            # Custom Container-wrapped Stack modal for editor (EXACT pattern from working create topic modal)
            editor_modal_container = ft.Container(
                visible=False,
                expand=True,
                content=ft.Stack([
                    # Semi-transparent background
                    ft.Container(expand=True, bgcolor="rgba(0,0,0,0.5)"),
                    # Editor content centered
                    ft.Container(
                        alignment=ft.Alignment(0, 0),
                        content=ft.Container(
                            width=min(450, (page.window_width or 450) * 0.94),
                            bgcolor="white",
                            border_radius=15,
                            padding=30,
                            content=ft.Column([
                                ft.Row([
                                    ft.Text("일정 확인", size=20, weight="bold", color="#212121"),
                                    ft.IconButton(icon=ft.Icons.CLOSE, icon_color="#757575", on_click=handle_cancel_editor)
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Divider(),
                                tf_summary, tf_description,
                                ft.Row([ft.IconButton(ft.Icons.CALENDAR_MONTH, on_click=lambda _: page.open(dp_start)), tf_start_date], wrap=True),
                                ft.Row([ft.IconButton(ft.Icons.EVENT_REPEAT, on_click=lambda _: page.open(dp_end)), tf_end_date], wrap=True),
                                ft.Row([ft.IconButton(ft.Icons.ACCESS_TIME, on_click=lambda _: page.open(tp)), tf_time], wrap=True),
                                ft.Container(height=10),
                                ft.Row([
                                    ft.OutlinedButton("취소", on_click=handle_cancel_editor, expand=1),
                                    ft.ElevatedButton("등록", on_click=handle_register, bgcolor=AppColors.PRIMARY, color="white", expand=1)
                                ], spacing=10)
                            ], tight=True, spacing=10, scroll=ft.ScrollMode.AUTO, max_height=page.window_height * 0.8)
                        )
                    )
                ])
            )
            
            # Add to overlay ONCE, then toggle visibility
            page.overlay.append(editor_modal_container)
            editor_modal_container.visible = True
            page.update()

        except Exception as outer_ex:
            state.set("is_ai_processing", False)
            if loading_modal_container and loading_modal_container in page.overlay:
                loading_modal_container.visible = False
            log_error(f"AI Analysis Error: {outer_ex}")
            page.open(ft.SnackBar(ft.Text(f"AI 분석 오류: {outer_ex}"), bgcolor="red")); page.update()



    chat_page_header = AppHeader(
        title_text=ft.Text("대화", ref=chat_title_ref, style=AppTextStyles.HEADER_TITLE, color=AppColors.TEXT_PRIMARY),
        on_back_click=back_to_list,
        action_button=ft.Row([
            ft.IconButton(ft.Icons.SEARCH, icon_color=AppColors.TEXT_SECONDARY, tooltip="검색", on_click=lambda e: asyncio.create_task(open_search_dialog(e))),
            # [NEW] AI Summary Button (Multi-select)
            ft.IconButton(ft.Icons.AUTO_AWESOME_OUTLINED, icon_color="#5C6BC0", tooltip="AI 요약", on_click=lambda _: asyncio.create_task(toggle_selection_mode(True))),
            # [NEW] Member Management
            ft.IconButton(ft.Icons.PEOPLE_OUTLINE, icon_color=AppColors.TEXT_SECONDARY, tooltip="멤버 관리", on_click=lambda e: asyncio.create_task(open_topic_member_management_dialog(e))),
             ft.PopupMenuButton(
                icon=ft.Icons.MORE_VERT,
                icon_color=AppColors.TEXT_SECONDARY,
                items=[
                    ft.PopupMenuItem(
                        content=ft.Text("새로 고침"),
                        icon=ft.Icons.REFRESH,
                        on_click=lambda e: asyncio.create_task(load_messages(e))
                    )
                ]
            )
        ])
    )

    # [Active Selection Bar]
    selection_action_bar = ft.Container(
        content=ft.Row([
            ft.TextButton("취소", on_click=lambda _: asyncio.create_task(toggle_selection_mode(False)), icon=ft.Icons.CLOSE, icon_color="white", style=ft.ButtonStyle(color="white")),
            ft.Container(expand=True), # Spacer
            ft.ElevatedButton("AI 요약 실행", icon=ft.Icons.AUTO_AWESOME, on_click=open_ai_calendar_dialog, bgcolor="white", color="#1976D2")
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
        bgcolor="#1976D2", # Blue bar
        visible=False
    )


    def try_pick_files(e):
        # FilePicker disabled in Flet 0.80 due to compatibility issues
        page.open(ft.SnackBar(ft.Text("파일 업로드 기능은 현재 버전에서 지원되지 않습니다."), bgcolor="orange"))
        page.update()

    chat_input_row = ft.Row([
        ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED, icon_color="#757575", on_click=try_pick_files),
        msg_input,
        ft.IconButton(ft.Icons.SEND_ROUNDED, icon_color="#2E7D32", icon_size=32, on_click=lambda _: asyncio.create_task(send_message())),
    ], spacing=10)

    input_row_container = ft.Container(
        content=ft.Column([
            pending_container,
            chat_input_row
        ]),
        visible=True
    )

    chat_page = ft.Container(
        expand=True, bgcolor="white",
        content=ft.Column([
            chat_page_header,
            ft.Container(
                content=ft.Stack([
                    message_list_view,
                    floating_new_msg_container
                ]), 
                expand=True, 
                bgcolor="#F5F5F5"
            ),
            ft.Container(
                content=ft.Stack([
                    input_row_container,
                    selection_action_bar
                ])
            )
        ])
    )

    # Removed local import to fix scope UnboundLocalError

    # ...
    
    # Style applied by AppHeader
    msg_input.bgcolor = AppColors.SURFACE_VARIANT
    msg_input.color = AppColors.TEXT_PRIMARY
    msg_input.border_color = AppColors.BORDER
    msg_input.border_width = 1

    # [FIX] Robust Realtime Task
    async def realtime_handler():
        file_log_info("REALTIME HANDLER STARTED")
        
        # 1. Start Polling Task (Reliable fallback)
        async def polling_loop():
            file_log_info("POLLING LOOP STARTED")
            # Wait a few seconds for UI to settle before even considering auto-cleanup
            await asyncio.sleep(5)
            count = 0
            # [FIX] termination condition: is_active AND exact route match
            while state["is_active"] and page.route == "chat":
                # [FIX] Safer page check - only stop if page is explicitly gone AND it was previously there
                if hasattr(page, "is_running") and not page.is_running:
                    state["is_active"] = False
                    break
                
                try:
                    curr_tid = state.get("current_topic_id")
                    last_id = state.get("last_loaded_msg_id")
                    view_mode = state.get("view_mode")
                    
                    # A. Current Room Check
                    if curr_tid:
                        if not state.get("is_loading_messages"):
                            if chat_service.check_new_messages(curr_tid, last_id):
                                 file_log_info(f"POLLING: New message detected for {curr_tid}! Reloading.")
                                 load_messages()
                    
                    # B. Background Topic Refresh (Real-time Badges)
                    # [Iteration 10] Optimize refresh based on view mode
                    # If in list: Refresh every loop (~3.3s)
                    # If in chat: Refresh every 6 loops (~20s) - background sync
                    should_refresh_topics = False
                    if view_mode == "list":
                        should_refresh_topics = True
                    elif count % 6 == 0:
                        should_refresh_topics = True
                        
                    if should_refresh_topics:
                        do_ui = (view_mode == "list")
                        # file_log_info(f"POLLING: Triggering topic refresh. UI={do_ui}")
                        asyncio.create_task(load_topics_async(update_ui=do_ui, show_all=False))
                    
                    count += 1
                except Exception as poll_ex:
                    file_log_info(f"POLLING ERROR: {repr(poll_ex)}")
                
                # Increased interval to 15s to reduce lag, as we have Realtime connection
                await asyncio.sleep(15.0)
        
        # 2. Start Realtime Connection
        async def connection_loop():
            file_log_info("CONNECTION LOOP STARTED")
            while state["is_active"]:
                try:
                    rt = supabase.get_realtime_client()
                    if not rt:
                        await asyncio.sleep(60)
                        continue
                    
                    await rt.connect()
                    
                    # [FIX] Spec change in realtime-py 2.x: use .on_postgres_changes
                    channel = rt.channel("chat-sync")
                    
                    async def on_new_msg(payload):
                        file_log_info("REALTIME: New Message Detected!")
                        load_messages()

                    channel.on_postgres_changes(
                        event="INSERT",
                        schema="public",
                        table="chat_messages",
                        callback=on_new_msg
                    )
                    
                    await channel.subscribe()
                    file_log_info("REALTIME: Subscribed to chat_messages")
                    
                    # Keep alive while active
                    while state["is_active"] and page.route == "chat":
                        await asyncio.sleep(10)
                        
                except Exception as rt_ex:
                    file_log_info(f"REALTIME ERROR: {rt_ex}")
                    await asyncio.sleep(30) # Prevent tight loop on error
                finally:
                    try:
                        await rt.disconnect()
                    except Exception:
                        pass  # Realtime disconnect failed

        # Run both
        await asyncio.gather(polling_loop(), connection_loop())

    def init_chat():
        update_layer_view()
        load_topics(True)
        asyncio.create_task(realtime_handler())

    init_chat()
    
    return [
        ft.Stack([
            ft.SafeArea(root_view, expand=True),
            overlay
        ], expand=True)
    ]
