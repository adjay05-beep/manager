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
            "selected_ids": set()
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


def get_chat_controls(page: ft.Page, navigate_to):
    file_log_info("Entering Chat View (get_chat_controls)")
    # [FIX] Stability: Use Global FilePicker and Robust Lifecycle Management
    from views.components.chat_bubble import ChatBubble

    # [SECURITY] Thread-safe state management
    state = ThreadSafeState()
    # [RBAC] Get User from Session
    current_user_id = page.session.get("user_id")
    
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
    message_list_view = ft.ListView(expand=True, spacing=5, padding=10, auto_scroll=True)
    # chat_header_title removed (Refactored to AppHeader)

    # ... inside load topics ...
    # chat_header_title.controls[1].value = f"Topics: {len(topics)}"
    msg_input = ft.TextField(hint_text="메시지를 입력하세요...", expand=True, multiline=True, max_lines=3)
    
    # [NEW] Image Viewer Overlay
    image_viewer = ft.Stack(visible=False, expand=True)

    def close_image_viewer(e):
        image_viewer.visible = False
        image_viewer.controls.clear()
        page.update()

    def show_image_viewer(src):
        image_viewer.controls = [
            ft.Container(
                expand=True,
                bgcolor="black",
                content=ft.Stack([
                    ft.Container(
                        content=ft.Image(src=src, fit=ft.ImageFit.CONTAIN),
                        alignment=ft.alignment.center,
                        on_click=close_image_viewer, # Click background to close
                        expand=True
                    ),
                    ft.Container(
                        content=ft.IconButton(ft.Icons.CLOSE, icon_color="white", icon_size=30, on_click=close_image_viewer),
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

    async def load_topics_thread(update_ui=True, show_all=False):
        # [DEBUG] Start
        try:
            pass
            # chat_header_title.controls[1].value = "Debug: Starting..."
            # [FIX] Remove instant update to prevent race with Main Thread init
        except: pass

        if not state["is_active"]: return
        if not current_user_id:
            # chat_header_title.controls[1].value = "Error: No Session"
            page.update()
            log_info("Chat ERROR: No user session found - cannot load topics")
            page.snack_bar = ft.SnackBar(ft.Text("세션이 만료되었습니다."), bgcolor="red", open=True); page.update()
            return
            
        try:
            # chat_header_title.controls[1].value = "Debug: Checking DB..."
            if update_ui: page.update()
            
            log_info(f"Loading topics (Mode: {'ALL' if show_all else 'Members Only'}) for {current_user_id}")
            
            # [DIAGNOSTIC] Log database connection status
            log_info(f"Database URL: {service_supabase.url[:30]}...")
            
            # [FIX] Multi-Channel Support
            current_channel_id = page.session.get("channel_id")
            if not current_channel_id:
                log_info("Chat ERROR: No channel_id in session")
                page.snack_bar = ft.SnackBar(ft.Text("매장 정보가 없습니다. 다시 로그인해 주세요."), bgcolor="red", open=True)
                page.update()
                return

            log_info(f"Loading topics for user {current_user_id} in channel {current_channel_id}")
            
            # [FIX] Async wrappers for Blocking Service Calls
            # chat_header_title.controls[1].value = "Debug: Fetching Cats..."
            if update_ui: page.update()
            
            categories_data = await asyncio.to_thread(chat_service.get_categories, current_channel_id)
            log_info(f"Categories loaded: {len(categories_data) if categories_data else 0}")
            categories = [c['name'] for c in categories_data] if categories_data else ["공지", "일반", "중요", "개별 업무"]

            if show_all:
                # chat_header_title.controls[1].value = "Debug: Fetching All Topics..."
                if update_ui: page.update()
                topics = await asyncio.to_thread(chat_service.get_all_topics, current_channel_id)
            else:
                # chat_header_title.controls[1].value = "Debug: Fetching User Topics..."
                if update_ui: page.update()
                topics = await asyncio.to_thread(chat_service.get_topics, current_user_id, current_channel_id)
                
            log_info(f"Topics fetched: {len(topics)} topics for user {current_user_id}")
            if len(topics) == 0:
                log_info("WARNING: No topics returned from database - user may need to create one or check membership")
            sorted_topics = sorted(topics, key=lambda x: (x.get('display_order', 0) or 0, x.get('created_at', '')), reverse=True)
            
            # [FIX] Efficient Unread Count Fetching
            unread_counts = await asyncio.to_thread(chat_service.get_unread_counts, current_user_id, topics)
            log_info(f"Unread Counts calculated for {len(topics)} topics")

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
                                                 on_click=lambda e, cid=cat_id, cn=cat_name: open_rename_cat_dialog(cid, cn))
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
                    # Render Items
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
                                ft.Text("우측 상단 + 버튼을 눌러 만들어보세요", size=14, color="#BDBDBD"),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                            alignment=ft.alignment.center,
                            padding=40
                        )
                    )
                
                list_view = ft.ListView(expand=True, spacing=0, padding=0, controls=list_view_ctrls)
                new_controls = [list_view]
            
            topic_list_container.controls = new_controls
            
            # [DEBUG] Show detailed count
            ctrl_count = len(list_view_ctrls) if 'list_view_ctrls' in locals() else "N/A"
            # chat_header_title.controls[1].value = f"Debug: {len(topics)} topics, {ctrl_count} items. Mode: {state.get('view_mode')}"
            if update_ui: page.update()
        except Exception as ex:
            log_info(f"Load Topics Critical Error: {ex}")
            # chat_header_title.controls[1].value = f"Error: {str(ex)[:20]}"
            if update_ui: page.update()
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
            if not list_ctrl: return
            controls = list_ctrl.controls
            moved_item = controls.pop(e.old_index)
            controls.insert(e.new_index, moved_item)
            
            # Fire and forget update
            def _update_order():
                # Loop top-down to determine category context and order
                current_cat = None # Default
                # Find the first category header if exists
                
                # Check the first item, if it's a topic, what category is it?
                # We need to scan/state-machine it.
                # Actually, simply iterating and updating 'current_cat' when we hit a header is perfect.
                # But what if the first item is a topic and we haven't hit a header yet?
                # It belongs to the category of the header ABOVE it.
                # If there is no header above it (e.g. at very top), it gets 'None' (Uncategorized/General) or we should infer?
                # In our UI, "General" header is usually first. 
                # So if we hit that, current_cat = "일반".
                
                current_cat_name = "일반" # Default fallback
                
                # We need to process updates in a batch or loop
                db_updates = []
                
                # Calculate display_order (Reverse of index, usually)
                # But wait, if I have [Header A, Topic 1, Topic 2, Header B]
                # Topic 1 order > Topic 2 order? Or just use index?
                # Usually 0 is top. If we want Descending sort for display:
                # Top item has LOWEST index, HIGHEST score.
                
                max_score = len(controls) * 10
                
                for i, ctrl in enumerate(controls):
                    data = ctrl.data
                    if not data: continue
                    
                    dtype = data.get("type")
                    if dtype == "category":
                        current_cat_name = data.get("name")
                    elif dtype == "topic":
                        tid = data.get("id")
                        # Update Category AND Order
                        # We use 'score' = max_score - i
                        score = max_score - i
                        
                        # Perform update (Sync or threaded?)
                        # We are in a thread.
                        # We need to get current topic data to see if category changed to avoid redundant DB call?
                        # Or just update blindly. Blind update is safer for consistency.
                        
                        # However, 'update_topic' updates name too. We don't want to wipe name.
                        # We should use a specific function for 'move_topic' or update specific cols.
                        # chat_service.update_topic_order just updates order.
                        # We need update_topic_metadata(id, category, order).
                        
                        # Creating ad-hoc update in chat_service or using raw query here?
                        # Better to add a method in chat_service or use existing ones combined.
                        # chat_service.update_topic calls with (id, name, category). Requires Name.
                        # We don't have the Name handy in the 'data' (we might, but risky).
                        # Let's add 'name' to topic data too for safety.
                        
                        t_name = data.get("topic_name")
                        # Update
                        chat_service.update_topic(tid, t_name, current_cat_name)
                        chat_service.update_topic_order(tid, score, current_user_id)

                load_topics(True)
                
            threading.Thread(target=_update_order, daemon=True).start()
        except Exception as ex:
            log_info(f"Reorder Error: {ex}")

    def toggle_priority(tid, current_val):
        def _do_toggle():
            try:
                chat_service.toggle_topic_priority(tid, current_val, current_user_id)
                load_topics(True)
            except PermissionError as perm_err:
                page.snack_bar = ft.SnackBar(ft.Text(str(perm_err)), bgcolor="red", open=True)
                page.update()
            except Exception as ex:
                log_info(f"Toggle priority error: {ex}")
        threading.Thread(target=_do_toggle, daemon=True).start()

    def open_manage_categories_dialog(e):
        cat_list = ft.Column(spacing=5)
        new_cat_input = ft.TextField(hint_text="새 주제 이름", expand=True)
        
        def refresh_cats():
            def _refresh():
                cid = page.session.get("channel_id")
                cats = chat_service.get_categories(cid)
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
                cid = page.session.get("channel_id")
                threading.Thread(target=lambda: (
                    chat_service.create_category(new_cat_input.value, cid),
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

    # [FIX] Render ID to prevent race conditions in fast reloads
    render_context = {"last_id": 0}

    def load_messages_thread():
        if not state["current_topic_id"] or not state["is_active"]: return
        
        # Increment Render ID
        render_context["last_id"] += 1
        my_id = render_context["last_id"]
        
        sel_mode = bool(state.get("selection_mode"))
        render_user_id = page.session.get("user_id")
        print(f"DEBUG_CHAT: [Thread {my_id}] RenderStart. User={render_user_id}, Topic={state['current_topic_id']}", flush=True)

        try:
            # 1. Fetch DB Messages
            db_messages = chat_service.get_messages(state["current_topic_id"])
            
            # 2. Extract Existing Pending Messages
            pending_bubbles = []
            if message_list_view.controls and isinstance(message_list_view.controls, list):
                for ctrl in message_list_view.controls:
                    if isinstance(ctrl, ChatBubble) and getattr(ctrl, "is_sending", False):
                        p_content = ctrl.message.get("content")
                        is_landed = False
                        for db_m in reversed(db_messages[-10:]): 
                            if db_m.get("content") == p_content and db_m.get("user_id") == current_user_id:
                                is_landed = True
                                break
                        if not is_landed:
                            pending_bubbles.append(ctrl)
            
            # 3. Build New Control List
            new_controls = []
            def on_msg_select(mid, val):
                if val: state.add_selected(mid)
                else: state.remove_selected(mid)

            for m in db_messages:
                new_controls.append(ChatBubble(
                    m,
                    render_user_id,
                    selection_mode=sel_mode,
                    on_select=on_msg_select,
                    on_image_click=show_image_viewer
                ))
            
            # 4. Append Pending Messages at the End
            for p_ctrl in pending_bubbles:
                p_ctrl.selection_mode = sel_mode
                p_ctrl.build_ui()
                new_controls.append(p_ctrl)
            
            # 5. Atomic Update UI (Only if we are the LATEST thread)
            if my_id == render_context["last_id"]:
                message_list_view.controls = new_controls
                print(f"DEBUG_CHAT: [Thread {my_id}] UI Updated with {len(new_controls)} controls. SelectionMode pushed: {sel_mode}")
                
                # [Smart Scroll]
                if new_controls:
                    try:
                        message_list_view.scroll_to(offset=-1, duration=200)
                    except: pass
                
                page.update()
            else:
                print(f"DEBUG_CHAT: [Thread {my_id}] Ignored (Stale). Latest is {render_context['last_id']}")

        except Exception as ex:
            print(f"DEBUG_CHAT: [Thread {my_id}] Error: {ex}")
            log_info(f"Load Messages Error: {ex}")

    def select_topic(topic):
        state["current_topic_id"] = topic['id']
        if 'chat_page_header' in locals():
            chat_page_header.content.controls[1].value = topic['name']
        else:
             # Fallback if variable scope issue (though likely fine due to closure)
             # But wait, chat_page_header is defined later?
             # Python Update: In nested functions, if variable is assigned later in the outer scope, it is accessible.
             # However, we must ensure it is initialized.
             # Actually, since select_topic is called via User Action, chat_page_header will be defined by then.
             chat_page_header.content.controls[1].value = topic['name']
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
        def _do_send():
            try:
                chat_service.send_message(state["current_topic_id"], final_content, final_image_url, current_user_id)
                # Realtime will likely trigger update, but we call load just in case
                # The load_messages_thread will merge/remove the temp message once DB has it
                load_messages_thread()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"전송 실패: {ex}"), bgcolor="red", open=True); page.update()
        
        threading.Thread(target=_do_send, daemon=True).start()

    pending_container = ft.Container(visible=False, padding=10, bgcolor="#3D4446", border_radius=10)
    
    # [FIX] Local FilePicker Logic
    def on_chat_file_result(e: ft.FilePickerResultEvent):
        if not e.files: return
        f = e.files[0]
        from utils.logger import log_info
        log_info(f"File Selected: {f.name}, Size: {f.size} bytes")
        # Immediate Feedback
        page.open(ft.SnackBar(ft.Text("파일 확인 중..."), open=True))
        page.update()

        if not state["current_topic_id"]:
            page.open(ft.SnackBar(ft.Text("대화방을 먼저 선택해주세요."), bgcolor="red", open=True))
            page.update()
            return
            
        f = e.files[0]
        is_web_mode = page.web # Capture safely

        # [FIX] Main Thread Execution for Upload Trigger
        # Previously inside a thread, which caused reliable upload issues.
        def update_snack(msg):
            try:
                page.open(ft.SnackBar(ft.Text(msg, size=12), open=True))
                page.update()
            except: pass

        def show_error_ui(msg, color="red"):
             try:
                 pending_container.content = ft.Container(
                     ft.Text(msg, color="white", size=11),
                     bgcolor=color, padding=5, border_radius=5
                 )
                 pending_container.update()
                 time.sleep(5)
                 pending_container.visible = False
                 page.update()
             except: pass

        try:
            update_snack(f"1/4. '{f.name}' 준비 중...")
            
            # [DEBUG] Immediate Upload (Main Thread)
            from utils.logger import log_info
            log_info(f"DEBUG: Calling handle_file_upload in Main Thread. Web={is_web_mode}")
            
            # [FIX] Use e.control to target the EXACT picker that triggered this event
            # addressing potential ID mismatch or instance staleness
            active_picker = e.control
            
            # Synchronous Call triggers Browser Command immediately
            result = storage_service.handle_file_upload(is_web_mode, f, update_snack, picker_ref=active_picker)
            
            if result and "public_url" in result:
                 state["pending_image_url"] = result["public_url"]
            
            if result:
                 if result.get("type") == "proxy_upload_triggered":
                      s_name = result["storage_name"]
                      state["pending_storage_name"] = s_name
                      update_snack("2/4. 서버 전송 시작...")
                      
                      pending_container.content = ft.Row([
                            ft.Container(ft.ProgressRing(stroke_width=2, color="white"), width=40, height=40, alignment=ft.alignment.center, bgcolor="#424242", border_radius=5),
                            ft.Column([
                                ft.Text("서버 처리 중...", size=12, weight="bold", color="white"),
                                ft.Text("파일을 저장하고 있습니다.", size=10, color="white70"),
                            ], spacing=2, tight=True),
                         ], spacing=10)
                      pending_container.visible = True
                      page.update()

                      # [BACKGROUND WATCHER]
                      def watch_server_file_target(target_name):
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
                                    time.sleep(1.0)
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
                                        except: pass
                                    
                                    if found_new:
                                        # Stabilize
                                        try:
                                            size1 = os.path.getsize(target_path)
                                            time.sleep(1.0)
                                            if os.path.exists(target_path) and os.path.getsize(target_path) == size1:
                                                 log_info("File Stable. Finalizing.")
                                                 final_url = storage_service.upload_proxy_file_to_supabase(current_storage_name)
                                                 state["pending_image_url"] = final_url
                                                 update_pending_ui(final_url)
                                                 page.open(ft.SnackBar(ft.Text("🔒 보안 업로드 완료!"), bgcolor="green", open=True))
                                                 page.update()
                                                 return
                                        except Exception as fin_ex:
                                             log_info(f"Finalize Error: {fin_ex}")
                                             show_error_ui(f"업로드 실패: {fin_ex}")
                                             return
                                    
                                    # Feedback (Simplified)
                                    if i % 3 == 0:
                                        try:
                                            # Optional: Update text if container is valid
                                            pass 
                                        except: pass

                                log_info("Watcher Timeout")
                                show_error_ui("시간 초과: 파일을 찾을 수 없습니다.")
                            
                            except Exception as ex:
                                log_info(f"Watcher Crash: {ex}")
                                show_error_ui(f"시스템 오류: {ex}")

                      threading.Thread(target=watch_server_file_target, args=(s_name,), daemon=True).start()

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
            update_snack(f"처리 중 오류: {logic_ex}")

    def on_chat_upload_progress(e: ft.FilePickerUploadEvent):
        from utils.logger import log_info
        log_info(f"Upload Progress: {e.progress:.2f}, Error: {e.error}")
        
        if e.error:
            log_info(f"CRITICAL: Upload Event Error: {e.error}")
            page.open(ft.SnackBar(ft.Text(f"업로드 실패: {e.error}"), bgcolor="red", open=True))
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
            except: pass

            if e.progress == 1.0:
                s_name = state.get("pending_storage_name")
                if s_name:
                    # [PROXY FINALIZATION]
                    state["pending_storage_name"] = None # Reset
                    
                    def finalize_step():
                        try:
                             final_url = storage_service.upload_proxy_file_to_supabase(s_name)
                             state["pending_image_url"] = final_url
                             
                             # Success UI
                             update_pending_ui(final_url)
                             page.open(ft.SnackBar(ft.Text("🔒 보안 업로드 완료!"), bgcolor="green", open=True))
                             page.update()
                        except Exception as fin_ex:
                             print(f"Proxy Finalize Error: {fin_ex}")
                             page.open(ft.SnackBar(ft.Text(f"처리 실패: {fin_ex}"), bgcolor="red", open=True))
                             page.update()
                             
                    threading.Thread(target=finalize_step, daemon=True).start()
                
                else:
                    update_pending_ui(state.get("pending_image_url"))
                    page.open(ft.SnackBar(ft.Text("이미지 로드 완료!"), bgcolor="green", open=True))
                    page.update()

    # [FIX] Use Global FilePicker (initialized in main.py)
    # This prevents "Unknown control" errors caused by local instantiation.
    local_file_picker = page.chat_file_picker
    # [CRITICAL FIX] Ensure it is in overlay even after page.clean()
    if local_file_picker not in page.overlay:
        page.overlay.append(local_file_picker)

    def update_pending_ui(public_url):
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
                alignment=ft.alignment.center
            ),
            ft.Column([
                ft.Text(status_text, size=12, weight="bold", color="white"),
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
    
    # Bind handlers to the local picker (global page.chat_file_picker is a backup)
    local_file_picker.on_result = on_chat_file_result
    local_file_picker.on_upload = on_chat_upload_progress

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
                    await load_topics_thread(True) # Call directly to ensure it runs
                    print("DEBUG: Topics reloaded")
                except PermissionError as perm_err:
                    print(f"DEBUG: Permission Error: {perm_err}")
                    page.snack_bar = ft.SnackBar(ft.Text(str(perm_err)), bgcolor="red", open=True)
                    page.update()
                except Exception as ex:
                    print(f"DEBUG: Critical Delete Error: {ex}")
                    log_info(f"Delete topic error: {ex}")
                    page.snack_bar = ft.SnackBar(ft.Text(f"삭제 실패: {ex}"), bgcolor="red", open=True)
                    page.update()
            
            page.run_task(_do_delete)
            page.close(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text("스레드 삭제"),
            content=ft.Text("이 스레드와 모든 메시지가 삭제됩니다.\n(삭제 후 복구할 수 없습니다)"),
            actions=[
                ft.TextButton("취소", on_click=lambda _: page.close(dlg)),
                ft.TextButton(content=ft.Text("삭제", color="red"), on_click=delete_it)
            ]
        )
        page.open(dlg)

    # Custom modal overlay (instead of AlertDialog/BottomSheet which don't work on mobile)
    modal_container = ft.Container()  # Will be defined below
    
    def show_create_modal(e):
        log_info("Showing custom modal overlay")
        modal_container.visible = True
        modal_name_field.value = ""
        page.update()
    
    def hide_create_modal(e):
        log_info("Hiding custom modal overlay")
        modal_container.visible = False
        page.update()
    
    modal_name_field = ft.TextField(label="새 스레드 이름", autofocus=True, width=300)
    
    def create_from_modal(e):
        # [CRITICAL DEBUG] Immediate feedback to verify click detection
        page.snack_bar = ft.SnackBar(
            ft.Text(f"🔍 버튼 클릭 감지됨! 값: '{modal_name_field.value}'", color="white"),
            bgcolor="purple",
            open=True,
            duration=5000
        )
        page.update()
        
        log_info(f"Create from modal clicked, name='{modal_name_field.value}'")
        if not modal_name_field.value:
            log_info("ERROR: Name field is empty!")
            page.snack_bar = ft.SnackBar(
                ft.Text("스레드 이름을 입력해주세요", color="white"),
                bgcolor="orange",
                open=True
            )
            page.update()
            return
        
        async def _do_create():
            try:
                log_info(f"Creating topic from modal: {modal_name_field.value}")
                cid = page.session.get("channel_id")
                result = chat_service.create_topic(modal_name_field.value, None, current_user_id, cid)  # None = no category
                log_info(f"Topic creation success: {modal_name_field.value}")
                
                # Hide modal and show success
                modal_container.visible = False
                modal_name_field.value = ""  # Clear input for next time
                page.snack_bar = ft.SnackBar(
                    ft.Text("스레드가 생성되었습니다!", color="white"),
                    bgcolor="green",
                    open=True
                )
                page.update()
                
                # [FIX] Reload topics immediately and await completion
                log_info("Reloading topics after creation...")
                try:
                    # Directly call the async version to ensure it completes
                    await load_topics_thread(update_ui=True, show_all=False)
                    log_info("Topic list refreshed successfully")
                except Exception as reload_ex:
                    log_info(f"Reload error: {reload_ex}")
            except Exception as ex:
                log_info(f"Creation ERROR: {ex}")
                import traceback
                traceback.print_exc()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"생성 실패: {ex}", color="white"),
                    bgcolor="red",
                    open=True
                )
                page.update()
        
        page.run_task(_do_create)

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

        def load_cats_for_dialog():
             cid = page.session.get("channel_id")
             cats = chat_service.get_categories(cid)
             opts = [ft.dropdown.Option(c['name']) for c in cats]
             # Add Option for "Uncategorized"
             opts.insert(0, ft.dropdown.Option(key="none_val", text="미분류")) # We'll handle "none_val" -> None
             cat_dropdown.options = opts
             cat_dropdown.value = current_cat if current_cat else "none_val"
             page.update()

        threading.Thread(target=load_cats_for_dialog, daemon=True).start()
        
        async def do_update(e):
            if name_input.value:
                try:
                    new_cat = cat_dropdown.value
                    if new_cat == "none_val": new_cat = None
                    
                    chat_service.update_topic(topic_id, name_input.value, new_cat)
                    page.close(dlg)
                    load_topics(True)
                except Exception as ex:
                    log_info(f"Update Topic Error: {ex}")
                    page.snack_bar = ft.SnackBar(ft.Text(f"수정 실패: {ex}"), bgcolor="red", open=True); page.update()
        
        dlg = ft.AlertDialog(
            title=ft.Text("스레드 이름 수정"),
            content=name_input,
            actions=[
                ft.TextButton("취소", on_click=lambda _: page.close(dlg)),
                ft.ElevatedButton("저장", on_click=do_update, bgcolor="#2E7D32", color="white")
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

    # [SEARCH] Global Search Logic
    search_results_col = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, height=300)
    search_input = ft.TextField(hint_text="검색어 입력...", autofocus=True, expand=True, on_submit=lambda e: do_search())
    
    def do_search():
        query = search_input.value
        if not query or len(query) < 2:
            page.snack_bar = ft.SnackBar(ft.Text("2글자 이상 입력해주세요."), bgcolor="red", open=True); page.update()
            return

        search_results_col.controls = [ft.Container(ft.ProgressRing(), alignment=ft.alignment.center, padding=20)]
        page.update()
        
        def _search_task():
            try:
                cid = page.session.get("channel_id")
                results = chat_service.search_messages_global(query, cid)
                
                items = []
                if not results:
                    items.append(ft.Container(ft.Text("검색 결과가 없습니다.", color="grey"), padding=20, alignment=ft.alignment.center))
                else:
                    for r in results:
                        # r keys: id, content, created_at, topic_id, profiles(full_name), chat_topics(name)
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
                                    page.close(search_dlg),
                                    select_topic(t)
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
        
        threading.Thread(target=_search_task, daemon=True).start()

    search_dlg = ft.AlertDialog(
        title=ft.Text("전체 대화 검색"),
        content=ft.Container(
            content=ft.Column([
                ft.Row([search_input, ft.IconButton(ft.Icons.SEARCH, on_click=lambda e: do_search())]),
                ft.Divider(),
                search_results_col
            ], tight=True,  width=400),
            height=400
        ),
        actions=[ft.TextButton("닫기", on_click=lambda e: page.close(search_dlg))]
    )
    
    def open_search_dialog(e):
        search_input.value = ""
        search_results_col.controls = [ft.Text("검색어를 입력하고 엔터를 누르세요.", color="grey", size=12)]
        page.open(search_dlg)

    list_page_content = ft.Container(
        expand=True, bgcolor="white",
        content=ft.Column([
            AppHeader(
                title_text="메신저",
                on_back_click=lambda _: navigate_to("home"),
                action_button=ft.Row([
                    ft.IconButton(ft.Icons.SEARCH, icon_color=AppColors.TEXT_SECONDARY, tooltip="전체 검색", on_click=open_search_dialog),
                    ft.PopupMenuButton(
                        icon=ft.Icons.ADD,
                        icon_color=AppColors.PRIMARY,
                        tooltip="메뉴",
                        items=[
                            ft.PopupMenuItem(
                                text="새 스레드 생성",
                                icon=ft.Icons.ADD_COMMENT_OUTLINED,
                                on_click=show_create_modal
                            ),
                            ft.PopupMenuItem(
                                text="카테고리 관리",
                                icon=ft.Icons.CATEGORY_OUTLINED,
                                on_click=open_manage_categories_dialog
                            ),
                        ]
                    ),
                    ft.OutlinedButton(
                        ref=edit_btn_ref, 
                        text="편집", 
                        style=ft.ButtonStyle(color=AppColors.TEXT_SECONDARY, shape=ft.RoundedRectangleBorder(radius=30), side=ft.BorderSide(1, AppColors.BORDER_LIGHT), padding=ft.padding.symmetric(horizontal=12, vertical=0)), 
                        on_click=lambda _: toggle_edit_mode()
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
    
    # Custom modal overlay (replaces AlertDialog/BottomSheet)
    modal_container = ft.Container(
        visible=False,
        expand=True,
        content=ft.Stack([
            # Background overlay - click to close
            ft.Container(
                expand=True,
                bgcolor="rgba(0,0,0,0.5)",
                on_click=hide_create_modal  # Only background closes modal
            ),
            # Modal content - positioned center
            ft.Container(
                alignment=ft.alignment.center,
                content=ft.Container(
                    width=350,
                    bgcolor="white",
                    border_radius=15,
                    padding=30,
                    content=ft.Column([
                        ft.Row([
                            ft.Text("새 스레드 만들기", size=20, weight="bold", color="#212121"),
                            ft.IconButton(icon=ft.Icons.CLOSE, icon_color="#757575", on_click=hide_create_modal)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        modal_name_field,
                        ft.Container(height=20),
                        ft.Row([
                            ft.OutlinedButton("취소", on_click=hide_create_modal, expand=1),
                            ft.ElevatedButton("만들기", on_click=create_from_modal, bgcolor="#2E7D32", color="white", expand=1)
                        ], spacing=10)
                    ], tight=True, spacing=15)
                )
            )
        ])
    )
    
    list_page = ft.Stack([
        list_page_content,
        modal_container
    ], expand=True)

    # [AI Calendar Feature]
    def open_ai_calendar_dialog(e):
        from views.styles import AppColors
        from utils.logger import log_error, log_info
        # [FIX] Local imports to resolve scope issues safely
        from services import ai_service, calendar_service
        from datetime import datetime, timedelta, time
        
        if not state.get("current_topic_id"): return
        
        # [NEW] Cancel Flag
        is_cancelled = [False]
        
        def on_cancel(e):
            is_cancelled[0] = True
            log_info("AI Analysis Cancelled by User")
            page.close(loading_dlg)
            
        # 1. Show Loading with Cancel
        loading_dlg = ft.AlertDialog(
            content=ft.Row([ft.ProgressRing(), ft.Text("AI가 대화를 분석 중입니다...")], alignment="center", spacing=20), 
            modal=True,
            actions=[ft.TextButton("취소", on_click=on_cancel)]
        )
        page.open(loading_dlg)
        page.update()
        
        # [NEW] Force Timeout Thread (Safeguard)
        import threading
        import time as tm
        def force_timeout_check():
            tm.sleep(45) # Increased to 45s due to potential cold start
            if not is_cancelled[0]: # If still running
                is_cancelled[0] = True
                try:
                    log_error("AI Analysis Timeout (Client-side 45s Limit)")
                    page.close(loading_dlg)
                    page.snack_bar = ft.SnackBar(ft.Text("AI 분석 시간이 초과되었습니다. (서버 응답 지연)"), bgcolor="red")
                    page.snack_bar.open = True
                    page.update()
                except: pass
        
        threading.Thread(target=force_timeout_check, daemon=True).start()
        
        def run_analysis():
            try:
                log_info(f"AI START: TopicID={state.get('current_topic_id')}, SelectionMode={state.get('selection_mode')}")

                # Get selected IDs safely (thread-safe copy)
                selected_ids = state.get_selected_copy()
                if state.get("selection_mode") and selected_ids:
                    full_msgs = chat_service.get_messages(state.get("current_topic_id"), limit=100)
                    msgs = [m for m in full_msgs if str(m['id']) in selected_ids]

                    if not msgs:
                        log_info("AI Aborted: No messages selected.")
                        page.snack_bar = ft.SnackBar(ft.Text("선택된 메시지가 범위 내에 없거나 로드되지 않았습니다."), bgcolor="orange"); page.snack_bar.open=True; page.update(); page.close(loading_dlg); return
                else:
                    msgs = chat_service.get_messages(state.get("current_topic_id"), limit=50)
                
                log_info(f"AI Processing {len(msgs)} messages...")

                # 3. Analyze
                result = {}
                try:
                    result = ai_service.analyze_chat_for_calendar(msgs)
                except Exception as api_err:
                     if is_cancelled[0]: return
                     log_error(f"AI Service Critical Failure: {api_err}")
                     print(f"AI API Error: {api_err}")
                     # [UX Fix] Continue even if AI fails, so user can enter manually
                     result = {
                         "summary": "분석 실패 (직접 입력해주세요)",
                         "date": datetime.now().strftime("%Y-%m-%d"),
                         "time": "09:00"
                     }
                     page.snack_bar = ft.SnackBar(ft.Text(f"AI 연결 실패: {str(api_err)[:30]}..."), bgcolor="orange")
                     page.snack_bar.open = True
                     page.update()
                
                if is_cancelled[0]: return
                
                # 4. Prepare Dialog Default Values
                summary = result.get("summary", "")
                description = result.get("description", "")
                d_str = result.get("date")
                t_str = result.get("time")
                
                log_info(f"AI Result: Summary='{summary}', Date='{d_str}'")

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
                    
                # 5. Show Editor Dialog
                def show_editor():
                    if is_cancelled[0]: return
                    try:
                        page.close(loading_dlg)
                    except: pass
                    
                    tf_summary = ft.TextField(label="제목", value=summary, autofocus=True, filled=True, border_radius=8, text_size=16)
                    tf_description = ft.TextField(label="상세 요약", value=description, multiline=True, min_lines=3, max_lines=5, filled=True, border_radius=8, text_size=14)
                    
                    default_end_date = default_date
                    tf_start_date = ft.TextField(label="시작 날짜", value=default_date.strftime("%Y-%m-%d"), read_only=True, expand=True, filled=True, border_radius=8, text_size=14)
                    tf_end_date = ft.TextField(label="마감 날짜", value=default_end_date.strftime("%Y-%m-%d"), read_only=True, expand=True, filled=True, border_radius=8, text_size=14)
                    tf_time = ft.TextField(label="시간", value=default_time.strftime("%H:%M"), read_only=True, expand=True, filled=True, border_radius=8, text_size=14)
                    
                    def on_start_date_change(e):
                        if e.control.value: tf_start_date.value = e.control.value.strftime("%Y-%m-%d"); page.update()
                    dp_start = ft.DatePicker(on_change=on_start_date_change, value=default_date)

                    def on_end_date_change(e):
                        if e.control.value: tf_end_date.value = e.control.value.strftime("%Y-%m-%d"); page.update()
                    dp_end = ft.DatePicker(on_change=on_end_date_change, value=default_end_date)
                    
                    def on_time_change(e):
                        if e.control.value: tf_time.value = e.control.value.strftime("%H:%M"); page.update()
                    tp = ft.TimePicker(on_change=on_time_change, value=default_time, time_picker_entry_mode=ft.TimePickerEntryMode.DIAL_ONLY)
                    
                    page.overlay.extend([dp_start, dp_end, tp])
                    
                    def start_save(e):
                        if not tf_summary.value: tf_summary.error_text = "내용을 입력하세요."; tf_summary.update(); return
                        
                        async def do_save():
                            try:
                                d_start_val = datetime.strptime(tf_start_date.value, "%Y-%m-%d")
                                d_end_val = datetime.strptime(tf_end_date.value, "%Y-%m-%d")
                                t_val = datetime.strptime(tf_time.value, "%H:%M").time()
                                
                                dt_start = datetime.combine(d_start_val.date(), t_val)
                                dt_end = datetime.combine(d_end_val.date(), t_val) + timedelta(hours=1)
                                
                                payload = {
                                    "title": tf_summary.value,
                                    "start_date": dt_start.strftime("%Y-%m-%d %H:%M:%S"),
                                    "end_date": dt_end.strftime("%Y-%m-%d %H:%M:%S"),
                                    "is_all_day": False,
                                    "color": "#448AFF",
                                    "created_by": page.session.get("user_id"),
                                    "user_id": page.session.get("user_id"),
                                    "channel_id": page.session.get("channel_id"), 
                                    "description": tf_description.value or "AI Generated from Chat"
                                }
                                
                                await calendar_service.create_event(payload)
                                page.snack_bar = ft.SnackBar(ft.Text("일정이 등록되었습니다!"), bgcolor="green"); page.snack_bar.open=True
                                page.close(dlg)
                                toggle_selection_mode(False) # Turn off selection mode
                                page.update()
                            except Exception as ex:
                                log_error(f"Event Save Failed: {ex}")
                                page.snack_bar = ft.SnackBar(ft.Text(f"등록 실패: {ex}"), bgcolor="red"); page.snack_bar.open=True; page.update()
                                
                        page.run_task(do_save)

                    dlg = ft.AlertDialog(
                        title=ft.Text("일정 등록", weight="bold", size=20),
                        content=ft.Container(
                            width=400,
                            content=ft.Column([
                                tf_summary,
                                tf_description,
                                ft.Row([
                                    ft.IconButton(ft.Icons.CALENDAR_MONTH, on_click=lambda _: page.open(dp_start), icon_color="#5C6BC0", tooltip="시작 날짜"),
                                    tf_start_date
                                ], alignment=ft.MainAxisAlignment.CENTER),
                                ft.Row([
                                    ft.IconButton(ft.Icons.EVENT_REPEAT, on_click=lambda _: page.open(dp_end), icon_color="#5C6BC0", tooltip="마감 날짜"),
                                    tf_end_date
                                ], alignment=ft.MainAxisAlignment.CENTER),
                                ft.Row([
                                    ft.IconButton(ft.Icons.ACCESS_TIME, on_click=lambda _: page.open(tp), icon_color="#5C6BC0"),
                                    tf_time
                                ], alignment=ft.MainAxisAlignment.CENTER)
                            ], tight=True, spacing=15)
                        ),
                        actions=[
                            ft.TextButton("취소", on_click=lambda _: page.close(dlg), style=ft.ButtonStyle(color="grey")),
                            ft.ElevatedButton("등록", on_click=start_save, bgcolor=AppColors.PRIMARY, color="white", style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))
                        ],
                        actions_alignment=ft.MainAxisAlignment.END,
                        shape=ft.RoundedRectangleBorder(radius=12)
                    )
                    page.open(dlg)
                    page.update()
                
                show_editor()
                
            except Exception as ex:
                try: page.close(loading_dlg)
                except: pass
                log_error(f"AI Dialog System Error: {ex}")
                print(f"AI Error: {ex}")
                # Fallback to Editor even on Outer Exception? 
                # If outer exception happens, 'msg' might be undefined or 'result' undefined.
                # Just show error snackbar for critical crashes.
                page.snack_bar = ft.SnackBar(ft.Text(f"시스템 오류: {str(ex)}"), bgcolor="red"); page.snack_bar.open=True
                page.update()
                
        # [FIX] Use explicit thread to avoid Flet task pool exhaustion
        import threading
        threading.Thread(target=run_analysis, daemon=True).start()

    def open_topic_member_management_dialog(e):
        try:
            print(f"DEBUG: Opening Member Dialog. TopicID={state.get('current_topic_id')}")
            if not state.get("current_topic_id"): 
                page.snack_bar = ft.SnackBar(ft.Text("오류: 선택된 토픽이 없습니다."), bgcolor="red")
                page.snack_bar.open = True
                page.update()
                return
        
            # Load Data
            topic_id = state.get("current_topic_id")
            channel_id = page.session.get("channel_id")
            
            # UI Holders
            members_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
            invite_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
            
            # Views (initialized late)
            members_view = ft.Column(visible=True)
            invite_view = ft.Column(visible=False)

            def load_members():
                try:
                    members = chat_service.get_topic_members(topic_id)
                    items = []
                    current_uid = page.session.get("user_id")
                    my_ch_role = page.session.get("user_role")
                    
                    # [DIAGNOSTIC] Log member list to terminal
                    print(f"DEBUG: Topic Members for {topic_id}: {len(members)}", flush=True)
                    for m in members:
                         print(f"  - {m.get('full_name')} ({m.get('user_id')}) role={m.get('permission_level')}", flush=True)

                    for m in members:
                        is_me = m['user_id'] == current_uid
                        can_kick = (my_ch_role in ['owner', 'manager']) and not is_me
                        
                        items.append(
                            ft.Container(
                                padding=10,
                                bgcolor="#F5F5F5",
                                border_radius=8,
                                content=ft.Row([
                                    ft.Row([
                                        ft.Icon(ft.Icons.PERSON, size=20, color="grey"),
                                        ft.Column([
                                            ft.Text(f"{m['full_name']}", weight="bold"),
                                            ft.Text(f"{m['email']} • {m['permission_level']}", size=12, color="grey")
                                        ], spacing=2)
                                    ]),
                                    ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, icon_color="red", 
                                                tooltip="내보내기",
                                                on_click=lambda e, u=m['user_id']: kick_member(u),
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
                                alignment=ft.alignment.center
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
                            padding=20, alignment=ft.alignment.center
                        )
                    ]
                    page.update()

            def kick_member(target_id):
                try:
                    chat_service.remove_topic_member(topic_id, target_id)
                    load_members()
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(ft.Text(f"오류: {ex}"), bgcolor="red"); page.snack_bar.open=True; page.update()

            def load_candidates():
                try:
                    candidates = chat_service.get_channel_members_not_in_topic(channel_id, topic_id)
                    items = []
                    for c in candidates:
                        items.append(
                            ft.Container(
                                padding=10, border=ft.border.all(1, "#EEEEEE"), border_radius=8,
                                content=ft.Row([
                                    ft.Text(f"{c['full_name']}"),
                                    ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color="green", 
                                                tooltip="초대",
                                                on_click=lambda e, u=c['user_id']: invite_user(u))
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                            )
                        )
                    if not items:
                        items.append(ft.Container(content=ft.Text("초대할 수 있는 멤버가 없습니다.\n(모든 직원이 이미 참여 중입니다)", color="grey", text_align="center"), alignment=ft.alignment.center, padding=20))
                    
                    invite_col.controls = items
                    # [DEBUG] Feedback
                    print(f"Candidates Loaded: {len(items)}")
                    page.update()
    
                except Exception as ex:
                    print(f"Load Candidates Error: {ex}")

            def invite_user(target_id):
                try:
                    chat_service.add_topic_member(topic_id, target_id)
                    # Toggle back
                    invite_view.visible = False
                    members_view.visible = True
                    load_members()
                    page.update()
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(ft.Text(f"초대 실패: {ex}"), bgcolor="red"); page.snack_bar.open=True; page.update()

            def show_invite_view(e):
                members_view.visible = False
                invite_view.visible = True
                load_candidates()
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

            dlg = ft.AlertDialog(
                title=ft.Text("채팅방 멤버 관리"),
                content=ft.Container(
                    width=400,
                    height=500, # Fixed height for stability across devices
                    content=ft.Column([members_view, invite_view], tight=True, scroll=ft.ScrollMode.AUTO)
                ),
                actions=[ft.TextButton("닫기", on_click=lambda e: page.close(dlg))]
            )
            page.open(dlg)
            page.update()
            
            # Call load_members safely
            try:
                load_members()
            except: pass

        except Exception as e:
            print(f"CRITICAL ERROR in Member Dialog: {e}")
            import traceback
            traceback.print_exc()
            page.snack_bar = ft.SnackBar(ft.Text(f"대화상자 열기 실패: {e}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()


    chat_page_header = AppHeader(
        title_text="스레드",
        on_back_click=lambda _: back_to_list(),
        action_button=ft.Row([
            ft.IconButton(ft.Icons.SEARCH, icon_color=AppColors.TEXT_SECONDARY, tooltip="검색", on_click=open_search_dialog),
            # [NEW] AI Summary Button (Multi-select)
            ft.IconButton(ft.Icons.AUTO_AWESOME_OUTLINED, icon_color="#5C6BC0", tooltip="AI 요약", on_click=lambda _: toggle_selection_mode(True)),
            # [NEW] Member Management
            ft.IconButton(ft.Icons.PEOPLE_OUTLINE, icon_color=AppColors.TEXT_SECONDARY, tooltip="멤버 관리", on_click=open_topic_member_management_dialog),
             ft.PopupMenuButton(
                icon=ft.Icons.MORE_VERT,
                icon_color=AppColors.TEXT_SECONDARY,
                items=[
                    ft.PopupMenuItem(
                        text="새로 고침",
                        icon=ft.Icons.REFRESH,
                        on_click=lambda _: load_messages()
                    )
                ]
            )
        ])
    )

    # [Active Selection Bar]
    selection_action_bar = ft.Container(
        content=ft.Row([
            ft.TextButton("취소", on_click=lambda _: toggle_selection_mode(False), icon=ft.Icons.CLOSE, icon_color="white", style=ft.ButtonStyle(color="white")),
            ft.Container(expand=True), # Spacer
            ft.ElevatedButton("AI 요약 실행", icon=ft.Icons.AUTO_AWESOME, on_click=open_ai_calendar_dialog, bgcolor="white", color="#1976D2")
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
        bgcolor="#1976D2", # Blue bar
        visible=False
    )

    def toggle_selection_mode(active):
        print(f"DEBUG_CHAT: Toggling Selection Mode to {active}")
        state.set("selection_mode", active)
        state.clear_selected()
        selection_action_bar.visible = active
        input_row_container.visible = not active
        page.update()
        # [FIX] Delayed load to ensure state has time to settle (optional but safer)
        load_messages() 

    chat_input_row = ft.Row([
        ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED, icon_color="#757575", on_click=lambda _: local_file_picker.pick_files()),
        msg_input, 
        ft.IconButton(ft.Icons.SEND_ROUNDED, icon_color="#2E7D32", icon_size=32, on_click=lambda _: send_message())
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
            ft.Container(content=message_list_view, expand=True, bgcolor="#F5F5F5"),
            ft.Container(
                content=ft.Stack([
                    input_row_container,
                    selection_action_bar
                ])
            )
        ])
    )
    def back_to_list():
        state["view_mode"] = "list"
        update_layer_view()

    def update_layer_view():
        root_view.controls = [list_page] if state["view_mode"] == "list" else [chat_page]
        page.update()

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
            while state["is_active"]:
                if not root_view.page:
                    state["is_active"] = False
                    break
                
                try:
                    curr_tid = state.get("current_topic_id")
                    last_id = state.get("last_loaded_msg_id")
                    
                    if curr_tid:
                        # [VERBOSE] Log 1 in 10 times or just on change?
                        # file_log_info(f"POLLING CHECK: {curr_tid}")
                        if chat_service.check_new_messages(curr_tid, last_id):
                             file_log_info(f"POLLING: New message detected for {curr_tid}! Reloading.")
                             load_messages()
                except Exception as poll_ex:
                    file_log_info(f"POLLING ERROR: {repr(poll_ex)}")
                
                await asyncio.sleep(3)
        
        # 2. Start Realtime Connection (Disabled for now due to library incompatibility)
        async def connection_loop():
            file_log_info("CONNECTION LOOP STARTED (Passive Mode)")
            # await asyncio.sleep(2)
            # ... (Realtime implementation temporarily disabled to prevent logs spam/crash)
            # The polling loop is the primary mechanism now.
            while state["is_active"]:
                await asyncio.sleep(10)

        # Run both
        await asyncio.gather(polling_loop(), connection_loop())

    def init_chat():
        update_layer_view()
        load_topics(True)
        page.run_task(realtime_handler)

    init_chat()
    
    return [ft.SafeArea(root_view, expand=True)]
