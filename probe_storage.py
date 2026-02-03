import flet as ft
import asyncio

async def main(page: ft.Page):
    print(f"DEBUG: page.client_storage: {hasattr(page, 'client_storage')}")
    print(f"DEBUG: page.shared_preferences: {hasattr(page, 'shared_preferences')}")
    print(f"DEBUG: dir(page): {[m for m in dir(page) if 'storage' in m.lower()]}")
    await asyncio.sleep(1)
    page.window_close()

ft.app(target=main)
