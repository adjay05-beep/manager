import flet as ft
from views.styles import AppColors, AppTextStyles, AppLayout, AppAnimations

class ErrorBoundary(ft.Container):
    """
    A professional error display component with a retry option.
    """
    def __init__(self, message: str, retry_callback=None):
        super().__init__()
        self.expand = True
        self.alignment = ft.Alignment(0, 0)
        self.padding = AppLayout.XL
        
        self.content = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=AppLayout.MD,
            controls=[
                ft.Icon(
                    name=ft.Icons.ERROR_OUTLINE_ROUNDED,
                    color=AppColors.ERROR,
                    size=64,
                ),
                ft.Text(
                    "문제가 발생했습니다",
                    style=ft.TextStyle(size=20, weight=ft.FontWeight.BOLD),
                ),
                ft.Text(
                    message,
                    style=ft.TextStyle(color=AppColors.TEXT_MUTE),
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.ElevatedButton(
                    text="다시 시도",
                    icon=ft.Icons.REFRESH_ROUNDED,
                    color=ft.Colors.WHITE,
                    bgcolor=AppColors.PRIMARY,
                    on_click=retry_callback if retry_callback else lambda _: None,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=AppLayout.BORDER_RADIUS_MD),
                        padding=ft.padding.symmetric(horizontal=AppLayout.LG, vertical=AppLayout.MD),
                    ),
                ) if retry_callback else ft.Container()
            ]
        )
