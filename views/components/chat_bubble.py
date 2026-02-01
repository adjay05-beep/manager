import flet as ft
from datetime import datetime
from views.styles import AppColors

class ChatBubble(ft.Container):
    def __init__(self, message, current_user_id, selection_mode=False, on_select=None, on_image_click=None):
        super().__init__()
        self.message = message
        self.current_user_id = current_user_id
        self.selection_mode = bool(selection_mode)
        self.on_select = on_select
        self.on_image_click = on_image_click
        self.is_sending = message.get("is_sending", False)
        # Assign key for programmatic scrolling
        self.key = str(message.get("id"))
        
        # [ROBUST ID COMPARISON] Handles UUID vs String
        self.is_me = str(message.get("user_id")).strip().lower() == str(self.current_user_id).strip().lower()
        
        self.build_ui()

    def build_ui(self):
        msg = self.message
        sender_id = msg.get("user_id")
        content = msg.get("content", "")
        img_url = msg.get("image_url")
        created_at = msg.get("created_at", "")
        profile = msg.get("profiles", {}) or {}
        username = profile.get("full_name") or profile.get("username", "Unknown")
        
        is_me = self.is_me
        
        # Time Formatting
        time_str = ""
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at)
                if dt.tzinfo: dt = dt.astimezone()
                else:
                   from datetime import timedelta
                   dt = dt + timedelta(hours=9)
                ampm = "오전" if dt.hour < 12 else "오후"
                hour = dt.hour if dt.hour <= 12 else dt.hour - 12
                if hour == 0: hour = 12
                time_str = f"{ampm} {hour}:{dt.minute:02d}"
            except ValueError:
                pass  # Invalid date format
            
        status_indicator = None
        if self.is_sending:
            status_indicator = ft.Icon(ft.Icons.ACCESS_TIME_ROUNDED, size=12, color="#9E9E9E")
            time_str = ""
            
        avatar = ft.CircleAvatar(
            content=ft.Text(username[:1], size=10, color="white"),
            bgcolor="blue" if is_me else "green",
            radius=16,
            visible=not is_me
        )

        bubble_items = []
        if is_me:
            bg_color = "#FFF9C4" # Pale Yellow
            text_color = "black"
            border_side = ft.border.all(1, "#FFECB3") # Slightly darker yellow border
        else:
            bg_color = "#F0F0F0" 
            text_color = "black"
            border_side = None
        
        if img_url:
            clean_url = img_url.split("?")[0]
            ext = clean_url.split(".")[-1].lower() if "." in clean_url else ""
            if ext in ["jpg", "jpeg", "png", "gif", "webp", "ico", "bmp"]:
                img_widget = ft.Image(src=img_url, width=200, height=200, fit=ft.ImageFit.COVER, border_radius=8)
                if self.on_image_click:
                    bubble_items.append(ft.Container(content=img_widget, on_click=lambda e: self.on_image_click(img_url)))
                else: bubble_items.append(img_widget)
            elif ext in ["mp4", "mov", "avi", "wmv", "mkv", "webm"]:
                def play_video(e):
                    try:
                        v = ft.Video(expand=True, playlist=[ft.VideoMedia(img_url)], autoplay=True, show_controls=True)
                        w = min(e.page.width - 20, 600)
                        dlg = ft.AlertDialog(content=ft.Container(content=v, width=w, height=w*0.56, bgcolor="black"))
                        e.page.open(dlg); e.page.update()
                    except: e.page.launch_url(img_url)
                bubble_items.append(ft.Container(content=ft.Row([ft.Icon(ft.Icons.PLAY_CIRCLE_FILL, color="red"), ft.Text("비디오")], spacing=10), padding=10, border=ft.border.all(1, "grey"), on_click=play_video))
            else:
                 bubble_items.append(ft.Container(content=ft.Row([ft.Icon(ft.Icons.ATTACH_FILE), ft.Text("파일")], spacing=10), padding=10, border=ft.border.all(1, "grey"), on_click=lambda e: e.page.launch_url(img_url)))
        
        if content:
            bubble_items.append(ft.Text(content, color=text_color, size=14, selectable=not self.selection_mode))

        bubble = ft.Container(
            content=ft.Column(bubble_items, spacing=5, tight=True),
            padding=10,
            border_radius=ft.border_radius.only(top_left=12, top_right=12, bottom_left=0 if is_me else 12, bottom_right=12 if is_me else 0),
            bgcolor=bg_color,
            shadow=ft.BoxShadow(blur_radius=2, color="#1A000000"),
            border=border_side
        )

        from views.components.custom_checkbox import CustomCheckbox
        selection_ctrl = ft.Container(visible=False)
        if self.selection_mode:
            self.custom_checkbox = CustomCheckbox(
                value=False,
                on_change=lambda cb: self.on_select(self.message.get('id'), cb.value) if self.on_select else None,
                label_style=ft.TextStyle(size=0)
            )
            selection_ctrl = ft.Container(
                content=self.custom_checkbox,
                width=40, height=40, alignment=ft.Alignment(0, 0), visible=True
            )
        # [FINAL ALIGNMENT] 
        # Me: RIGHT (MainAxisAlignment.END)
        # Others: LEFT (MainAxisAlignment.START)
        if is_me: # Me (Right side)
            self.content = ft.Row([
                ft.Container(expand=True), # Push everything to the right
                selection_ctrl,
                ft.Row([
                    ft.Row([c for c in [status_indicator, ft.Text(time_str, size=10, color="grey") if time_str else None] if c], spacing=2),
                    bubble,
                ], vertical_alignment="end", spacing=4)
            ], alignment=ft.MainAxisAlignment.END, spacing=10)
        else: # Others (Left side)
            self.content = ft.Row([
                avatar,
                ft.Column([
                    ft.Text(username, size=11, color="grey"),
                    ft.Row([
                        bubble,
                        ft.Text(time_str, size=10, color="grey"),
                    ], vertical_alignment="end", spacing=4)
                ], horizontal_alignment=ft.CrossAxisAlignment.START),
                selection_ctrl,
                ft.Container(expand=True), # Push everything to the left
            ], alignment=ft.MainAxisAlignment.START, spacing=10)

        self.opacity = 0.6 if self.is_sending else 1.0
        self.padding = ft.padding.symmetric(vertical=5)
        self.expand = True # Essential for full-width in ListView
