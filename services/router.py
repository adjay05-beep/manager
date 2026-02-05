import flet as ft
from utils.logger import log_error, log_info

# View Imports
# Importing here to map routes. 
# Using conditional/lazy imports inside methods can avoid circular dependency if those views import router, 
# but generally views shouldn't import router directly (they accept callbacks).
from views.login_view import get_login_controls
from views.home_view import get_home_controls
from views.chat_view import get_chat_controls
from views.calendar_view import get_calendar_controls
from views.order_view import get_order_controls
from views.closing_view import get_closing_controls
from views.signup_view import get_signup_controls
from views.create_profile_view import get_create_profile_controls
from views.work_view import get_work_controls
from views.profile_edit_view import get_profile_edit_controls
from views.onboarding_view import get_onboarding_controls
from views.store_manage_view import get_store_manage_controls
from views.handover_view import get_handover_controls
from views.voice_view import get_voice_controls
from views.attendance_view import get_attendance_controls
from views.profile_view import get_profile_controls
from views.debug_upload_view import DebugUploadView
from views.gps_test_view import get_gps_test_controls

class Router:
    def __init__(self, page: ft.Page):
        print("DEBUG: Router.__init__ start")
        self.page = page
        self.history_stack = []
        
        # Configure Navigation Bar
        print("DEBUG: Creating navigation bar")
        self.page.navigation_bar = self._create_navigation_bar()
        self.page.on_route_change = self._handle_route_change_event
        self.page.on_view_pop = self._handle_view_pop
        
        # Helper for back button
        self.page.go_back = self.go_back
        print("DEBUG: Router.__init__ complete")

    def _create_navigation_bar(self):
        """Creates the standard navigation bar."""
        return ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label="홈"),
                ft.NavigationBarDestination(icon=ft.Icons.CHAT_BUBBLE_OUTLINE, selected_icon=ft.Icons.CHAT_BUBBLE, label="메신저"),
                ft.NavigationBarDestination(icon=ft.Icons.CALENDAR_MONTH_OUTLINED, selected_icon=ft.Icons.CALENDAR_MONTH, label="일정"),
                ft.NavigationBarDestination(icon=ft.Icons.DESCRIPTION_OUTLINED, selected_icon=ft.Icons.DESCRIPTION, label="업무일지"),
                ft.NavigationBarDestination(icon=ft.Icons.CHECK_CIRCLE_OUTLINE, selected_icon=ft.Icons.CHECK_CIRCLE, label="마감"),
                # ft.NavigationBarDestination(icon=ft.Icons.MIC_NONE, selected_icon=ft.Icons.MIC, label="음성"),
                ft.NavigationBarDestination(icon=ft.Icons.TIMER_OUTLINED, selected_icon=ft.Icons.TIMER, label="출퇴근"),
                ft.NavigationBarDestination(icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS, label="설정"),
            ],
            on_change=lambda e: self.page.run_task(self._on_nav_bar_change, e),
            bgcolor="white",
            indicator_color="#E3F2FD",
            shadow_color="black",
            elevation=5
        )

    async def _on_nav_bar_change(self, e):
        """Handles clicks on the navigation bar."""
        idx = e.control.selected_index
        routes = ["home", "chat", "calendar", "handover", "closing", "attendance", "store_info"]
        route = routes[idx] if idx < len(routes) else "home"
        await self.navigate_to(route)

    async def _handle_route_change_event(self, e):
        """Flet's native route change handler (if page.go is used)."""
        # We primarily use navigate_to, but this catches external or basic page.go calls
        # For now, we rely on navigate_to explicit calls, but this can be expanded.
        pass

    async def _handle_view_pop(self, view):
        """Handle browser back button or view pop."""
        await self.go_back()

    async def cleanup_overlays(self):
        """Closes all open dialogs, bottom sheets, and banners."""
        try:
            print("DEBUG: Cleaning up overlays")
            page = self.page
            if hasattr(page, "dialog") and page.dialog:
                page.dialog.open = False
            if hasattr(page, "bottom_sheet") and page.bottom_sheet:
                page.bottom_sheet.open = False
            if hasattr(page, "banner") and page.banner:
                page.banner.open = False
            
            # Close overlay controls
            for ctrl in page.overlay:
                if hasattr(ctrl, "open") and not isinstance(ctrl, (ft.FilePicker, ft.AudioRecorder)):
                    ctrl.open = False
            
            # Reset splash
            if getattr(page, "splash", None):
                page.splash = None

            # [FIX] Clear Drawer to prevent ghost references
            if getattr(page, "drawer", None):
                page.drawer = None
            
            page.update()
        except Exception as e:
            log_error(f"Cleanup Error: {e}")

    async def start(self):
        """Initial startup logic."""
        print("DEBUG: Router.start called")
        await self.navigate_to("login")

    async def go_back(self, e=None):
        """Navigates to the previous route in history."""
        if self.history_stack:
            prev_route = self.history_stack.pop()
            await self.navigate_to(prev_route, is_back=True)
        else:
            if self.page.route != "home":
                await self.navigate_to("home", is_back=True)

    async def navigate_to(self, route, is_back=False, add_to_history=True):
        """
        Main navigation logic.
        Args:
            route (str): Target route name (e.g., "home", "chat").
            is_back (bool): True if this is a 'back' navigation (prevents circular history).
            add_to_history (bool): Whether to add current route to history stack.
        """
        page = self.page
        try:
            if page.route == route and page.controls:
                return

            log_info(f"Navigating to: {route} (Back: {is_back})")
            
            # 1. Cleanup Overlays
            await self.cleanup_overlays()
            print(f"DEBUG: Overlay cleanup complete")

            # 2. History Management
            clean_route = route.lstrip("/")
            
            if add_to_history and not is_back and page.route and page.route != clean_route:
                # Add current route to stack before moving
                if route not in ["login", "/"]:  # Don't stack login pages
                    self.history_stack.append(page.route)
                    print(f"DEBUG: Added '{page.route}' to history. Current stack: {self.history_stack}")

            # 3. Update Route State
            page.route = clean_route
            page.clean()
            
            # Public routes
            public_routes = ["login", "signup", "onboarding", "create_profile", "gps-test", "/"]
            
            print(f"DEBUG: Checking authentication for route: {clean_route}")
            # Auth Check
            if clean_route not in public_routes:
                user_id = page.app_session.get("user_id")
                channel_id = page.app_session.get("channel_id")
                print(f"DEBUG: Auth check - user_id={user_id}, channel_id={channel_id}")
                if not user_id:
                    print(f"DEBUG: No user_id, redirecting to login")
                    page.controls.clear()
                    # Lazy import to avoid circular dependency if login_view imports router
                    from views.login_view import get_login_controls 
                    page.controls = await get_login_controls(page, self.navigate_to)
                    page.update()
                    return
            
            controls = []
            
            print(f"DEBUG: About to load view for route: {clean_route}")
            # Route Map
            if clean_route in ["login", "/"]:
                print(f"DEBUG: Loading login view")
                from views.login_view import get_login_controls
                controls = await get_login_controls(page, self.navigate_to)
                print(f"DEBUG: Login view loaded, controls count: {len(controls)}")
            elif clean_route == "signup":
                print(f"DEBUG: Loading signup view")
                from views.signup_view import get_signup_controls
                controls = await get_signup_controls(page, self.navigate_to)
                print(f"DEBUG: Signup view loaded, controls count: {len(controls)}")
            elif clean_route == "onboarding":
                print(f"DEBUG: Loading onboarding view")
                from views.onboarding_view import get_onboarding_controls
                controls = await get_onboarding_controls(page, self.navigate_to)
                print(f"DEBUG: Onboarding view loaded, controls count: {len(controls)}")
            elif clean_route == "create_profile":
                print(f"DEBUG: Loading create_profile view")
                from views.create_profile_view import get_create_profile_controls
                uid = page.app_session.get("user_id")
                email = page.app_session.get("user_email") or "unknown@example.com"
                controls = await get_create_profile_controls(page, self.navigate_to, uid, email)
                print(f"DEBUG: Create_profile view loaded, controls count: {len(controls)}")
            elif clean_route == "edit_profile":
                print(f"DEBUG: Loading edit_profile view")
                from views.profile_edit_view import get_profile_edit_controls
                controls = await get_profile_edit_controls(page, self.navigate_to)
                print(f"DEBUG: Edit_profile view loaded, controls count: {len(controls)}")
            elif clean_route == "home":
                print(f"DEBUG: Loading home view")
                from views.home_view import get_home_controls
                controls = await get_home_controls(page, self.navigate_to)
                print(f"DEBUG: Home view loaded, controls count: {len(controls)}")
            elif clean_route == "chat":
                print(f"DEBUG: Loading chat view")
                from views.chat_view import get_chat_controls
                controls = await get_chat_controls(page, self.navigate_to)
                print(f"DEBUG: Chat view loaded, controls count: {len(controls)}")
            elif clean_route == "calendar":
                print(f"DEBUG: Loading calendar view")
                from views.calendar_view import get_calendar_controls
                controls = await get_calendar_controls(page, self.navigate_to)
                print(f"DEBUG: Calendar view loaded, controls count: {len(controls)}")
            elif clean_route in ["voice", "order"]:
                print(f"DEBUG: Loading voice/order view")
                from views.voice_view import get_voice_controls
                controls = await get_voice_controls(page, self.navigate_to)
                print(f"DEBUG: Voice/order view loaded, controls count: {len(controls)}")
            elif clean_route == "closing":
                print(f"DEBUG: Loading closing view")
                from views.closing_view import get_closing_controls
                controls = await get_closing_controls(page, self.navigate_to)
                print(f"DEBUG: Closing view loaded, controls count: {len(controls)}")
            elif clean_route == "work":
                print(f"DEBUG: Loading work view")
                from views.work_view import get_work_controls
                controls = await get_work_controls(page, self.navigate_to)
                print(f"DEBUG: Work view loaded, controls count: {len(controls)}")
            elif clean_route in ["store_info", "store_manage"]:
                print(f"DEBUG: Loading store_info/store_manage view")
                from views.store_manage_view import get_store_manage_controls
                controls = await get_store_manage_controls(page, self.navigate_to)
                print(f"DEBUG: Store_info/store_manage view loaded, controls count: {len(controls)}")
            elif clean_route == "profile":
                print(f"DEBUG: Loading profile view")
                from views.profile_view import get_profile_controls
                controls = await get_profile_controls(page, self.navigate_to)
                print(f"DEBUG: Profile view loaded, controls count: {len(controls)}")
            elif clean_route == "debug_upload":
                print(f"DEBUG: Loading debug_upload view")
                from views.debug_upload_view import DebugUploadView
                controls = await DebugUploadView(page)
                print(f"DEBUG: Debug_upload view loaded, controls count: {len(controls)}")
            elif clean_route == "handover":
                print(f"DEBUG: Loading handover view")
                from views.handover_view import get_handover_controls
                controls = await get_handover_controls(page, self.navigate_to)
                print(f"DEBUG: Handover view loaded, controls count: {len(controls)}")
            elif clean_route == "attendance":
                print(f"DEBUG: Loading attendance view")
                from views.attendance_view import get_attendance_controls
                controls = await get_attendance_controls(page, self.navigate_to)
                print(f"DEBUG: Attendance view loaded, controls count: {len(controls)}")
            elif clean_route == "gps-test":
                print(f"DEBUG: Loading gps-test view")
                from views.gps_test_view import get_gps_test_controls
                controls = await get_gps_test_controls(page, self.navigate_to)
                print(f"DEBUG: GPS test view loaded, controls count: {len(controls)}")
            else:
                print(f"DEBUG: Route '{clean_route}' not found, showing default message")
                controls = [ft.Text(f"Page {route} not found", size=20)]
            
            print(f"DEBUG: View loaded, updating page controls")
            # Set Navigation Bar Visibility
            if clean_route in ["login", "signup", "onboarding", "create_profile", "edit_profile", "/"]:
                if page.navigation_bar:
                    page.navigation_bar.visible = False
                    print(f"DEBUG: Navigation bar hidden for route: {clean_route}")
            else:
                if page.navigation_bar:
                    page.navigation_bar.visible = True
                    mapping = {
                        "home": 0, "chat": 1, "calendar": 2, "handover": 3, 
                        "closing": 4, "attendance": 5, "store_info": 6, "store_manage": 6
                    }
                    page.navigation_bar.selected_index = mapping.get(clean_route, 0)
                    print(f"DEBUG: Navigation bar visible and index set for route: {clean_route}")
            
            # Update Page
            page.controls.clear()
            page.controls.extend(controls) # Use extend instead of direct assignment for consistency
            page.route = clean_route # Update page.route after controls are set
            print(f"DEBUG: Calling page.update()")
            page.update()
            print(f"DEBUG: Navigation complete for route: {clean_route}")
            
        except Exception as e:
            print(f"DEBUG ERROR in navigate_to: {e}")
            import traceback
            err_msg = traceback.format_exc()
            log_error(f"Navigation Error ({route}): {err_msg}")
            page.controls.clear()
            page.add(ft.Text(f"시스템 오류: {e}", color="red"))
            page.add(ft.ElevatedButton("재시도(로그인)", on_click=lambda _: self.navigate_to("login")))
            page.update()
