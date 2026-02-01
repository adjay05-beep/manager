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
from views.profile_view import get_profile_controls
from views.debug_upload_view import DebugUploadView

class Router:
    def __init__(self, page: ft.Page):
        self.page = page
        self.history_stack = []
        
        # Configure Navigation Bar
        self.page.navigation_bar = self._create_navigation_bar()
        self.page.on_route_change = self._handle_route_change_event
        self.page.on_view_pop = self._handle_view_pop
        
        # Helper for back button
        self.page.go_back = self.go_back

    def _create_navigation_bar(self):
        """Creates the standard navigation bar."""
        return ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label="홈"),
                ft.NavigationBarDestination(icon=ft.Icons.CHAT_BUBBLE_OUTLINE, selected_icon=ft.Icons.CHAT_BUBBLE, label="메신저"),
                ft.NavigationBarDestination(icon=ft.Icons.CALENDAR_MONTH_OUTLINED, selected_icon=ft.Icons.CALENDAR_MONTH, label="일정"),
                ft.NavigationBarDestination(icon=ft.Icons.DESCRIPTION_OUTLINED, selected_icon=ft.Icons.DESCRIPTION, label="업무일지"),
                ft.NavigationBarDestination(icon=ft.Icons.CHECK_CIRCLE_OUTLINE, selected_icon=ft.Icons.CHECK_CIRCLE, label="마감"),
                ft.NavigationBarDestination(icon=ft.Icons.MIC_NONE, selected_icon=ft.Icons.MIC, label="음성"),
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
        routes = ["home", "chat", "calendar", "handover", "closing", "voice", "store_info"]
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
            
            page.update()
        except Exception as e:
            log_error(f"Cleanup Error: {e}")

    async def start(self):
        """Initial startup logic."""
        await self.navigate_to("login")

    async def go_back(self, e=None):
        """Navigates to the previous route in history."""
        if self.history_stack:
            prev_route = self.history_stack.pop()
            await self.navigate_to(prev_route, is_back=True)
        else:
            if self.page.route != "home":
                await self.navigate_to("home", is_back=True)

    async def navigate_to(self, route, is_back=False):
        """
        Main navigation logic.
        Args:
            route (str): Target route name (e.g., "home", "chat").
            is_back (bool): True if this is a 'back' navigation (prevents circular history).
        """
        page = self.page
        try:
            if page.route == route and page.controls:
                return

            log_info(f"Navigating to: {route} (Back: {is_back})")
            
            # 1. Cleanup Overlays
            await self.cleanup_overlays()

            # 2. History Management
            if not is_back and page.route:
                # Add current route to stack before moving, unless we are just going back
                # or if it's a login/logout transition where history should be cleared.
                if route not in ["login", "/"]: # Don't stack login pages
                     page.history_stack.append(page.route)
                     # Sync local stack logic if needed, but page.history_stack is what main.py used.
                     # We can sync it to self.history_stack if we want to move completely away from page prop.
                     self.history_stack = page.history_stack 

            # 3. Update Route State
            page.route = route
            page.clean()

            # 4. Handle Navbar & Special UI States
            page.drawer = None # Reset drawer
            if route in ["login", "signup", "create_profile", "edit_profile", "/"]:
                if page.navigation_bar:
                    page.navigation_bar.visible = False
                page.history_stack.clear()
                self.history_stack.clear()
            else:
                if page.navigation_bar:
                    page.navigation_bar.visible = True
                    mapping = {
                        "home": 0, "chat": 1, "calendar": 2, "handover": 3, 
                        "closing": 4, "voice": 5, "order": 5, 
                        "store_info": 6, "store_manage": 6
                    }
                    # Update selected index without triggering event
                    page.navigation_bar.selected_index = mapping.get(route, 0)

            # 5. Route Matching & Control Generation
            clean_route = route.lstrip('/') if route != '/' and route.lstrip('/') else route
            if route == "/": clean_route = "/"
            
            controls = []
            
            # Route Map
            if clean_route in ["login", "/"]:
                controls = await get_login_controls(page, self.navigate_to)
            elif clean_route == "signup":
                controls = await get_signup_controls(page, self.navigate_to)
            elif clean_route == "onboarding":
                controls = await get_onboarding_controls(page, self.navigate_to)
            elif clean_route == "create_profile":
                uid = page.app_session.get("user_id")
                email = page.app_session.get("user_email") or "unknown@example.com"
                controls = await get_create_profile_controls(page, self.navigate_to, uid, email)
            elif clean_route == "edit_profile":
                controls = await get_profile_edit_controls(page, self.navigate_to)
            elif clean_route == "home":
                controls = await get_home_controls(page, self.navigate_to)
            elif clean_route == "chat":
                controls = await get_chat_controls(page, self.navigate_to)
            elif clean_route == "calendar":
                controls = await get_calendar_controls(page, self.navigate_to)
            elif clean_route in ["voice", "order"]:
                controls = await get_voice_controls(page, self.navigate_to)
            elif clean_route == "closing":
                controls = await get_closing_controls(page, self.navigate_to)
            elif clean_route == "work":
                controls = await get_work_controls(page, self.navigate_to)
            elif clean_route in ["store_info", "store_manage"]:
                controls = await get_store_manage_controls(page, self.navigate_to)
            elif clean_route == "profile":
                controls = await get_profile_controls(page, self.navigate_to)
            elif clean_route == "debug_upload":
                controls = await DebugUploadView(page)
            elif clean_route == "handover":
                controls = await get_handover_controls(page, self.navigate_to)
            else:
                controls = [ft.Text(f"Page {route} not found", size=20)]

            # 6. Render
            # Safety check for coroutines
            import asyncio
            if asyncio.iscoroutine(controls):
                 raise RuntimeError(f"controls is coroutine! Did you forget 'await'? Route: {route}")

            # Double check route hasn't changed during await
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
            page.add(ft.Text(f"시스템 오류: {e}", color="red"))
            page.add(ft.Button("재시도(로그인)", on_click=lambda _: self.navigate_to("login")))
            page.update()
