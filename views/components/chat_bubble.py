import flet as ft
from datetime import datetime

class ChatBubble(ft.Container):
    def __init__(self, message, current_user_id):
        super().__init__()
        self.message = message
        self.current_user_id = current_user_id
        self.build_ui()

    def build_ui(self):
        msg = self.message
        sender_id = msg.get("user_id")
        content = msg.get("content", "")
        img_url = msg.get("image_url")
        created_at = msg.get("created_at", "")
        profile = msg.get("profiles", {}) or {}
        username = profile.get("full_name") or profile.get("username", "Unknown")
        
        is_me = (sender_id == self.current_user_id)
        
        # Time Formatting
        time_str = ""
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at)
                time_str = dt.strftime("%H:%M")
            except: pass

        # Avatar
        avatar = ft.CircleAvatar(
            content=ft.Text(username[:1], size=10, color="white"),
            bgcolor="blue" if is_me else "green",
            radius=16,
            visible=not is_me
        )

        # Bubble Content
        bubble_items = []
        border_side = None
        
        if is_me:
            bg_color = "white" 
            text_color = "black"
            align = ft.MainAxisAlignment.END
            border_side = ft.border.all(1, "#E0E0E0")
            
            # Show read count if available (and if verify logic exists)
            # For now simple bubble
        else:
            bg_color = "#F0F0F0" # Light Grey
            text_color = "black"
            align = ft.MainAxisAlignment.START
            border_side = None
        
        if img_url:
            bubble_items.append(
                ft.Image(
                    src=img_url,
                    width=200,
                    height=200,
                    fit=ft.ImageFit.COVER,
                    border_radius=8,
                    repeat=ft.ImageRepeat.NO_REPEAT,
                )
            )
        
        if content:
            bubble_items.append(
                ft.Text(content, color=text_color, size=14, selectable=True)
            )

        bubble = ft.Container(
            content=ft.Column(bubble_items, spacing=5, tight=True),
            padding=10,
            border_radius=ft.border_radius.only(
                top_left=12, top_right=12,
                bottom_left=0 if is_me else 12,
                bottom_right=12 if is_me else 0
            ),
            bgcolor=bg_color,
            shadow=ft.BoxShadow(blur_radius=2, color="#1A000000"),
            border=border_side
        )

        display_row = ft.Row([
            avatar,
            ft.Column([
                ft.Text(username, size=11, color="grey", visible=not is_me),
                ft.Row([
                    ft.Text(time_str, size=10, color="grey") if is_me else ft.Container(),
                    bubble,
                    ft.Text(time_str, size=10, color="grey") if not is_me else ft.Container(),
                ], vertical_alignment="end", spacing=4)
            ], spacing=2)
        ], alignment="end" if is_me else "start", vertical_alignment="start")

        self.content = display_row
        self.padding = ft.padding.symmetric(vertical=5)
