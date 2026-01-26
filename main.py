import flet as ft
from views.login_view import get_login_controls
from views.home_view import get_home_controls
from views.chat_view import get_chat_controls
from views.calendar_view import get_calendar_controls
from views.order_view import get_order_controls
from views.closing_view import get_closing_controls
from views.signup_view import get_signup_controls
from views.create_profile_view import get_create_profile_controls

def main(page: ft.Page):
    page.title = "The Manager"
    # 모바일/데스크탑 반응형 대응을 위해 고정 크기 제거
    # page.window_width = 390
    # page.window_height = 844
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.spacing = 0
    page.bgcolor = "#0A1929" # SaaS Navy Global Default
    
    # Global FilePicker for all views
    page.file_picker = ft.FilePicker()
    page.overlay.append(page.file_picker)

    # Global Chat FilePicker (Prevent Chat Layout Freeze)
    page.chat_file_picker = ft.FilePicker()
    page.overlay.append(page.chat_file_picker)

    # Global AudioRecorder (Singleton for WeChat-style Voice Memo)
    if not hasattr(page, "audio_recorder"):
        page.audio_recorder = ft.AudioRecorder()
        page.overlay.append(page.audio_recorder)
    
    
    # Persistent Navigation Bar
    def on_nav_change(e):
        idx = e.control.selected_index
        if idx == 0: navigate_to("chat")
        elif idx == 1: navigate_to("order") # Voice Memo
        elif idx == 2: navigate_to("closing")

    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.CHAT, label="팀 스레드"),
            ft.NavigationBarDestination(icon=ft.Icons.MIC, label="음성 메모"),
            ft.NavigationBarDestination(icon=ft.Icons.CHECK_CIRCLE, label="마감 점검"),
        ],
        on_change=on_nav_change,
        bgcolor="#1A237E", # Dark Blue SaaS Theme
        indicator_color="#3949AB"
    )

    def navigate_to(route):
        page.clean()
        
        # Hide Nav Bar on Auth Pages
        if route in ["login", "signup", "create_profile"]:
            page.navigation_bar.visible = False
        else:
            page.navigation_bar.visible = True
            # Sync Nav Bar State
            if route == "chat": page.navigation_bar.selected_index = 0
            elif route == "order": page.navigation_bar.selected_index = 1
            elif route == "closing": page.navigation_bar.selected_index = 2
            else: 
                # Keep current or set to None/0? 
                # Ensure it doesn't break. 
                pass

        if route == "login" or route == "/":
            controls = get_login_controls(page, navigate_to)
        elif route == "signup":
            controls = get_signup_controls(page, navigate_to)
        elif route == "create_profile":
            user_id = page.session.get("user_id")
            user_email = page.session.get("user_email")
            if not user_email:
                user_email = "unknown@example.com"
            controls = get_create_profile_controls(page, navigate_to, user_id, user_email)
        elif route == "home":
            controls = get_home_controls(page, navigate_to)
            # Home is not in nav bar, maybe select None? 
            # Or make Home accessible? User asked for 3 icons. 
            # If user goes to home, nav bar is visible? 
            # Let's keep it visible.
        elif route == "chat":
            controls = get_chat_controls(page, navigate_to)
        elif route == "calendar":
            controls = get_calendar_controls(page, navigate_to)
        elif route == "order":
            # Pass the global recorder
            controls = get_order_controls(page, navigate_to)
        elif route == "closing":
            controls = get_closing_controls(page, navigate_to)
        else:
            controls = [ft.Text("Not Found")]
        
        page.add(*controls)
        page.update()

    navigate_to("login")

if __name__ == "__main__":
    import os
    # 클라우드 환경(Render 등)에서 제공하는 PORT 변수를 우선 사용합니다.
    port = int(os.getenv("PORT", 8555))
    host = "0.0.0.0"
    # 브라우저 실행 모드로 명시적 설정
    ft.app(target=main, port=port, host=host, assets_dir="assets", view=ft.AppView.WEB_BROWSER)
