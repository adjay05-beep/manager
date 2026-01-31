import flet as ft
from views.styles import AppColors, AppLayout

class EmptyState(ft.Container):
    """
    A polished empty state component.
    """
    def __init__(self, title: str, subtitle: str, icon=ft.Icons.INBOX_ROUNDED):
        super().__init__()
        self.expand = True
        self.alignment = ft.alignment.center
        self.padding = AppLayout.XL
        
        self.content = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=AppLayout.SM,
            controls=[
                ft.Icon(
                    name=icon,
                    color=AppColors.INFO,
                    size=48,
                    opacity=0.5
                ),
                ft.Text(
                    title,
                    size=18,
                    weight=ft.FontWeight.W_600,
                    color=AppColors.INFO
                ),
                ft.Text(
                    subtitle,
                    size=14,
                    color=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
                    text_align=ft.TextAlign.CENTER
                )
            ]
        )
