import flet as ft
from services.auth_service import auth_service
from services.channel_service import channel_service
from utils.logger import log_debug, log_error
from views.styles import AppColors, AppTextStyles, AppLayout, AppGradients
from components.premium_card import PremiumCard
from db import service_supabase

def get_home_controls(page: ft.Page, navigate_to):
    log_debug(f"Entering Home View. User: {page.session.get('user_id')}")
    user_id = page.session.get("user_id")
    channel_id = page.session.get("channel_id")
    
    if not user_id or not channel_id:
        navigate_to("login")
        return []

    # Initialize Theme Mode if not set
    if page.theme_mode is None:
        page.theme_mode = ft.ThemeMode.LIGHT

    # Fetch user's role
    role = channel_service.get_channel_role(channel_id, user_id)
    display_name = page.session.get("display_name")
    
    if not display_name:
        try:
            p_res = service_supabase.table("profiles").select("full_name").eq("id", user_id).single().execute()
            if p_res.data:
                display_name = p_res.data.get("full_name")
                page.session.set("display_name", display_name)
        except Exception as e:
            log_error(f"Failed to fetch profile name: {e}")
            display_name = "User"

    display_name = display_name or "User"
    
    # Store Switcher Data
    token = auth_service.get_access_token()
    user_channels = channel_service.get_user_channels(user_id, token)
    
    store_options = [ft.dropdown.Option(key=str(ch["id"]), text=ch["name"]) for ch in user_channels]
    
    store_selector = ft.Dropdown(
        label="매장 전환",
        value=str(channel_id),
        options=store_options,
        width=140,
        text_size=12,
        dense=True,
        border_radius=AppLayout.BORDER_RADIUS_SM,
        bgcolor=AppColors.SURFACE_LIGHT if page.theme_mode == ft.ThemeMode.LIGHT else AppColors.SURFACE_DARK,
    )
    
    def on_store_change(e):
        new_cid = int(store_selector.value)
        selected = next((ch for ch in user_channels if ch["id"] == new_cid), None)
        if selected:
            page.session.set("channel_id", selected["id"])
            page.session.set("channel_name", selected["name"])
            page.session.set("user_role", selected["role"])
            page.snack_bar = ft.SnackBar(ft.Text(f"✅ '{selected['name']}'(으)로 전환되었습니다."), open=True)
            page.update()
            navigate_to("home")

    store_selector.on_change = on_store_change

    def perform_logout(e):
        auth_service.sign_out()
        page.session.clear()
        navigate_to("login")

    # === MENU ITEMS ===
    def menu_item(label, image_path=None, icon=None, route="home", color=AppColors.PRIMARY):
        icon_content = ft.Image(src=image_path, width=64, height=64) if image_path else ft.Icon(icon, size=48, color=color)
        return PremiumCard(
            content=ft.Column([
                icon_content,
                ft.Text(label, style=AppTextStyles.header(page, size=16), text_align=ft.TextAlign.CENTER),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=AppLayout.SM),
            on_click=lambda _: navigate_to(route),
        )

    items = [
        menu_item("메신저", image_path="images/icon_chat_3d.png", route="chat"),
        menu_item("캘린더", image_path="images/icon_calendar_3d.png", route="calendar"),
        # [FIX] Use string literal for icon to avoid AttributeError
        menu_item("업무 일지", icon="edit_note", route="handover", color=AppColors.PRIMARY),
        menu_item("체크리스트", image_path="images/icon_closing_3d.png", route="closing"),
        menu_item("음성 메모", image_path="images/icon_voice_3d.png", route="voice"),
        menu_item("설정", image_path="images/icon_settings_3d.png", route="store_info"),
    ]

    if role == "owner":
        items.append(menu_item("직원 관리", image_path="images/icon_work_3d.png", route="work"))

    grid = ft.ResponsiveRow(
        controls=[ft.Container(content=it, col={"xs": 6, "sm": 4, "md": 3}) for it in items],
        spacing=AppLayout.MD,
        run_spacing=AppLayout.MD,
    )

    """
    # Floating Debug
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.BUG_REPORT_ROUNDED, 
        bgcolor=AppColors.ERROR, 
        on_click=lambda _: navigate_to("debug_upload"),
        mini=True
    )
    page.floating_action_button_location = ft.FloatingActionButtonLocation.START_TOP
    """

    return [
        ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                bgcolor=AppColors.BG_LIGHT if page.theme_mode == ft.ThemeMode.LIGHT else AppColors.BG_DARK,
                content=ft.ListView(
                    controls=[
                        # --- PREMIUM HEADER ---
                        ft.Container(
                            padding=ft.padding.all(AppLayout.MD),
                            gradient=AppGradients.PRIMARY_LINEAR,
                            content=ft.Row([
                                ft.Row([
                                    ft.Container(
                                        content=ft.Icon(ft.Icons.PERSON_ROUNDED, color=AppColors.PRIMARY, size=24),
                                        width=48, height=48, bgcolor=ft.Colors.WHITE, border_radius=24,
                                        on_click=lambda _: navigate_to("profile"),
                                    ),
                                    ft.Column([
                                        ft.Text(page.session.get("channel_name") or "매장", style=ft.TextStyle(size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)),
                                        ft.Text(f"{display_name}님 반갑습니다", style=ft.TextStyle(size=12, color=ft.Colors.with_opacity(0.8, ft.Colors.WHITE))),
                                    ], spacing=0),
                                ], spacing=AppLayout.SM),
                                
                                ft.Row([
                                    store_selector if len(user_channels) > 1 else ft.Container(),
                                    ft.Container(
                                        content=ft.Column([
                                            ft.Icon(ft.Icons.LOGOUT_ROUNDED, color=ft.Colors.WHITE, size=20),
                                            ft.Text("로그아웃", size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
                                        ], spacing=0, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                        on_click=perform_logout,
                                        padding=5
                                    ),
                                ], spacing=AppLayout.XS)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        ),
                        
                        # --- MAIN CONTENT ---
                        ft.Container(
                            padding=AppLayout.MD,
                            content=grid
                        )
                    ],
                    expand=True,
                )
            )
        )
    ]
