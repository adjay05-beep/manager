import flet as ft
from views.login_view import get_login_controls
from views.home_view import get_home_controls
from views.chat_view import get_chat_controls
from views.calendar_view import get_calendar_controls
from views.order_view import get_order_controls
from views.closing_view import get_closing_controls
from views.signup_view import get_signup_controls
from views.create_profile_view import get_create_profile_controls
from views.work_view import get_work_controls

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
    # The on_nav_change function is now integrated into the NavigationBar's on_change property
    # and will be dynamically updated in navigate_to.

    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.CHAT_BUBBLE_OUTLINE, selected_icon=ft.Icons.CHAT_BUBBLE, label="팀"),
            ft.NavigationBarDestination(icon=ft.Icons.MIC_NONE, selected_icon=ft.Icons.MIC, label="음성"),
            ft.NavigationBarDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label="홈"),
            ft.NavigationBarDestination(icon=ft.Icons.WORK_OUTLINE, selected_icon=ft.Icons.WORK, label="업무"),
            ft.NavigationBarDestination(icon=ft.Icons.CALENDAR_MONTH_OUTLINED, selected_icon=ft.Icons.CALENDAR_MONTH, label="일정"),
        ],
        on_change=lambda e: navigate_to(
            "chat" if e.control.selected_index == 0 else
            "order" if e.control.selected_index == 1 else
            "home" if e.control.selected_index == 2 else 
            "work" if e.control.selected_index == 3 else
            "calendar"
        ),
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
            elif route == "home": page.navigation_bar.selected_index = 2
            elif route == "work": page.navigation_bar.selected_index = 3
            elif route == "calendar": page.navigation_bar.selected_index = 4
            else: 
                # If route is not explicitly mapped to a nav bar item, select None
                page.navigation_bar.selected_index = None

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
        elif route == "chat":
            controls = get_chat_controls(page, navigate_to)
        elif route == "calendar":
            controls = get_calendar_controls(page, navigate_to)
        elif route == "order":
            # Pass the global recorder
            controls = get_order_controls(page, navigate_to)
        elif route == "closing":
            # Direct link support, but now part of Work tab usually
            controls = get_closing_controls(page, navigate_to)
        elif route == "work":
            controls = get_work_controls(page, navigate_to)
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
