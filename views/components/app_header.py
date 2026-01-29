import flet as ft
from views.styles import AppColors, AppTextStyles, AppLayout

def AppHeader(title_text: str, on_back_click=None, action_button: ft.Control = None, back_button_visible: bool = True):
    """
    Standard Application Header.
    """
    
    # Left Content: Back Button or Spacer
    left_content = ft.Container(width=40)
    if back_button_visible and on_back_click:
        left_content = ft.IconButton(
            ft.Icons.ARROW_BACK_IOS_NEW, 
            icon_color=AppColors.TEXT_PRIMARY, 
            on_click=on_back_click,
            tooltip="뒤로가기"
        )
    
    # Right Content: Action Button or Spacer
    right_content = action_button if action_button else ft.Container(width=40)

    header_row = ft.Row([
        left_content,
        ft.Text(title_text, style=AppTextStyles.HEADER_TITLE, color=AppColors.TEXT_PRIMARY),
        right_content
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    return ft.Container(
        content=header_row,
        padding=AppLayout.HEADER_PADDING,
        bgcolor=AppColors.SURFACE,
        border=ft.border.only(bottom=ft.border.BorderSide(1, AppColors.BORDER_LIGHT)),
        height=60 # Fixed height for consistency
    )
