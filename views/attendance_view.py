import flet as ft
import asyncio
from datetime import datetime
from views.styles import AppColors, AppLayout, AppTextStyles, AppButtons, AppGradients, AppShadows
from views.components.app_header import AppHeader
from services.attendance_service import attendance_service

class SelectableCard(ft.Container):
    def __init__(self, label, icon, value, selected=False, on_change=None):
        super().__init__()
        self.label = label
        self.icon_name = icon
        self.value = value
        self.selected = selected
        self.on_change = on_change
        
        self.icon_control = ft.Icon(
            self.icon_name, 
            color="white" if self.selected else AppColors.TEXT_SECONDARY, 
            size=28
        )
        self.text_control = ft.Text(
            self.label, 
            color="white" if self.selected else AppColors.TEXT_SECONDARY, 
            size=13, 
            weight="bold"
        )
        
        self.content = ft.Column([
            self.icon_control,
            self.text_control
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8)
        
        self.width = 140
        self.height = 90
        self.border_radius = 16
        self.alignment = ft.Alignment(0, 0)  # Center alignment (Flet 0.80+ compatible)
        self.on_click = self._handle_click
        self.animate = ft.Animation(300, ft.AnimationCurve.DECELERATE)
        self._update_style()

    def _update_style(self):
        if self.selected:
            self.gradient = AppGradients.PRIMARY_LINEAR
            self.shadow = AppShadows.GLOW
            self.border = None
        else:
            self.bgcolor = ft.Colors.with_opacity(0.1, ft.Colors.GREY_400)
            self.border = ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.GREY_400))
            self.shadow = None
            self.gradient = None

    def _handle_click(self, e):
        if not self.selected:
            if self.on_change:
                self.on_change(self.value)

    def set_selected(self, selected):
        self.selected = selected
        self._update_style()
        self.icon_control.color = "white" if self.selected else AppColors.TEXT_SECONDARY
        self.text_control.color = "white" if self.selected else AppColors.TEXT_SECONDARY
        self.update()

