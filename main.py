import flet as ft
from services.router import Router
from utils.logger import log_error, log_info

async def main(page: ft.Page):
    print("DEBUG: Inside main function!")
    page.title = "The Manager"

    # [Flet 0.80+] Custom session storage since page.session API changed
    page.app_session = {}
    
    # [THEME PERSISTENCE] Load theme from client_storage
    try:
        theme_mode_str = await page.client_storage.get_async("theme_mode")
    except Exception as e:
        theme_mode_str = None
    
    if theme_mode_str == "dark":
        page.theme_mode = ft.ThemeMode.DARK
    else:
        page.theme_mode = ft.ThemeMode.LIGHT
    
    page.padding = 0
    page.spacing = 0
    
    # [Flet 0.80+] FilePicker disabled
    page.file_picker = None
    page.chat_file_picker = None
    page.audio_recorder = None
    
    # Optimized Route Management via Router Service
    page.history_stack = [] # Kept for backward compatibility if any view accesses it directly
    
    # Initialize Router
    router = Router(page)
    
    # Start Application
    await router.start()

if __name__ == "__main__":
    import os
    import flet as ft
    # Ensure upload directory exists for Proxy Uploads
    os.makedirs("uploads", exist_ok=True)

    # 클라우드 환경(Render 등)에서 제공하는 PORT 변수를 우선 사용합니다.
    port = int(os.getenv("PORT", 8555))
    host = "0.0.0.0"
    
    # Secure Uploads require a Secret Key
    secret_key = os.getenv("FLET_SECRET_KEY")
    if not secret_key:
        import secrets
        secret_key = secrets.token_hex(32)
        print("WARNING: FLET_SECRET_KEY not set. Generated temporary key.")
    os.environ["FLET_SECRET_KEY"] = secret_key

    # flet 0.80.x 이상
    try:
        ft.app(
            target=main,
            port=port,
            host=host,
            assets_dir="assets",
            upload_dir="uploads",
            view=ft.AppView.WEB_BROWSER
        )
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
