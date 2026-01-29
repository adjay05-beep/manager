import flet as ft
from services.auth_service import auth_service
from services.channel_service import channel_service
from db import service_supabase
from utils.logger import log_debug, log_error
from views.styles import AppColors, AppTextStyles, AppLayout

def get_home_controls(page: ft.Page, navigate_to):
    log_debug(f"Entering Home View. User: {page.session.get('user_id')}")
    user_id = page.session.get("user_id")
    channel_id = page.session.get("channel_id")
    
    if not user_id or not channel_id:
        navigate_to("login")
        return []

    # Fetch user's role in current channel
    role = channel_service.get_channel_role(channel_id, user_id)
    
    
    # Fetch user display name - check session first (updated from settings), then database
    display_name = page.session.get("display_name")
    if not display_name:
        try:
            # Try to get full_name from profiles table first
            profile_data = service_supabase.table("profiles").select("full_name").eq("id", user_id).execute()
            if profile_data.data and len(profile_data.data) > 0 and profile_data.data[0].get("full_name"):
                display_name = profile_data.data[0].get("full_name")
            else:
                # Fallback to email prefix
                user_data = service_supabase.table("users").select("email").eq("id", user_id).execute()
                if user_data.data and len(user_data.data) > 0:
                    email = user_data.data[0].get("email", "")
                    display_name = email.split('@')[0] if email else "User"
                else:
                    display_name = "User"
            
            # Store in session for future use
            page.session.set("display_name", display_name)
        except Exception as e:
            log_error(f"Error fetching user name: {e}")
            print(f"Error fetching user name: {e}")
            display_name = "User"
    
    # === STORE SWITCHER ===
    # Fetch all user's channels
    # [FIX] Pass token for RLS
    from services.auth_service import auth_service
    token = auth_service.get_access_token()
    user_channels = channel_service.get_user_channels(user_id, token)
    
    # Create dropdown options
    store_options = [
        ft.dropdown.Option(key=str(ch["id"]), text=ch["name"]) 
        for ch in user_channels
    ]
    
    store_selector = ft.Dropdown(
        label="현재 매장",
        value=str(channel_id),
        options=store_options,
        width=250,
        color="#0A1929",
        border_color="#CCCCCC",
        label_style=ft.TextStyle(color="grey")
    )
    
    
    # [DEBUG] Temporary Diagnostics Button
    debug_btn = ft.TextButton("업로드 진단", on_click=lambda _: navigate_to("debug_upload"), icon=ft.Icons.BUG_REPORT, style=ft.ButtonStyle(color="red"))
    
    def on_store_change(e):
        new_channel_id = int(store_selector.value)
        
        # Find selected channel
        selected_ch = next((ch for ch in user_channels if ch["id"] == new_channel_id), None)
        
        if selected_ch:
            # Update session
            page.session.set("channel_id", selected_ch["id"])
            page.session.set("channel_name", selected_ch["name"])
            page.session.set("user_role", selected_ch["role"])
            
            # Show snackbar
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✅ '{selected_ch['name']}'(으)로 전환되었습니다."),
                open=True
            )
            page.update()
            
            # Refresh home view
            navigate_to("home")
    
    store_selector.on_change = on_store_change
    
    # === ACTION BUTTON HELPER ===
    def action_btn(label, icon_path, route):
        return ft.Container(
            content=ft.Column([
                ft.Image(src=icon_path, width=80, height=80),
                ft.Text(label, weight="bold", size=14, color="#0A1929"),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=165, height=180,
            bgcolor="white",
            border_radius=25,
            on_click=lambda _: navigate_to(route),
            alignment=ft.alignment.center,
            ink=True,
            shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.05, "black")),
            border=ft.border.all(1, "white")
        )

    from db import has_service_key
    
    debug_badge = ft.Container(
        content=ft.Text(
            "Service Key: OK" if has_service_key else "Service Key: Missing (Bypass OFF)",
            size=10, color="white" if has_service_key else "orange", weight="bold"
        ),
        bgcolor=ft.Colors.with_opacity(0.1, "green" if has_service_key else "red"),
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
        border_radius=5
    )

    # === GRID LAYOUT ===
    grid = ft.Column([
        ft.Row([
            action_btn("팀 스레드", "images/icon_chat_3d.png?v=6", "chat"),
            action_btn("마감 점검", "images/icon_closing_3d.png?v=6", "closing"),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
        ft.Row([
            action_btn("음성 메모", "images/icon_voice_3d.png?v=6", "voice"),
            action_btn("캘린더", "images/icon_calendar_3d.png?v=6", "calendar"),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
    ], spacing=15)

    # RBAC: Show "직원 관리" for owners
    if role == "owner":
        grid.controls.append(
             ft.Row([
                action_btn("직원 관리", "images/icon_work_3d.png?v=6", "work"),
                action_btn("설정", "images/icon_settings_3d.png?v=6", "store_info"), 
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=15)
        )
    else:
        grid.controls.append(
            ft.Row([
                 action_btn("설정", "images/icon_settings_3d.png?v=6", "store_info"), 
            ], alignment=ft.MainAxisAlignment.CENTER)
        )

    
    # Logout handler
    def perform_logout(e):
        try:
            from services.auth_service import auth_service
            auth_service.sign_out()
            page.session.clear()
            page.client_storage.remove("supa_session")
            navigate_to("login")
        except Exception as ex:
            print(f"Logout error: {ex}")
            page.session.clear()
            navigate_to("login")

    # === ACTION BUTTON HELPER ===
    # === ACTION BUTTON HELPER ===
    def action_btn(label, icon_path, route):
        return ft.Container(
            content=ft.Column([
                ft.Image(src=icon_path, width=80, height=80),
                ft.Text(label, style=AppTextStyles.SECTION_TITLE),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            height=180,
            # Responsive Column Settings:
            # xs=6 (2 per row on mobile)
            # sm=4 (3 per row on tablet)
            # md=3 (4 per row on desktop)
            col={"xs": 6, "sm": 4, "md": 3},
            bgcolor=AppColors.SURFACE,
            border_radius=25,
            on_click=lambda _: navigate_to(route),
            alignment=ft.alignment.center,
            ink=True,
            shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.05, "black")),
            border=ft.border.all(1, AppColors.SURFACE)
        )

    # === GRID LAYOUT ===
    # Collect all items
    # [FIX] Revert to simple relative paths, REMOVE query string
    menu_items = [
        action_btn("팀 스레드", "images/icon_chat_3d.png", "chat"),
        action_btn("마감 점검", "images/icon_closing_3d.png", "closing"),
        action_btn("음성 메모", "images/icon_voice_3d.png", "voice"),
        action_btn("캘린더", "images/icon_calendar_3d.png", "calendar"),
    ]

    # RBAC: Show "직원 관리" for owners
    if role == "owner":
        menu_items.append(action_btn("직원 관리", "images/icon_work_3d.png", "work"))
    
    # Settings is for everyone
    menu_items.append(action_btn("설정", "images/icon_settings_3d.png", "store_info"))

    grid = ft.ResponsiveRow(
        controls=menu_items,
        spacing=15,
        run_spacing=15,
    )

    # [DEBUG] Set FAB for Diagnostics (Moved to Top Left to avoid obstruction)
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.BUG_REPORT, 
        bgcolor="red", 
        on_click=lambda _: navigate_to("debug_upload"),
        tooltip="업로드 진단 (개발용)"
    )
    # Move to Top Left
    page.floating_action_button_location = ft.FloatingActionButtonLocation.START_TOP

    # Layout
    return [
        ft.SafeArea(
            ft.Container(
                expand=True,
                bgcolor=AppColors.BACKGROUND,
                content=ft.Column([
                    # === HEADER WITH STORE SELECTOR ===
                    ft.Container(
                        padding=AppLayout.HEADER_PADDING,
                        bgcolor=AppColors.SURFACE,
                        border=ft.border.only(bottom=ft.border.BorderSide(1, AppColors.BORDER_LIGHT)),
                        content=ft.Row([
                            # Left: Profile Avatar + Store Info
                            ft.Row([
                                ft.Container(
                                    content=ft.Icon(ft.Icons.PERSON, color=AppColors.SURFACE, size=24),
                                    width=45, height=45, bgcolor="#E0E0E0", border_radius=22.5,
                                    alignment=ft.alignment.center,
                                    on_click=lambda _: navigate_to("profile"),
                                    tooltip="내 프로필"
                                ),
                                ft.Column([
                                    ft.Text(
                                        page.session.get("channel_name") or "매장",
                                        style=AppTextStyles.HEADER_TITLE
                                    ),
                                    ft.Text(
                                        f"{display_name}님",
                                        style=AppTextStyles.BODY_SMALL
                                    )
                                        color="grey",
                                    )
                                ], spacing=0, alignment=ft.MainAxisAlignment.CENTER),
                            ], spacing=10), # End Left Row

                        # Right: Actions
                        ft.Row([
                            ft.IconButton(
                                ft.Icons.ADD_BUSINESS,
                                icon_color="#1565C0",
                                # symbol=False,  # [FIX] Removed invalid arg
                                tooltip="새 매장 추가",
                                icon_size=35, # [FIX] Typo fixed
                                on_click=lambda _: navigate_to("onboarding"),
                                visible=True
                            ) if len(user_channels) > 1 else ft.Container(),
                            
                            ft.Container(
                                content=store_selector,
                                visible=len(user_channels) > 1,
                                width=120
                            ) if len(user_channels) > 1 else ft.IconButton(
                                ft.Icons.ADD_BUSINESS,
                                icon_color="#1565C0",
                                tooltip="새 매장 추가",
                                icon_size=35, # [FIX] 130% larger
                                on_click=lambda _: navigate_to("onboarding")
                            ),
                            
                            ft.IconButton(
                                ft.Icons.LOGOUT,
                                icon_color="#E53935",
                                tooltip="로그아웃",
                                icon_size=35, # [FIX] 130% larger
                                on_click=perform_logout
                            )
                        ], spacing=0, alignment=ft.MainAxisAlignment.END, vertical_alignment=ft.CrossAxisAlignment.START)

                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START) # [FIX] Align Tops
                ),
                
                ft.Divider(color="#EEEEEE", height=1),
                
                # === MAIN CONTENT ===
                ft.Container(
                    padding=20,
                    content=grid,
                    expand=True,
                    # Ensure grid can scroll if needed, though home screen usually fits
                    # But responsive row needs width context.
                )
            ], scroll=ft.ScrollMode.AUTO)
        ))
    ]
