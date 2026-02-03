import flet as ft
import asyncio

async def main(page: ft.Page):
    msg = ft.Text("Testing Markdown Injection...")
    
    # We'll use a hidden Markdown element to trigger JS
    # The JS will change the text of 'msg' by finding its DOM element if possible, 
    # OR it will set a value in a TextField bridge.
    
    bridge = ft.TextField(label="Bridge", placeholder="BRIDGE_TARGET", width=300)
    
    inject = ft.Markdown(
        "![test](https://invalid.url) <img src=x onerror=\"document.querySelector('input[placeholder=\\'BRIDGE_TARGET\\']').value='SUCCESS'; document.querySelector('input[placeholder=\\'BRIDGE_TARGET\\']').dispatchEvent(new Event('input', {bubbles:true}));\">",
        extension_set="gitHubWeb"
    )
    
    def on_change(e):
        if bridge.value == "SUCCESS":
            msg.value = "INJECTION SUCCESSFUL!"
            msg.color = "green"
            page.update()

    bridge.on_change = on_change
    
    page.add(msg, bridge, inject)
    
    await asyncio.sleep(5)
    page.window_close()

if __name__ == "__main__":
    ft.run(main, port=8998)
