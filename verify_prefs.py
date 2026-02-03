import flet as ft
import asyncio

async def main(page: ft.Page):
    # Set something in python
    await page.shared_preferences.set("python_key", "python_val")
    # Check if we can read it
    val = await page.shared_preferences.get("python_key")
    print(f"Read python_key: {val}")
    page.window_close()

ft.run(main)
