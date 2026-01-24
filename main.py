import flet as ft
from app_views import get_login_controls, get_home_controls, get_closing_controls, get_chat_controls, get_calendar_controls, get_order_controls

def main(page: ft.Page):
    page.title = "The Manager"
    page.window_width = 390
    page.window_height = 844
    page.theme_mode = ft.ThemeMode.LIGHT
    
    def navigate_to(route):
        page.clean()
        if route == "login" or route == "/":
            controls = get_login_controls(page, navigate_to)
        elif route == "home":
            controls = get_home_controls(page, navigate_to)
        elif route == "chat":
            controls = get_chat_controls(page, navigate_to)
        elif route == "calendar":
            controls = get_calendar_controls(page, navigate_to)
        elif route == "order":
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
    ft.app(target=main, port=port, host=host, assets_dir="assets")


