import flet as ft
import asyncio
from datetime import datetime, timedelta
from services.handover_service import handover_service
from views.styles import AppColors, AppTextStyles, AppLayout

def get_handover_controls(page: ft.Page, navigate_to):
    user_id = page.session.get("user_id")
    channel_id = page.session.get("channel_id")
    
    # UI State
    current_tab = "업무 일지"
    grouped_data = {}
    POLL_INTERVAL = 10 # Seconds

    # Controls
    list_view = ft.ListView(expand=True, spacing=10, padding=20)
    input_tf = ft.TextField(
        hint_text="내용을 입력하세요...",
        expand=True,
        border_radius=20,
        bgcolor="#F5F5F5",
        border_color="transparent",
        content_padding=ft.padding.symmetric(horizontal=15, vertical=10),
    )

    def open_edit_dialog(item):
        edit_tf = ft.TextField(value=item.get("content", ""), multiline=True, expand=True)
        
        async def save_edit(e):
            if await handover_service.update_handover(item.get("id"), edit_tf.value):
                page.close(dlg)
                await fetch_and_update()

        dlg = ft.AlertDialog(
            title=ft.Text("기록 수정"),
            content=ft.Container(content=edit_tf, height=100),
            actions=[
                ft.TextButton("취소", on_click=lambda _: page.close(dlg)),
                ft.ElevatedButton("저장", on_click=save_edit, bgcolor=AppColors.PRIMARY, color="white")
            ]
        )
        page.open(dlg)

    async def delete_entry(item_id):
        await handover_service.delete_handover(item_id)
        await fetch_and_update()

    def render_feed():
        list_view.controls.clear()
        target_cat = "handover" if current_tab == "업무 일지" else "order"
        
        # Sort dates descending
        sorted_dates = sorted(grouped_data.keys(), reverse=True)

        for d_str in sorted_dates:
            items = grouped_data[d_str].get(target_cat, [])
            if not items: continue

            # Date Header
            dt = datetime.fromisoformat(d_str)
            m, d = dt.month, dt.day
            today_str = (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d")
            header_text = f"{m}월 {d}일"
            if d_str == today_str: header_text += " (오늘)"
            
            list_view.controls.append(
                ft.Container(
                    content=ft.Text(header_text, size=12, color="grey", weight="bold"),
                    alignment=ft.alignment.center,
                    padding=ft.padding.only(top=10, bottom=5)
                )
            )

            for item in items:
                content = item.get("content", "")
                time_str = item.get("time_str", "")
                author = item.get("user_name", "")
                item_id = item.get("id")
                
                def create_edit_handler(i):
                    async def handler(e): open_edit_dialog(i)
                    return handler

                def create_delete_handler(oid):
                    async def handler(e): await delete_entry(oid)
                    return handler

                edit_btn = ft.IconButton(ft.Icons.EDIT, icon_size=16, icon_color="grey", on_click=create_edit_handler(item))
                delete_btn = ft.IconButton(ft.Icons.CLOSE, icon_size=16, icon_color="grey", on_click=create_delete_handler(item_id))

                card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(content, size=15, color="#424242", expand=True),
                            ft.Row([edit_btn, delete_btn], spacing=0)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START),
                        ft.Row([
                            ft.Text(f"{author}", size=10, color="grey"),
                            ft.Text(time_str, size=10, color="grey")
                        ], alignment=ft.MainAxisAlignment.END)
                    ], spacing=5),
                    padding=10, bgcolor="white", border_radius=12, border=ft.border.all(1, "#EEEEEE"),
                )
                list_view.controls.append(card)

        list_view.controls.append(ft.Container(height=20))
        page.update()

    async def fetch_and_update():
        raw = await handover_service.get_handovers(channel_id)
        from collections import defaultdict
        temp_grouped = defaultdict(lambda: {"handover": [], "order": []})
        raw.sort(key=lambda x: x.get("created_at") or "")
        for item in raw:
            try:
                c_at = item.get("created_at")
                if c_at:
                    if c_at.endswith('Z'): c_at = c_at.replace('Z', '+00:00')
                    dt = datetime.fromisoformat(c_at) + timedelta(hours=9)
                    d_key = dt.strftime("%Y-%m-%d")
                    t_str = dt.strftime("%H:%M")
                    cat = item.get("category", "handover")
                    profile = item.get("profiles")
                    user_name = profile.get("full_name") if profile else "멤버"
                    temp_grouped[d_key][cat].append({"id": item.get("id"), "content": item.get("content"), "time_str": t_str, "user_name": user_name})
            except: pass
        nonlocal grouped_data
        grouped_data = dict(temp_grouped)
        render_feed()

    async def submit_entry(e=None):
        txt = input_tf.value
        if not txt.strip(): return
        input_tf.value = ""; input_tf.update()
        target_cat = "handover" if current_tab == "업무 일지" else "order"
        await handover_service.add_handover_entry(user_id, channel_id, target_cat, txt)
        await fetch_and_update()

    def on_tab_change(e):
        nonlocal current_tab
        current_tab = e.control.content.value
        for c in tabs_row.controls:
             if isinstance(c, ft.Container) and c.content:
                 is_selected = c.content.value == current_tab
                 c.bgcolor = "#E3F2FD" if is_selected else "transparent"
                 c.content.color = "#1565C0" if is_selected else "#9E9E9E"
        tabs_row.update()
        render_feed()

    tabs_row = ft.Row([
        ft.Container(content=ft.Text(t, size=16), padding=ft.padding.symmetric(horizontal=12, vertical=8), border_radius=20, on_click=on_tab_change)
        for t in ["업무 일지", "발주 일지"]
    ], alignment=ft.MainAxisAlignment.CENTER)

    input_area = ft.Container(content=ft.Row([input_tf, ft.IconButton(ft.Icons.SEND_ROUNDED, on_click=lambda e: page.run_task(submit_entry))]), padding=10)
    header = ft.Container(content=ft.Column([ft.Text("업무 일지", size=22, weight="bold", text_align="center"), tabs_row]))

    page.run_task(fetch_and_update)
    return [ft.Column([header, ft.Container(list_view, expand=True), input_area], expand=True)]
