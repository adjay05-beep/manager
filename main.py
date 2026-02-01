import flet as ft
from views.login_view import get_login_controls
from views.home_view import get_home_controls
from views.chat_view import get_chat_controls
from views.calendar_view import get_calendar_controls
from views.order_view import get_order_controls
from utils.logger import log_error, log_info
from views.closing_view import get_closing_controls
from views.signup_view import get_signup_controls
from views.create_profile_view import get_create_profile_controls
from views.work_view import get_work_controls
from views.profile_edit_view import get_profile_edit_controls
from views.onboarding_view import get_onboarding_controls
from views.store_manage_view import get_store_manage_controls
from views.handover_view import get_handover_controls

async def main(page: ft.Page):
    # print("DEBUG: main() started")
    print("DEBUG: Inside main function!")
    page.title = "The Manager"

    # [Flet 0.80+] Custom session storage since page.session API changed
    page.app_session = {}
    # page.window_width = 390
    # page.window_height = 844
    
    # [THEME PERSISTENCE] Load theme from client_storage
    # print("DEBUG: Loading theme...")
    try:
        theme_mode_str = await page.client_storage.get_async("theme_mode")
        # print(f"DEBUG: Theme loaded: {theme_mode_str}")
    except Exception as e:
        # print(f"DEBUG: Theme load error: {e}")
        theme_mode_str = None
    
    if theme_mode_str == "dark":
        page.theme_mode = ft.ThemeMode.DARK
    else:
        page.theme_mode = ft.ThemeMode.LIGHT
    
    page.padding = 0
    page.spacing = 0
    # page.bgcolor = "white" # [REMOVED] Let theme control bgcolor (white/dark)
    
    # [Flet 0.80+] FilePicker disabled - causes "Unknown control" error
    # TODO: Re-enable when Flet 0.80 FilePicker is properly supported
    page.file_picker = None
    page.chat_file_picker = None

    # AudioRecorder removed (Deprecated)
    page.audio_recorder = None
    
    
    # Persistent Navigation Bar
    # The on_nav_change function is now integrated into the NavigationBar's on_change property
    # and will be dynamically updated in navigate_to.

    print("DEBUG: init NavigationBar")
    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label="홈"),
            ft.NavigationBarDestination(icon=ft.Icons.CHAT_BUBBLE_OUTLINE, selected_icon=ft.Icons.CHAT_BUBBLE, label="메신저"),
            ft.NavigationBarDestination(icon=ft.Icons.CALENDAR_MONTH_OUTLINED, selected_icon=ft.Icons.CALENDAR_MONTH, label="일정"),
            ft.NavigationBarDestination(icon=ft.Icons.DESCRIPTION_OUTLINED, selected_icon=ft.Icons.DESCRIPTION, label="업무일지"),
            ft.NavigationBarDestination(icon=ft.Icons.CHECK_CIRCLE_OUTLINE, selected_icon=ft.Icons.CHECK_CIRCLE, label="마감"),
            ft.NavigationBarDestination(icon=ft.Icons.MIC_NONE, selected_icon=ft.Icons.MIC, label="음성"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS, label="설정"),
        ],
        on_change=lambda e: page.run_task(on_nav_change, e),
        bgcolor="white",
        indicator_color="#E3F2FD",
        shadow_color="black",
        elevation=5
    )

    # Optimized Route Management
    page.history_stack = []

    async def on_nav_change(e):
        idx = e.control.selected_index
        routes = ["home", "chat", "calendar", "handover", "closing", "voice", "store_info"]
        route = routes[idx] if idx < len(routes) else "home"
        await navigate_to(route)

    async def cleanup_page():
        """Robustly closes all open overlays (dialogs, sheets, banners)."""
        try:
            # Traditional properties
            if hasattr(page, "dialog") and page.dialog:
                page.dialog.open = False
            if hasattr(page, "bottom_sheet") and page.bottom_sheet:
                page.bottom_sheet.open = False
            if hasattr(page, "banner") and page.banner:
                page.banner.open = False
            
            # Standard way to close dialogs in newer Flet
            # This handles dialogs opened via page.open(dlg)
            for ctrl in page.overlay:
                if hasattr(ctrl, "open") and not isinstance(ctrl, (ft.FilePicker, ft.AudioRecorder)):
                    ctrl.open = False
            
            # Reset splash
            if getattr(page, "splash", None):
                page.splash = None
            
            page.update()
        except Exception as e:
            from utils.logger import log_error
            log_error(f"Cleanup Error: {e}")

    async def navigate_to(route, is_back=False):
        try:
            # Prevent redundant navigation to same route
            if page.route == route and page.controls:
                return

            log_info(f"Navigating to: {route} (Back: {is_back})")
            # print(f"DEBUG: Navigating to {route}")

            # [CRITICAL] Close all dialogs/overlays before leaving
            await cleanup_page()

            # History Management
            if not is_back and page.route:
                page.history_stack.append(page.route)

            # If navigating to a root distinct from stack, we might want to clear stack or handle differently.
            # For simple back behavior, just appending is fine for now.
            # Root pages (bottom nav) typically act as fresh start points or parallel stacks.
            # For simplicity in this request: 
            if route in ["home", "chat", "order", "closing", "calendar"]:
                pass

            page.route = route
            page.clean()

            # Reset splash if it was lingering
            if getattr(page, "splash", None):
                page.splash = None

            # Hide Nav Bar on Auth Pages
            page.drawer = None
            if route in ["login", "signup", "create_profile", "edit_profile", "/"]:
                if page.navigation_bar:
                    page.navigation_bar.visible = False
                page.history_stack.clear() # Clear history on logout/login
            else:
                if page.navigation_bar:
                    page.navigation_bar.visible = True
                    mapping = {
                        "home": 0, 
                        "chat": 1, 
                        "calendar": 2, 
                        "handover": 3, 
                        "closing": 4, 
                        "voice": 5, 
                        "order": 5, # Map order to voice tab for now if needed, or separate. 
                        "store_info": 6,
                        "store_manage": 6
                    }
                    page.navigation_bar.selected_index = mapping.get(route)

            controls = []
            # [FIX] Robust Route Matching (ignore leading slashes)
            clean_route = route.lstrip('/') if route != '/' and route.lstrip('/') else route
            if route == "/": clean_route = "/"

            # 모든 get_*_controls 함수에 await 확실히 적용
            if clean_route in ["login", "/"]:
                controls = await get_login_controls(page, navigate_to)
            elif clean_route == "signup":
                controls = await get_signup_controls(page, navigate_to)
            elif clean_route == "onboarding":
                controls = await get_onboarding_controls(page, navigate_to)
            elif clean_route == "create_profile":
                uid = page.app_session.get("user_id")
                email = page.app_session.get("user_email") or "unknown@example.com"
                controls = await get_create_profile_controls(page, navigate_to, uid, email)
            elif clean_route == "edit_profile":
                controls = await get_profile_edit_controls(page, navigate_to)
            elif clean_route == "home":
                controls = await get_home_controls(page, navigate_to)
            elif clean_route == "chat":
                controls = await get_chat_controls(page, navigate_to)
            elif clean_route == "calendar":
                controls = await get_calendar_controls(page, navigate_to)
            elif clean_route in ["voice", "order"]:
                from views.voice_view import get_voice_controls
                controls = await get_voice_controls(page, navigate_to)
            elif clean_route == "closing":
                controls = await get_closing_controls(page, navigate_to)
            elif clean_route == "work":
                controls = await get_work_controls(page, navigate_to)
            elif clean_route in ["store_info", "store_manage"]:
                controls = await get_store_manage_controls(page, navigate_to)
            elif clean_route == "profile":
                from views.profile_view import get_profile_controls
                controls = await get_profile_controls(page, navigate_to)
            elif clean_route == "debug_upload":
                from views.debug_upload_view import DebugUploadView
                controls = await DebugUploadView(page)
            elif clean_route == "handover":
                controls = await get_handover_controls(page, navigate_to)
            else:
                controls = [ft.Text(f"Page {route} not found", size=20)]

            # 방어 코드: controls가 coroutine이면 에러 출력
            import asyncio
            if asyncio.iscoroutine(controls):
                raise RuntimeError(f"controls is coroutine! Did you forget 'await'? Route: {route}")

            # Critical: If route changed during control generation (e.g. auto-login), stop here.
            if page.route != route:
                return

            if controls:
                page.add(*controls)
            page.update()

        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            log_error(f"Navigation Error ({route}): {err_msg}")
            page.clean()
            page.add(ft.Text(f"시스템 오류: {e}", color="red", weight="bold"))

            async def retry_nav(ev):
                await navigate_to("login")

            page.add(ft.Button(content=ft.Text("재시도"), on_click=retry_nav))
            page.update()

    async def go_back(e=None):
        if page.history_stack:
            prev_route = page.history_stack.pop()
            await navigate_to(prev_route, is_back=True)
            # navigate_to appends next route, so we passed is_back=True to avoid re-appending the one we are leaving (which is current).
            # Wait, navigate_to logic: "if not is_back and page.route: stack.append(page.route)"
            # If we are at C (stack [A, B]), go_back pops B.
            # navigate_to(B, is_back=True).
            # page.route was C. Stack is [A].
            # New route B.
            # Correct.
        else:
            # If no history, maybe go Home?
            if page.route != "home":
                await navigate_to("home", is_back=True)

    page.go_back = go_back
    
    # print("DEBUG: Calling initial navigate_to('login')")
    await navigate_to("login")

if __name__ == "__main__":
    import os
    import asyncio
    import flet as ft
    # Ensure upload directory exists for Proxy Uploads
    os.makedirs("uploads", exist_ok=True)

    # 클라우드 환경(Render 등)에서 제공하는 PORT 변수를 우선 사용합니다.
    port = int(os.getenv("PORT", 8555))
    host = "0.0.0.0"
    # Secure Uploads require a Secret Key
    # [SECURITY FIX] 하드코딩된 기본값 제거 - 환경변수 필수 또는 안전한 랜덤 키 생성
    secret_key = os.getenv("FLET_SECRET_KEY")
    if not secret_key:
        import secrets
        secret_key = secrets.token_hex(32)
        print("WARNING: FLET_SECRET_KEY not set. Generated temporary key (will change on restart).")
    os.environ["FLET_SECRET_KEY"] = secret_key

    # flet 0.80.x 이상: asyncio.run + app_async 구조로 실행
    try:
        ft.app(
            target=main,
            port=port,
            host=host,
            assets_dir="assets",
            upload_dir="uploads",
            view=ft.AppView.WEB_BROWSER
        )
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
