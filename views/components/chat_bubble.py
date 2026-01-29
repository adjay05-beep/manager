import flet as ft
from datetime import datetime
from views.styles import AppColors

class ChatBubble(ft.Container):
    def __init__(self, message, current_user_id, selection_mode=False, on_select=None, on_image_click=None):
        super().__init__()
        self.message = message
        self.current_user_id = current_user_id
        self.selection_mode = selection_mode
        self.on_select = on_select
        self.on_image_click = on_image_click
        # [NEW] Optimistic UI Flag
        self.is_sending = message.get("is_sending", False)
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
            
        # [NEW] Sending Status Indicator
        status_indicator = None
        if self.is_sending:
            status_indicator = ft.Icon(ft.Icons.ACCESS_TIME_ROUNDED, size=12, color="#9E9E9E", tooltip="전송 중...")
            time_str = "" # Hide time while sending if preferred, or keep it. Let's keep it empty or "..."
            
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
        else:
            # ... (rest same)
            bg_color = "#F0F0F0" # Light Grey
            text_color = "black"
            align = ft.MainAxisAlignment.START
            border_side = None
        
        # ... (File Type Detection Logic - Already Implemented, assume preserved if I don't touch execution block) ...
        # Wait, I am replacing the START of build_ui. The file rendering logic is further down.
        # I need to be careful not to overwrite the file logic I just added.
        # The file logic starts at `if img_url:`.
        
        # Let's target lines 4-36 (Init and start of build_ui)
        pass

    # [RESTARTING STRATEGY]
    # I will replace lines 4-37.
    # Lines 4-37 covers __init__ and the start of build_ui up to Avatar creation.


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
            # [FIX] Robust File Type Detection
            # Extract extension ignoring query parameters
            clean_url = img_url.split("?")[0]
            ext = clean_url.split(".")[-1].lower() if "." in clean_url else ""
            
            image_exts = ["jpg", "jpeg", "png", "gif", "webp", "ico", "bmp"]
            video_exts = ["mp4", "mov", "avi", "wmv", "mkv", "webm"]
            
            if ext in image_exts:
                img_widget = ft.Image(
                        src=img_url,
                        width=200,
                        height=200,
                        fit=ft.ImageFit.COVER,
                        border_radius=8,
                        repeat=ft.ImageRepeat.NO_REPEAT,
                        gapless_playback=True
                    )
                if self.on_image_click:
                    bubble_items.append(
                        ft.Container(content=img_widget, on_click=lambda e: self.on_image_click(img_url))
                    )
                else:
                    bubble_items.append(img_widget)
            elif ext in video_exts:
                # [NEW] Video Card with Modal Player
                def play_video(e):
                    try:
                        # Modal Video Player using Flet's Native Video Control
                        video_media = ft.VideoMedia(img_url)
                        player = ft.Video(
                            expand=True,
                            playlist=[video_media],
                            playlist_mode=ft.PlaylistMode.SINGLE,
                            fill_color=ft.Colors.BLACK,
                            aspect_ratio=None, # Auto
                            autoplay=True,
                            filter_quality=ft.FilterQuality.HIGH,
                            muted=False,
                            show_controls=True
                        )
                        
                        # [FIX] Larger Dialog Size
                        w = 600
                        try: w = min(e.page.width - 20, 600)
                        except: pass

                        dlg_content = ft.Container(
                            content=player,
                            width=w, 
                            height=w * 0.56, # 16:9 approx
                            bgcolor="black",
                            alignment=ft.alignment.center
                        )
                        
                        dlg = ft.AlertDialog(
                            content=dlg_content,
                            content_padding=0,
                            bgcolor="transparent",
                            inset_padding=10
                        )
                        e.page.open(dlg)
                        e.page.update()
                    except Exception as ex:
                        print(f"Video Error: {ex}")
                        e.page.launch_url(img_url)

                card = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.PLAY_CIRCLE_FILL, color="#E53935", size=40),
                        ft.Column([
                            ft.Text("동영상 재생", weight="bold", size=14, color="#212121"),
                            ft.Text(f"{ext.upper()} 파일", size=12, color="grey")
                        ], spacing=2, alignment="center")
                    ], alignment="start", spacing=15),
                    padding=ft.padding.symmetric(horizontal=15, vertical=15),
                    bgcolor="#FAFAFA" if is_me else "white",
                    border=ft.border.all(1, "#E0E0E0"),
                    border_radius=12,
                    width=280, # [FIX] Larger Preview Width
                    on_click=play_video,
                    ink=True
                )
                bubble_items.append(card)
            else:
                # [NEW] Generic File Attachment
                 bubble_items.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.INSERT_DRIVE_FILE, color="#757575", size=30),
                            ft.Column([
                                ft.Text("파일 첨부", weight="bold", size=13, color="#212121"),
                                ft.Text(f"{ext.upper()}", size=10, color="grey")
                            ], spacing=0, expand=True),
                            ft.IconButton(ft.Icons.DOWNLOAD_ROUNDED, icon_color="#0288D1", tooltip="다운로드", on_click=lambda e: e.page.launch_url(img_url))
                        ]),
                        padding=10,
                        bgcolor="#FAFAFA" if is_me else "white",
                        border=ft.border.all(1, "#E0E0E0"),
                        border_radius=10,
                        width=220
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

        # [NEW] Selection Checkbox
        self.selection_checkbox = None
        selection_ctrl = ft.Container()
        if self.selection_mode:
            self.selection_checkbox = ft.Checkbox(
                value=False,
                fill_color=AppColors.PRIMARY if hasattr(AppColors, 'PRIMARY') else "green",
                on_change=lambda e: self.on_select(self.message.get('id'), e.control.value) if self.on_select else None
            )
            selection_ctrl = self.selection_checkbox
            
            # Make the bubble clickable to toggle selection
            def toggle_select(e):
                if self.selection_checkbox:
                    self.selection_checkbox.value = not self.selection_checkbox.value
                    self.selection_checkbox.update()
                    if self.on_select:
                        self.on_select(self.message.get('id'), self.selection_checkbox.value)
            
            # Attach click handler to the bubble container
            bubble.on_click = toggle_select
            bubble.ink = True # feedback


        display_row = ft.Row([
            selection_ctrl,
            avatar,
            ft.Column([
                ft.Text(username, size=11, color="grey", visible=not is_me),
                ft.Row([
                    # [FIX] Add Status Indicator for 'Me'
                    ft.Row([status_indicator] + ([ft.Text(time_str, size=10, color="grey")] if time_str else []), spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER) if (is_me and status_indicator) else (ft.Text(time_str, size=10, color="grey") if is_me else ft.Container()),
                    
                    bubble,
                    ft.Text(time_str, size=10, color="grey") if not is_me else ft.Container(),
                ], vertical_alignment="end", spacing=4)
            ], spacing=2)
        ], alignment="end" if is_me else "start", vertical_alignment="start")

        self.content = display_row
        # [NEW] Opacity for Pending Messages
        self.opacity = 0.6 if self.is_sending else 1.0
        self.padding = ft.padding.symmetric(vertical=5)
