import flet as ft
import asyncio
from services.auth_service import auth_service
from services.channel_service import channel_service
from utils.logger import log_debug, log_error
from views.styles import AppColors, AppTextStyles, AppLayout, AppGradients
from components.premium_card import PremiumCard
from db import service_supabase

async def get_home_controls(page: ft.Page, navigate_to):
    log_debug(f"Entering Home View. User: {page.app_session.get('user_id')}")
    user_id = page.app_session.get("user_id")
    channel_id = page.app_session.get("channel_id")
    
    if not user_id or not channel_id:
        await navigate_to("login")
        return []

    # Initialize Theme Mode if not set
    if page.theme_mode is None:
        page.theme_mode = ft.ThemeMode.LIGHT

    # Fetch user's role
    role = await asyncio.to_thread(lambda: channel_service.get_channel_role(channel_id, user_id))
    display_name = page.app_session.get("display_name")
    
    if not display_name:
        try:
            p_res = await asyncio.to_thread(lambda: service_supabase.table("profiles").select("full_name").eq("id", user_id).single().execute())
            if p_res.data:
                display_name = p_res.data.get("full_name")
                page.app_session["display_name"] = display_name
        except Exception as e:
            log_error(f"Failed to fetch profile name: {e}")
            display_name = "User"

    display_name = display_name or "User"
    
    # Store Switcher Data
    token = auth_service.get_access_token()
    user_channels = await asyncio.to_thread(lambda: channel_service.get_user_channels(user_id, token))
    
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
    
    async def on_store_change(e):
        new_cid = int(store_selector.value)
        selected = next((ch for ch in user_channels if ch["id"] == new_cid), None)
        if selected:
            page.app_session["channel_id"] = selected["id"]
            page.app_session["channel_name"] = selected["name"]
            page.app_session["user_role"] = selected["role"]
            page.open(ft.SnackBar(ft.Text(f"✅ '{selected['name']}'(으)로 전환되었습니다.")))
            page.update()
            await navigate_to("home")

    store_selector.on_change = on_store_change

    async def perform_logout(e):
        await asyncio.to_thread(auth_service.sign_out)
        # Clear app_session dict
        page.app_session.clear()
        await navigate_to("login")

    # === MENU ITEMS ===
    # Flet 0.80+: Create async handlers for each menu item
    async def go_to_chat(e): await navigate_to("chat")
    async def go_to_calendar(e): await navigate_to("calendar")
    async def go_to_handover(e): await navigate_to("handover")
    async def go_to_closing(e): await navigate_to("closing")
    async def go_to_voice(e): await navigate_to("voice")
    async def go_to_store_info(e): await navigate_to("store_info")
    async def go_to_work(e): await navigate_to("work")
    async def go_to_attendance(e): await navigate_to("attendance")
    async def go_to_profile(e): await navigate_to("profile")

    def menu_item(label, image_path=None, icon=None, handler=None, color=AppColors.PRIMARY):
        icon_content = ft.Image(src=image_path, width=64, height=64) if image_path else ft.Icon(icon, size=48, color=color)
        # Wrap async handler with lambda + asyncio.create_task for Flet 0.80+
        wrapped_handler = (lambda e, h=handler: asyncio.create_task(h(e))) if handler else None
        return PremiumCard(
            content=ft.Column([
                icon_content,
                ft.Text(label, style=AppTextStyles.header(page, size=16), text_align=ft.TextAlign.CENTER),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=AppLayout.SM),
            on_click=wrapped_handler,
        )

    items = [
        menu_item("메신저", image_path="images/icon_chat_3d.png", handler=go_to_chat),
        menu_item("캘린더", image_path="images/icon_calendar_3d.png", handler=go_to_calendar),
        menu_item("업무 일지", image_path="images/icon_handover_3d_v5.png", handler=go_to_handover),
        menu_item("체크리스트", image_path="images/icon_closing_3d.png", handler=go_to_closing),
        # menu_item("음성 메모", image_path="images/icon_voice_3d.png", handler=go_to_voice),
        menu_item("출퇴근", icon=ft.Icons.TIMER_OUTLINED, handler=go_to_attendance),
        menu_item("설정", image_path="images/icon_settings_3d.png", handler=go_to_store_info),
    ]

    if role == "owner":
        items.append(menu_item("직원 관리", image_path="images/icon_work_3d.png", handler=go_to_work))

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
                                        on_click=lambda e: asyncio.create_task(go_to_profile(e)),
                                    ),
                                    ft.Column([
                                        ft.Text(page.app_session.get("channel_name") or "매장", style=ft.TextStyle(size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)),
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
                                        on_click=lambda e: asyncio.create_task(perform_logout(e)),
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
