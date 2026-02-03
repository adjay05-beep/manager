import flet as ft
import asyncio

async def main(page: ft.Page):
    # Register the current polyfill
    if not hasattr(page, "run_javascript"):
        async def run_js(script):
            # Using the most aggressive version we have
            await page.launch_url(f"javascript:{script}", web_popup_window_name="_self")
        page.run_javascript = run_js

    async def test_alert(e):
        print("Sending alert...")
        await page.run_javascript("alert('JS Bridge Test')")
    
    page.add(ft.ElevatedButton("Test JS Alert", on_click=test_alert))

if __name__ == "__main__":
    ft.app(target=main, port=8556) # Use a different port to avoid conflicts
