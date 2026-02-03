import flet as ft
import asyncio

async def main(page: ft.Page):
    # Register run_javascript polyfill if missing
    if not hasattr(page, "run_javascript"):
        async def run_javascript_polyfill(script):
            await page._invoke_method("run_javascript", {"script": script})
        page.run_javascript = run_javascript_polyfill

    # 1. Set via localStorage directly (NO prefix)
    await page.run_javascript("localStorage.setItem('no_prefix', 'value_1')")
    await asyncio.sleep(1)
    val1 = await page.shared_preferences.get("no_prefix")
    print(f"Read NO prefix: {val1}")

    # 2. Set via localStorage with 'flet_pref:' prefix
    await page.run_javascript("localStorage.setItem('flet_pref:with_prefix', 'value_2')")
    await asyncio.sleep(1)
    val2 = await page.shared_preferences.get("with_prefix")
    print(f"Read WITH prefix: {val2}")

    page.window_close()

ft.run(main)
