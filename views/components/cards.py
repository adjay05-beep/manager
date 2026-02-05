import flet as ft
from views.styles import AppColors, AppLayout, AppShadows

class AuthCard(ft.Container):
    """
    A specific card container for Authentication forms (Login/Signup).
    Centered, shadowed, and rounded.
    """
    def __init__(self, content: ft.Control, width: int = None):
        super().__init__()
        self.content = content
        self.width = width
        
        # Standard Auth Card Styling
        self.padding = AppLayout.XL
        self.bgcolor = ft.Colors.WHITE
        self.border_radius = AppLayout.BORDER_RADIUS_LG
        self.shadow = AppShadows.MEDIUM
        self.alignment = ft.Alignment(0, 0)
