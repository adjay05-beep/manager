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
    # 외부 접속(모바일) 허용을 위해 host="0.0.0.0"으로 실행합니다.
    ft.app(target=main, port=8555, host="0.0.0.0")
