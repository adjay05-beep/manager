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

    # [POLYFILL 2.0] Enhanced run_javascript - Safari Compatible
    # Save the original method before we override it
    _original_run_js = ft.Page.run_javascript if hasattr(ft.Page, 'run_javascript') else None

    async def run_javascript_fixed(self, script: str, return_value: bool = False):
        import asyncio, re, urllib.parse

        # Minify script
        minified = re.sub(r"\s+", " ", script).strip()

        sys_log(f"run_javascript: Starting execution (return_value={return_value})...")

        # If return_value is True, wrap script to store result
        if return_value:
            # Store result in both document.title (for callback) and localStorage (for polling)
            wrapped_js = (
                f"(async()=>{{try{{"
                f"let r=await({minified});"
                f"let json=typeof r==='object'?JSON.stringify(r):String(r);"
                f"localStorage.setItem('flet_js_result',json);"
                f"document.title='RESULT:'+json;"
                f"}}catch(e){{"
                f"let err=JSON.stringify({{error:e.toString()}});"
                f"localStorage.setItem('flet_js_result',err);"
                f"document.title='RESULT:'+err;"
                f"}}}})();"
            )
            # Clear previous results
            self._js_event.clear()
            self._js_result = None
        else:
            wrapped_js = minified

        executed = False

        # Method 1: Try Flet's native run_javascript (Flet 0.80+)
        if _original_run_js and not executed:
            try:
                # Call the original method directly on the instance
                result = await _original_run_js(self, wrapped_js)
                sys_log("run_javascript: Native Flet method succeeded")
                executed = True
                if not return_value:
                    return result
            except Exception as e:
                sys_log(f"run_javascript: Native method failed: {e}")

        # Method 2: Try using Flet's internal _send_command if available
        if hasattr(self, '_send_command') and not executed:
            try:
                await self._send_command("runScript", {"script": wrapped_js})
                sys_log("run_javascript: _send_command succeeded")
                executed = True
            except Exception as e:
                sys_log(f"run_javascript: _send_command failed: {e}")

        # Method 3: Inject script via page overlay (more Safari-compatible)
        if not executed:
            try:
                # Use data URI approach which is more reliable than javascript: URLs
                # Encode the script for safe transmission
                encoded_script = urllib.parse.quote(wrapped_js, safe='')
                data_url = f"data:text/html,<script>{urllib.parse.unquote(encoded_script)}</script>"

                # Try iframe injection approach
                iframe_js = f"(function(){{var s=document.createElement('script');s.textContent={repr(wrapped_js)};document.body.appendChild(s);s.remove();}})();"

                # For Safari, try direct script injection via eval workaround
                await self.launch_url(f"javascript:{urllib.parse.quote(iframe_js)}")
                sys_log("run_javascript: launch_url with script injection")
                executed = True
            except Exception as e:
                sys_log(f"run_javascript: Script injection failed: {e}")

        if return_value:
            try:
                # Wait for title change event with timeout
                await asyncio.wait_for(self._js_event.wait(), timeout=30.0)
                if self._js_result:
                    return self._js_result
            except asyncio.TimeoutError:
                sys_log("run_javascript: Title bridge timeout, trying localStorage fallback...")

            # Fallback: Try to read result from localStorage
            try:
                read_result_js = "localStorage.getItem('flet_js_result')"
                if _original_run_js:
                    result = await _original_run_js(self, read_result_js)
                    if result:
                        sys_log(f"run_javascript: Got result from localStorage: {result[:50]}...")
                        return result
            except Exception as e:
                sys_log(f"run_javascript: localStorage fallback failed: {e}")

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
