import os
import asyncio
import flet as ft
from services.router import Router
from utils.logger import log_error, log_info
from utils.sys_logger import sys_log

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
    
    # [SYSTEM BRIDGE] Global hidden bridge for JS communication per session
    page._bridge = ft.TextField(
        opacity=0, width=1, height=1, 
        hint_text="SYSTEM_JS_BRIDGE"
    )
    page.overlay.append(page._bridge)

    # [SYSTEM BRIDGE 2.0] Title-based communication (The most stable method for 0.80+)
    page._js_result = None
    page._js_event = asyncio.Event()

    async def on_title_change(e):
        # We look for a special prefix in the title: "RESULT:{"
        if page.title.startswith("RESULT:"):
            res_json = page.title[7:]
            sys_log(f"TITLE_BRIDGE: Received data: {res_json[:50]}...")
            page._js_result = res_json
            page._js_event.set()
            # Restore title
            page.title = "Manager"
            page.update()

    page.on_title_change = on_title_change

    # [POLYFILL 2.0] Enhanced run_javascript
    async def run_javascript_fixed(self, script: str, return_value: bool = False):
        import asyncio, re
        
        # Minify
        minified = re.sub(r"\s+", " ", script).strip()
        
        # Wrap to write to document.title instead of TextField
        if return_value:
            # We use document.title because it triggers an event in Flet immediately
            wrapped_js = (
                f"(async()=>{{try{{"
                f"let r=await({minified});"
                f"document.title='RESULT:'+(typeof r==='object'?JSON.stringify(r):String(r));"
                f"}}catch(e){{"
                f"document.title='RESULT:'+JSON.stringify({{error:e.toString()}});"
                f"}}}}).call();"
            )
        else:
            wrapped_js = minified

        try:
            # First trial: Native Flet run_javascript (Flet 0.80+)
            # Note: The original 'self.run_javascript' is now 'run_javascript_fixed'
            # We call the base version if it exists or use the page object's method
            # In Flet 0.80+, ft.Page has run_javascript but it's often unreliable in web
            # So we use a more direct approach by calling the underlying client command if possible
            # But the most compatible way is actually launch_url for some, but Safari blocks it.
            # Let's try native run_javascript if it's available and not our fixed version
            
            sys_log(f"run_javascript: Executing via Title Bridge...")
            # We must use self.run_javascript but not recursively.
            # However, Flet's internal run_javascript is what we really want here.
            # Since we replaced ft.Page.run_javascript, we use the original logic but without launch_url
            
            # Use original launch_url as fallback, but try to avoid it if possible
            # For Safari, let's try to inject a script tag or use the native client
            await self.launch_url(f"javascript:void({wrapped_js})")
        except Exception as e:
            sys_log(f"run_javascript FAILED: {e}")
            return None

        if return_value:
            self._js_event.clear()
            self._js_result = None
            try:
                # Wait for title change event
                await asyncio.wait_for(self._js_event.wait(), timeout=45.0)
                return self._js_result
            except asyncio.TimeoutError:
                sys_log("run_javascript: ERROR - Title Bridge Timeout")
                return None
        return None

    ft.Page.run_javascript = run_javascript_fixed
    sys_log("Applied Title-Bridge Polyfill to ft.Page (v2.0)")

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
