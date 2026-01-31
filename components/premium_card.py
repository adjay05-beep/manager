import flet as ft
from views.styles import AppColors, AppLayout, AppShadows, AppAnimations

class PremiumCard(ft.Container):
    """
    A reusable premium card with elevation and hover animations.
    """
    def __init__(self, content, on_click=None, padding=None):
        super().__init__()
        self.content = content
        self.on_click = on_click
        self.padding = padding or AppLayout.MD
        self.border_radius = AppLayout.BORDER_RADIUS_MD
        self.bgcolor = AppColors.SURFACE_LIGHT
        self.shadow = AppShadows.SMALL
        self.animate = AppAnimations.FAST
        
        # Hover Effect
        self.on_hover = self._handle_hover

    def _handle_hover(self, e):
        self.shadow = AppShadows.MEDIUM if e.data == "true" else AppShadows.SMALL
        self.update()
