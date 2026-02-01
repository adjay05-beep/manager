
import flet as ft
import inspect

print(f"Flet Version: {ft.version}")
if hasattr(ft, 'run'):
    print("ft.run exists")
    try:
        sig = inspect.signature(ft.run)
        print(f"Signature: {sig}")
    except Exception as e:
        print(f"Could not get signature: {e}")
else:
    print("ft.run DOES NOT exist")

if hasattr(ft, 'app'):
    print("ft.app exists")
