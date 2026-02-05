import os
import asyncio
import flet as ft
from services.router import Router
from utils.logger import log_error, log_info
from utils.sys_logger import sys_log

# [SYSTEM] Safe run_javascript polyfill for Flet 0.80.5
async def run_javascript_polyfill(self, script):
    try:
        # 1. Try internal Flet method
        if hasattr(self, "_Page__run_javascript"):
            return await self._Page__run_javascript(script)
        # 2. Try legacy eval
        if hasattr(self, "eval"):
            return await self.eval(script)
        # 3. Last resort: launch_url
        return await self.launch_url(f"javascript:{script}")
    except Exception:
        return await self.launch_url(f"javascript:{script}")

# Apply to class immediately
if not hasattr(ft.Page, "run_javascript"):
    ft.Page.run_javascript = run_javascript_polyfill
    print("SYSTEM: ✓ Injected global run_javascript polyfill")
else:
    print("SYSTEM: ✓ Native run_javascript detected")

async def main(page: ft.Page):
    page.title = "The Manager"

    # [Flet 0.80+] Custom session storage
    page.app_session = {}
    
    # [THEME PERSISTENCE]
    try:
        theme_mode_str = await page.shared_preferences.get("theme_mode")
    except Exception:
        theme_mode_str = None
    
    if theme_mode_str == "dark":
        page.theme_mode = ft.ThemeMode.DARK
    else:
        page.theme_mode = ft.ThemeMode.LIGHT
    
    page.padding = 0
    page.spacing = 0

    sys_log("✓ Main page initialization complete")

    # [POLYFILL] Add Page.open/close support
    if not hasattr(ft.Page, "open"):
        def page_open_polyfill(self, control):
            if hasattr(control, 'open'):
                control.open = True
                control.visible = True
                if control not in self.overlay:
                    self.overlay.append(control)
                self.update()
            elif control not in self.overlay:
                self.overlay.append(control)
                self.update()
        ft.Page.open = page_open_polyfill

    if not hasattr(ft.Page, "close"):
        def page_close_polyfill(self, control):
            if not control: return
            if hasattr(control, 'open'): control.open = False
            if hasattr(control, 'visible'): control.visible = False
            if control in self.overlay: self.overlay.remove(control)
            self.update()
        ft.Page.close = page_close_polyfill

    # [Flet 0.80+] Global FilePicker (TEMPORARILY DISABLED AS IT CRASHES SAFARI)
    page.chat_file_picker = None
    # if page.web:
    #     file_picker = ft.FilePicker()
    #     page.overlay.append(file_picker)
    #     page.chat_file_picker = file_picker

    router = Router(page)
    await router.start()

if __name__ == "__main__":
    import os
    import flet as ft
    os.makedirs("uploads", exist_ok=True)
    
    # [CRITICAL PATCH] Fix 'text' and 'bytes' KeyError in Flet/Starlette WebSocket compatibility
    try:
        import starlette.websockets
        from typing import cast
        import json
        
        # Patch receive_bytes
        async def patched_receive_bytes(self) -> bytes:
            while True:
                message = await self.receive()
                self._raise_on_disconnect(message)
                if "bytes" in message:
                    return cast(bytes, message["bytes"])
                # Skip non-bytes messages silently
                if message.get("type") == "websocket.disconnect":
                    return b""
        
        # Patch receive_text
        async def patched_receive_text(self) -> str:
            while True:
                message = await self.receive()
                self._raise_on_disconnect(message)
                if "text" in message:
                    return cast(str, message["text"])
                # Skip non-text messages silently
                if message.get("type") == "websocket.disconnect":
                    return ""
        
        # Patch receive_json
        async def patched_receive_json(self):
            while True:
                message = await self.receive()
                self._raise_on_disconnect(message)
                if "text" in message:
                    text = cast(str, message["text"])
                    return json.loads(text)
                # Skip non-json messages silently
                if message.get("type") == "websocket.disconnect":
                    return None
        
        starlette.websockets.WebSocket.receive_bytes = patched_receive_bytes
        starlette.websockets.WebSocket.receive_text = patched_receive_text
        starlette.websockets.WebSocket.receive_json = patched_receive_json
        print("SYSTEM: ✓ Applied WebSocket patches (receive_bytes, receive_text, receive_json)")
    except ImportError:
        print("WARNING: Could not apply WebSocket patch")
    except Exception as e:
        print(f"WARNING: WebSocket patch failed: {e}")


    port = int(os.getenv("PORT", 8888))
    host = "0.0.0.0" 
    
    # Secure key setup
    secret_key = os.getenv("FLET_SECRET_KEY")
    if not secret_key:
        import secrets
        os.environ["FLET_SECRET_KEY"] = secrets.token_hex(32)

    # [RETENTION] Run cleanup task in background on startup
    try:
        from services.chat_service import cleanup_empty_topics
        import threading
        print("SYSTEM: Starting background cleanup task for empty topics...")
        threading.Thread(target=cleanup_empty_topics, kwargs={'days': 3}, daemon=True).start()
    except Exception as e:
        print(f"WARNING: Cleanup task failed to start: {e}")

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
    # Force Reload Trigger: 2026-02-05 10:25:00
