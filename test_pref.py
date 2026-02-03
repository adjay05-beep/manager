import flet as ft
import asyncio

async def main(page: ft.Page):
    await page.shared_preferences.set("test_key", "test_val")
    print("Set test_key")
    page.window_close()

ft.run(main)
