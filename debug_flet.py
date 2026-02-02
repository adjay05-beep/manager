import flet as ft
import inspect

print(f"Flet Version: {ft.version}")

try:
    print(f"Has ft.Page.open: {hasattr(ft.Page, 'open')}")
    print(f"Has ft.Page.open_async: {hasattr(ft.Page, 'open_async')}")
    
    # Check what 'open' actually is
    if hasattr(ft.Page, 'open'):
        print(f"ft.Page.open signature: {inspect.signature(ft.Page.open)}")
except Exception as e:
    print(f"Error checking attributes: {e}")

print("Done.")
