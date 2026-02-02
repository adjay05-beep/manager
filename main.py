import flet as ft
from services.router import Router
from utils.logger import log_error, log_info

async def main(page: ft.Page):
    print("DEBUG: Inside main function!")
    page.title = "The Manager"

    # [Flet 0.80+] Custom session storage since page.session API changed
    page.app_session = {}
    
    # [THEME PERSISTENCE] Load theme from shared_preferences (Flet 0.80+)
    try:
        theme_mode_str = await page.shared_preferences.get("theme_mode")  # Flet 0.80+ uses get()
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

    # [CRITICAL PATCH] Fix KeyError: 'bytes' in Flet/Starlette compatibility
    # Starlette's receive_bytes strict implementation crashes if 'bytes' key is missing.
    try:
        import starlette.websockets
        from typing import cast
        
        async def patched_receive_bytes(self) -> bytes:
            while True:
                message = await self.receive()
                self._raise_on_disconnect(message)
                if "bytes" in message:
                    return cast(bytes, message["bytes"])
                # If non-bytes (e.g. text 'ping'), log and continue waiting
                # This prevents the KeyError: 'bytes' crash
                print(f"DEBUG_SOCK: Ignored non-bytes message. Type: {message.get('type')}, Keys: {list(message.keys())}")
                # Loop continues to receive next message
            
        starlette.websockets.WebSocket.receive_bytes = patched_receive_bytes
        print("SYSTEM: Applied Monkey-Patch for WebSocket.receive_bytes")
    except ImportError:
        print("WARNING: Could not apply WebSocket patch (Starlette not found)")

    # [POLYFILL] Add Page.open support for Flet 0.80.5
    if not hasattr(ft.Page, "open"):
        print("SYSTEM: Applying Polyfill for Page.open (Overlay-only)")
        def page_open_polyfill(self, control):
            print(f"[POLYFILL] page.open called with: {type(control).__name__}")
            
            # For AlertDialog and similar controls with 'open' attribute
            if hasattr(control, 'open'):
                print(f"[POLYFILL] Using OVERLAY ONLY approach for dialog")
                control.open = True
                control.visible = True # Explicitly visible
                
                # IMPORTANT: DO NOT set self.dialog in 0.80.5 Web! 
                if control not in self.overlay:
                    self.overlay.append(control)
                    print(f"[POLYFILL] Added to page.overlay")
                
                self.update()
                print(f"[POLYFILL] Dialog should now be visible via overlay")
            else:
                # Non-dialog controls - add to overlay
                print(f"[POLYFILL] Adding non-dialog to overlay")
                if control not in self.overlay:
                    self.overlay.append(control)
                self.update()
        ft.Page.open = page_open_polyfill
    else:
        print("SYSTEM: Page.open already exists, skipping polyfill")
    
    # [POLYFILL] Add Page.close support
    _original_page_close = getattr(ft.Page, "close", None)

    def page_close_polyfill(self, control):
        if not control: return
        print(f"[POLYFILL] page.close called with: {type(control).__name__}")

        # Set open=False for dialog controls
        if hasattr(control, 'open'):
            control.open = False
            print(f"[POLYFILL] Set open=False")

        if hasattr(control, 'visible'):
            control.visible = False
            print(f"[POLYFILL] Set visible=False")

        # [FIX] Clear content to force visual removal
        if hasattr(control, 'content'):
            control.content = None
            print(f"[POLYFILL] Cleared content")

        if hasattr(control, 'actions'):
            control.actions = []
            print(f"[POLYFILL] Cleared actions")

        # [FIX] Try setting page.dialog = None
        try:
            self.dialog = None
            print(f"[POLYFILL] Set page.dialog = None")
        except Exception as e:
            print(f"[POLYFILL] Could not set page.dialog: {e}")

        # Remove from overlay
        if control in self.overlay:
            while control in self.overlay:
                self.overlay.remove(control)
            print(f"[POLYFILL] Removed from overlay")

        # [FIX] Call original close if exists
        if _original_page_close:
            try:
                _original_page_close(self, control)
                print(f"[POLYFILL] Called original page.close")
            except Exception as e:
                print(f"[POLYFILL] Original close error: {e}")

        # Force UI update
        self.update()
        print(f"[POLYFILL] Page updated after close")

    ft.Page.close = page_close_polyfill

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
        ft.run(
            main,
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
