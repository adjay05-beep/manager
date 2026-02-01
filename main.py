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

def main(page: ft.Page):
    page.title = "The Manager"
    # page.window_width = 390
    # page.window_height = 844
    
    # [THEME PERSISTENCE] Load theme from client_storage
    theme_mode_str = page.client_storage.get("theme_mode")
    if theme_mode_str == "dark":
        page.theme_mode = ft.ThemeMode.DARK
    else:
        page.theme_mode = ft.ThemeMode.LIGHT
    
    page.padding = 0
    page.spacing = 0
    # page.bgcolor = "white" # [REMOVED] Let theme control bgcolor (white/dark)
    
    # Global FilePicker for all views
    page.file_picker = ft.FilePicker()
    page.overlay.append(page.file_picker)

    # Global Chat FilePicker (Prevent Chat Layout Freeze)
    page.chat_file_picker = ft.FilePicker()
    page.overlay.append(page.chat_file_picker)

    # Global AudioRecorder for voice memos
    page.audio_recorder = ft.AudioRecorder()
    page.overlay.append(page.audio_recorder)
    
    
    # Persistent Navigation Bar
    # The on_nav_change function is now integrated into the NavigationBar's on_change property
    # and will be dynamically updated in navigate_to.

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
        on_change=lambda e: navigate_to(
            "home" if e.control.selected_index == 0 else
            "chat" if e.control.selected_index == 1 else
            "calendar" if e.control.selected_index == 2 else
            "handover" if e.control.selected_index == 3 else
            "closing" if e.control.selected_index == 4 else
            "voice" if e.control.selected_index == 5 else
            "store_info"
        ),
        bgcolor="white",
        indicator_color="#E3F2FD",
        shadow_color="black",
        elevation=5
    )

    # Optimized Route Management
    page.history_stack = []

    def cleanup_page():
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

    def navigate_to(route, is_back=False):
        # Prevent redundant navigation to same route
        if page.route == route and page.controls:
             return
             
        log_info(f"Navigating to: {route} (Back: {is_back})")
        
        # [CRITICAL] Close all dialogs/overlays before leaving
        cleanup_page()

        # History Management
        if not is_back and page.route:
            page.history_stack.append(page.route)
        
        # If navigating to a root distinct from stack, we might want to clear stack or handle differently.
        # For simple back behavior, just appending is fine for now.
        # Root pages (bottom nav) typically act as fresh start points or parallel stacks.
        # For simplicity in this request: 
        if route in ["home", "chat", "order", "closing", "calendar"]:
             # If jumping between main tabs, maybe clear stack? 
             # Standard behavior depends on app. Let's keep stack linear for now unless it grows too large.
             # User requested "Back button on all pages", implying linear history flow or sub-pages.
             # If I go Home -> Profile -> Back, I expect Home.
             pass

        page.route = route
        page.clean()
        
        # Reset splash if it was lingering
        # (Already handled in cleanup_page but good as backup)
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
                # Sync Nav Bar State
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

        try:
            controls = []
            # [FIX] Robust Route Matching (ignore leading slashes)
            clean_route = route.lstrip('/') if route != '/' and route.lstrip('/') else route
            # Handle empty string case if route was "/" -> clean_route "/"
            if route == "/": clean_route = "/"
            
            # Log normalized route for debugging
            # log_info(f"Route: {route} -> Clean: {clean_route}")

            controls = []
            if clean_route in ["login", "/"]:
                controls = get_login_controls(page, navigate_to)
            elif clean_route == "signup":
                controls = get_signup_controls(page, navigate_to)
            elif clean_route == "onboarding":
                controls = get_onboarding_controls(page, navigate_to)
            elif clean_route == "create_profile":
                uid = page.session.get("user_id")
                email = page.session.get("user_email") or "unknown@example.com"
                controls = get_create_profile_controls(page, navigate_to, uid, email)
            elif clean_route == "edit_profile":
                controls = get_profile_edit_controls(page, navigate_to)
            elif clean_route == "home":
                controls = get_home_controls(page, navigate_to)
            elif clean_route == "chat":
                controls = get_chat_controls(page, navigate_to)
            elif clean_route == "calendar":
                controls = get_calendar_controls(page, navigate_to)
            elif clean_route in ["voice", "order"]:
                from views.voice_view import get_voice_controls
                controls = get_voice_controls(page, navigate_to)
            elif clean_route == "closing":
                controls = get_closing_controls(page, navigate_to)
            elif clean_route == "work":
                controls = get_work_controls(page, navigate_to)
            elif clean_route in ["store_info", "store_manage"]:
                controls = get_store_manage_controls(page, navigate_to)
            elif clean_route == "profile":
                from views.profile_view import get_profile_controls
                controls = get_profile_controls(page, navigate_to)
            elif clean_route == "debug_upload":
                from views.debug_upload_view import DebugUploadView
                controls = DebugUploadView(page)
            elif clean_route == "handover":
                controls = get_handover_controls(page, navigate_to)
            else:
                controls = [ft.Text(f"Page {route} not found", size=20)]
            
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
            page.add(ft.Text(f"시스템 고침이 필요합니다: {e}", color="red", weight="bold"))
            page.add(ft.ElevatedButton("재시도", on_click=lambda _: navigate_to("login")))
            page.update()

    def go_back(e=None):
        if page.history_stack:
            prev_route = page.history_stack.pop()
            navigate_to(prev_route, is_back=True)
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
                navigate_to("home", is_back=True)

    page.go_back = go_back
    
    navigate_to("login")

if __name__ == "__main__":
    import os
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

    # 브라우저 실행 모드로 명시적 설정
    ft.app(target=main, port=port, host=host, assets_dir="assets", upload_dir="uploads", view=ft.AppView.WEB_BROWSER, web_renderer="html")
