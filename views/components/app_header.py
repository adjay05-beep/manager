import flet as ft
from views.styles import AppColors, AppTextStyles, AppLayout

def AppHeader(title_text: str, on_back_click=None, action_button: ft.Control = None, back_button_visible: bool = True):
    """
    Standard Application Header.
    """
    
    # Left Content: Back Button or Spacer
    left_content = ft.Container(width=40)
    if back_button_visible:
        # Default behavior: go back if on_back_click is True or a function
        # If it's a function, use it. If it's True, use page.go_back if available.
        
        callback = None
        if callable(on_back_click):
            callback = on_back_click
        elif on_back_click is True or on_back_click is None: # Default to True behavior if just visible is True
             # We need access to page.go_back.
             # Since controls don't easily access page until added, 
             # we might need to rely on the caller passing the callback or page.
             # Ideally, the caller (view function) passes `lambda _: page.go_back()`
             pass

        # To make it simple: "on_back_click" argument is the handler.
        # If None, no handler (and maybe no button if not visible).
        
        if on_back_click:
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
        height=80, # Increased to match HomeView premium header
        alignment=ft.alignment.center # Center content vertically
    )
