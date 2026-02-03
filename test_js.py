import flet as ft
import asyncio

async def main(page: ft.Page):
    print("Testing JS execution via _invoke_method...")
    try:
        # Flet internals often use _invoke_method to talk to the client
        # In some versions, run_javascript is just a wrapper around this
        await page._invoke_method("run_javascript", {"script": "console.log('Hello from Python via _invoke_method')"})
        print("Success!")
    except Exception as e:
        print(f"Failed: {e}")
    page.window_close()

ft.run(main)
