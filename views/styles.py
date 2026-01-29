import flet as ft

class AppColors:
    # Primary Palette
    PRIMARY = "#1565C0"       # Deep Blue
    SECONDARY = "#00BCD4"     # Cyan
    ACCENT = "#2E7D32"        # Green
    DANGER = "#E53935"        # Red
    WARNING = "#FF9800"       # Orange

    # Backgrounds
    BACKGROUND = "#F5F5F5"    # Light Grey (Page BG)
    SURFACE = "#FFFFFF"       # White (Cards, Headers)
    SURFACE_VARIANT = "#FAFAFA" 
    
    # Text
    TEXT_PRIMARY = "#212121"  # Almost Black
    TEXT_SECONDARY = "#757575" # Grey
    TEXT_HINT = "#BDBDBD"     # Light Grey
    
    # Borders
    BORDER = "#E0E0E0"
    BORDER_LIGHT = "#F0F0F0"

class AppTextStyles:
    # Headers
    HEADER_TITLE = ft.TextStyle(size=20, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY)
    SECTION_TITLE = ft.TextStyle(size=16, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY)
    SUBTITLE = ft.TextStyle(size=14, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_SECONDARY)
    
    # Body
    BODY_LARGE = ft.TextStyle(size=16, color=AppColors.TEXT_PRIMARY)
    BODY = ft.TextStyle(size=14, color=AppColors.TEXT_PRIMARY)
    BODY_SMALL = ft.TextStyle(size=12, color=AppColors.TEXT_SECONDARY)
    CAPTION = ft.TextStyle(size=11, color=AppColors.TEXT_HINT)

class AppLayout:
    # Spacing
    PAGE_PADDING = 0 # Use within SafeArea
    CONTENT_PADDING = 20 # Standard padding for content containers
    HEADER_PADDING = ft.padding.only(left=10, right=10, top=10, bottom=10)
    
    # Sizing
    HEADER_HEIGHT = 60
    
    # Borders
    STANDARD_BORDER_RADIUS = 10
