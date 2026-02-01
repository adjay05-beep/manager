import flet as ft

# [PROFESSIONAL] Commercial-Grade Design System

class AppColors:
    # Essential Palette (Premium Deep Themes)
    PRIMARY = ft.Colors.BLUE_700      # Deep Professional Blue
    PRIMARY_LIGHT = ft.Colors.BLUE_400
    PRIMARY_DARK = ft.Colors.BLUE_900
    
    SECONDARY = ft.Colors.CYAN_700
    ACCENT = ft.Colors.INDIGO_ACCENT_400
    
    # Semantic Colors
    ERROR = ft.Colors.RED_ACCENT_700
    SUCCESS = ft.Colors.GREEN_700
    WARNING = ft.Colors.AMBER_700
    INFO = ft.Colors.BLUE_GREY_600

    # Neutral Palette (Sleek Light/Dark)
    BG_DARK = "#121212"
    SURFACE_DARK = "#1E1E1E"
    
    BG_LIGHT = "#F8FAFC"
    SURFACE_LIGHT = "#FFFFFF"
    
    BORDER_LIGHT = ft.Colors.with_opacity(0.1, ft.Colors.GREY)
    
    # Aliases for compatibility
    BORDER = "outlineVariant"
    SURFACE = "surface"
    SURFACE_VARIANT = "surfaceVariant"
    
    # Text - Use Flet's adaptive colors
    TEXT_MAIN = ft.Colors.ON_SURFACE
    TEXT_MUTE = ft.Colors.ON_SURFACE_VARIANT
    
    TEXT_MAIN_DARK = ft.Colors.ON_SURFACE # Deprecated, maps to adaptive
    TEXT_MUTE_DARK = ft.Colors.ON_SURFACE_VARIANT # Deprecated, maps to adaptive

    # Text Aliases (Compatibility)
    TEXT_PRIMARY = TEXT_MAIN
    TEXT_SECONDARY = TEXT_MUTE
    TEXT_PRIMARY_DARK = TEXT_MAIN
    TEXT_SECONDARY_DARK = TEXT_MUTE

class AppShadows:
    # Soft, layered shadows for depth
    SMALL = ft.BoxShadow(
        spread_radius=1,
        blur_radius=10,
        color=ft.Colors.with_opacity(0.05, ft.Colors.BLACK),
        offset=ft.Offset(0, 2),
    )
    MEDIUM = ft.BoxShadow(
        spread_radius=1,
        blur_radius=20,
        color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
        offset=ft.Offset(0, 4),
    )
    GLOW = ft.BoxShadow(
        spread_radius=1,
        blur_radius=15,
        color=ft.Colors.with_opacity(0.3, AppColors.PRIMARY),
        offset=ft.Offset(0, 0),
    )

class AppGradients:
    # Modern Linear Gradients
    PRIMARY_LINEAR = ft.LinearGradient(
        begin=ft.Alignment(-1, -1),
        end=ft.Alignment(1, 1),
        colors=[AppColors.PRIMARY, ft.Colors.BLUE_900],
    )
    SURFACE_GLASS = ft.LinearGradient(
        begin=ft.Alignment(-1, -1),
        end=ft.Alignment(1, 1),
        colors=[ft.Colors.with_opacity(0.1, ft.Colors.WHITE), ft.Colors.with_opacity(0.05, ft.Colors.WHITE)],
    )

class AppAnimations:
    # Consistent micro-interactions
    FAST = ft.Animation(300, ft.AnimationCurve.DECELERATE)
    SMOOTH = ft.Animation(600, ft.AnimationCurve.EASE_OUT)
    BOUNCE = ft.Animation(500, ft.AnimationCurve.BOUNCE_OUT)

class AppTextStyles:
    @staticmethod
    def header(page: ft.Page, size=24, bold=True):
        # [Simplified] Use adaptive AppColors.TEXT_MAIN directly
        return ft.TextStyle(size=size, weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL, color=AppColors.TEXT_MAIN)

    @staticmethod
    def body(page: ft.Page, size=14, mute=False):
        # [Simplified] Use adaptive colors
        color = AppColors.TEXT_MUTE if mute else AppColors.TEXT_MAIN
        return ft.TextStyle(size=size, color=color)

    @staticmethod
    def caption(page: ft.Page, size=12):
        return ft.TextStyle(size=size, color=AppColors.TEXT_MUTE)

    # Simplified access for legacy views
    CAPTION = ft.TextStyle(size=12, color=ft.Colors.GREY_500)
    BODY_SMALL = ft.TextStyle(size=12)
    HEADER_TITLE = ft.TextStyle(size=20, weight=ft.FontWeight.BOLD)

class AppLayout:
    # Spacing Tokens (Step of 4 or 8)
    XS = 4
    SM = 8
    MD = 16
    LG = 24
    XL = 32
    
    HEADER_PADDING = 16 # Standard header padding
    CONTENT_PADDING = 16 # Standard content padding
    
    BORDER_RADIUS_SM = 8
    BORDER_RADIUS_MD = 12
    BORDER_RADIUS_LG = 16
    
    # Standard Container Style
    @staticmethod
    def card_style(page: ft.Page):
        is_dark = page.theme_mode == ft.ThemeMode.DARK
        return {
            "bgcolor": AppColors.SURFACE_DARK if is_dark else AppColors.SURFACE_LIGHT,
            "border_radius": AppLayout.BORDER_RADIUS_MD,
            "padding": AppLayout.MD,
            "shadow": AppShadows.MEDIUM if not is_dark else None,
            "border": ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.GREY)) if is_dark else None
        }

class AppButtons:
    """
    Standard Button Styles for Consistency.
    Usage: ft.ElevatedButton("Text", style=AppButtons.PRIMARY, ...)
    """
    
    # Base Shapes
    ROUNDED_SM = ft.RoundedRectangleBorder(radius=8)
    ROUNDED_MD = ft.RoundedRectangleBorder(radius=12)
    
    # standard height for touch targets
    HEIGHT_SM = 36
    HEIGHT_MD = 48
    
    @staticmethod
    def _base_style(bgcolor, color, radius=8):
        return ft.ButtonStyle(
            bgcolor=bgcolor,
            color=color,
            shape=ft.RoundedRectangleBorder(radius=radius),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            elevation=0, # Flat modern look
            overlay_color=ft.Colors.with_opacity(0.1, "white"),
        )

    # Pre-defined Styles (Properties to be spread or used directly where supported)
    # Note: Flet ButtonStyle is complex to merge, so we provide helper methods or standard dicts.
    
    @classmethod
    def PRIMARY(cls):
        return cls._base_style(AppColors.PRIMARY, ft.Colors.WHITE, 12)

    @classmethod
    def SECONDARY(cls):
        return cls._base_style(AppColors.SURFACE_VARIANT, AppColors.TEXT_MAIN, 12)
        
    @classmethod
    def SUCCESS(cls):
        return cls._base_style(AppColors.SUCCESS, ft.Colors.WHITE, 12)

    @classmethod
    def DANGER(cls):
        return cls._base_style(AppColors.ERROR, ft.Colors.WHITE, 12)
    
    @classmethod
    def OUTLINE(cls):
        return ft.ButtonStyle(
            color=AppColors.TEXT_MAIN,
            shape=ft.RoundedRectangleBorder(radius=12),
            side=ft.BorderSide(1, AppColors.BORDER_LIGHT),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
        )