async def get_attendance_controls(page: ft.Page, navigate_to):
    # Local State
    state = attendance_service.get_status()
    
    # UI Refs
    status_text = ft.Text(
        "출근 전" if state["status"] == "OFF" else "근무 중",
        style=ft.TextStyle(size=32, weight="bold", color="white" if state["status"] == "ON" else AppColors.TEXT_PRIMARY)
    )
    
    time_text = ft.Text(
        datetime.now().strftime("%H:%M:%S"),
        style=ft.TextStyle(size=48, weight="bold", font_family="monospace", color="white" if state["status"] == "ON" else AppColors.TEXT_PRIMARY)
    )
    
    date_text = ft.Text(
        datetime.now().strftime("%Y년 %m월 %d일"),
        style=ft.TextStyle(size=14, color="white" if state["status"] == "ON" else AppColors.TEXT_SECONDARY)
    )

    # GPS/WIFI Selection Cards
    cards = []
    
    def on_selection_change(new_val):
        attendance_service.save_settings(new_val)
        for card in cards:
            card.set_selected(card.value == new_val)

    gps_card = SelectableCard("GPS 기반", ft.Icons.LOCATION_ON_OUTLINED, "GPS", selected=(state["setting"] == "GPS"), on_change=on_selection_change)
    wifi_card = SelectableCard("와이파이(Wi-Fi)", ft.Icons.WIFI_OUTLINED, "WIFI", selected=(state["setting"] == "WIFI"), on_change=on_selection_change)
    cards.extend([gps_card, wifi_card])

    async def update_time():
        while True:
            now = datetime.now()
            time_text.value = now.strftime("%H:%M:%S")
            try:
                time_text.update()
            except:
                break
            await asyncio.sleep(1)
            
    asyncio.create_task(update_time())

    async def toggle_attendance(e):
        btn = e.control
        if state["status"] == "OFF":
            await attendance_service.clock_in(state["setting"])
            state["status"] = "ON"
            btn.text = "퇴근하기"
            btn.bgcolor = AppColors.ERROR
            status_text.value = "근무 중"
            status_card.gradient = AppGradients.PRIMARY_LINEAR
            status_card.shadow = AppShadows.GLOW
            status_text.color = "white"
            time_text.color = "white"
            date_text.color = ft.Colors.with_opacity(0.8, "white")
        else:
            await attendance_service.clock_out()
            state["status"] = "OFF"
            btn.text = "출근하기"
            btn.bgcolor = AppColors.SUCCESS
            status_text.value = "출근 전"
            status_card.gradient = None
            status_card.bgcolor = AppColors.SURFACE_LIGHT if page.theme_mode == ft.ThemeMode.LIGHT else AppColors.SURFACE_DARK
            status_card.shadow = AppShadows.MEDIUM
            status_text.color = AppColors.TEXT_PRIMARY
            time_text.color = AppColors.TEXT_PRIMARY
            date_text.color = AppColors.TEXT_SECONDARY
        
        status_card.update()
        btn.update()
        page.update()

    action_button = ft.ElevatedButton(
        "퇴근하기" if state["status"] == "ON" else "출근하기",
        bgcolor=AppColors.ERROR if state["status"] == "ON" else AppColors.SUCCESS,
        color="white",
        height=65,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=18),
            elevation=8,
            shadow_color=ft.Colors.with_opacity(0.3, "black")
        ),
        on_click=lambda e: asyncio.create_task(toggle_attendance(e))
    )

    status_card = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.AUTO_AWESOME_OUTLINED, color="white" if state["status"] == "ON" else AppColors.PRIMARY, size=20),
                ft.Text("Smart Attendance", size=12, weight="w500", color="white" if state["status"] == "ON" else AppColors.PRIMARY)
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=10),
            status_text,
            time_text,
            date_text,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
        padding=30,
        border_radius=24,
        gradient=AppGradients.PRIMARY_LINEAR if state["status"] == "ON" else None,
        bgcolor=AppColors.SURFACE_LIGHT if page.theme_mode == ft.ThemeMode.LIGHT else AppColors.SURFACE_DARK if state["status"] == "OFF" else None,
        shadow=AppShadows.GLOW if state["status"] == "ON" else AppShadows.MEDIUM,
        animate=ft.Animation(600, ft.AnimationCurve.EASE_OUT)
    )

    header = AppHeader(
        title_text="출퇴근 기록",
        on_back_click=lambda _: asyncio.create_task(navigate_to("home"))
    )

    content = ft.Column([
        header,
        ft.Container(
            padding=20,
            expand=True,
            content=ft.Column([
                status_card,
                ft.Container(height=30),
                ft.Text("인증 방식 선택", weight="bold", size=16, color=AppColors.TEXT_PRIMARY),
                ft.Container(height=10),
                ft.Row([gps_card, wifi_card], spacing=15, alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=40),
                ft.Container(
                    content=ft.Column([
                        ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=AppColors.TEXT_SECONDARY), ft.Text("안내사항", weight="bold", size=14, color=AppColors.TEXT_SECONDARY)], spacing=5),
                        ft.Text("• 반드시 매장 내에서만 출퇴근이 가능합니다.", size=12, color=AppColors.TEXT_SECONDARY),
                        ft.Text("• 위치 정보(GPS) 또는 매장 Wi-Fi 연결이 필요합니다.", size=12, color=AppColors.TEXT_SECONDARY),
                    ], spacing=8),
                    padding=15,
                    border_radius=12,
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.GREY_400)
                ),
                ft.Container(expand=True),
                ft.Container(
                    content=action_button,
                    width=float("inf"),
                    padding=ft.padding.only(bottom=10)
                )
            ], scroll=ft.ScrollMode.AUTO)
        )
    ], spacing=0, expand=True)

    return [
        ft.SafeArea(expand=True, content=content)
    ]
