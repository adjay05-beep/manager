import flet as ft
import asyncio

async def main(page: ft.Page):
    print("Testing JS polyfill...")
    if not hasattr(page, "run_javascript"):
        async def run_javascript_polyfill(script):
            await page._invoke_method("run_javascript", {"script": script})
        page.run_javascript = run_javascript_polyfill
        print("Polyfill added.")
    
    try:
        await page.run_javascript("console.log('Polyfill works!')")
        print("Call success.")
    except Exception as e:
        print(f"Call failed: {e}")
    page.window_close()

ft.run(main)
