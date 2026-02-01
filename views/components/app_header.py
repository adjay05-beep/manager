import flet as ft
from typing import Union, List
from views.styles import AppColors, AppTextStyles, AppLayout

def AppHeader(
    title_text: Union[str, ft.Control], 
    on_back_click=None, 
    action_button: ft.Control = None, 
    back_button_visible: bool = True,
    left_button: ft.Control = None # For custom left side (e.g. Menu + Back)
):
    """
    Standard Application Header with guaranteed center alignment for Title.
    """
    
    # Left Content
    if left_button:
        left_side = left_button
    else:
        left_side = ft.Container(width=48)
        if back_button_visible and on_back_click:
            left_side = ft.IconButton(
                ft.Icons.ARROW_BACK_IOS_NEW, 
                icon_color=AppColors.TEXT_PRIMARY, 
                icon_size=20,
                on_click=on_back_click,
                tooltip="뒤로가기"
            )
    
    # Center Content (Title)
    if isinstance(title_text, str):
        title_ctrl = ft.Text(
            title_text, 
            style=AppTextStyles.HEADER_TITLE, 
            color=AppColors.TEXT_PRIMARY,
            text_align=ft.TextAlign.CENTER
        )
    else:
        title_ctrl = title_text

    # Right Content
    right_side = action_button if action_button else ft.Container(width=48)

    # Use Stack for perfect mathematical centering of the title
    header_content = ft.Stack([
        # Center title (Full-width background layer for perfect alignment)
        ft.Container(
            content=title_ctrl,
            alignment=ft.Alignment(0, 0),
            width=float("inf"),
            height=70
        ),
        
        # Action layer (Foreground with SpaceBetween row)
        ft.Row([
            ft.Container(left_side, padding=ft.padding.only(left=5)),
            ft.Container(right_side, padding=ft.padding.only(right=5))
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER, height=70),
    ], height=70)


    # Return standard container
    return ft.Container(
        content=header_content,
        bgcolor=AppColors.SURFACE,
        border=ft.border.only(bottom=ft.border.BorderSide(1, AppColors.BORDER_LIGHT)),
        height=70,
        alignment=ft.Alignment(0, 0) 
    )

