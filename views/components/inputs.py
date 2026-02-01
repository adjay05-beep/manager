import flet as ft
from views.styles import AppColors, AppLayout, AppTextStyles

class StandardTextField(ft.TextField):
    """
    A standardized TextField with consistent styling.
    """
    def __init__(
        self,
        label: str,
        password: bool = False,
        can_reveal_password: bool = False,
        width: int = 320,
        bgcolor: str = ft.Colors.WHITE,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.label = label
        self.password = password
        self.can_reveal_password = can_reveal_password
        self.width = width
        self.bgcolor = bgcolor
        
        # Standard Styling
        self.border_radius = AppLayout.BORDER_RADIUS_MD
        self.text_size = 14
        self.color = AppColors.TEXT_MAIN
        self.label_style = ft.TextStyle(color=AppColors.TEXT_MUTE, size=14)
        self.border_color = AppColors.BORDER_LIGHT
        self.focused_border_color = AppColors.PRIMARY
        self.content_padding = 15

class StandardDropdown(ft.Dropdown):
    """
    A standardized Dropdown with consistent styling.
    """
    def __init__(
        self,
        label: str,
        options: list[ft.dropdown.Option],
        width: int = 320,
        bgcolor: str = ft.Colors.WHITE,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.label = label
        self.options = options
        self.width = width
        self.bgcolor = bgcolor
        
        # Standard Styling
        self.border_radius = AppLayout.BORDER_RADIUS_MD
        self.text_size = 14
        self.color = AppColors.TEXT_MAIN
        self.label_style = ft.TextStyle(color=AppColors.TEXT_MUTE, size=14)
        self.border_color = AppColors.BORDER_LIGHT
        self.focused_border_color = AppColors.PRIMARY
        self.content_padding = 10
