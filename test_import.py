try:
    from flet import DragHandle
    print("Direct import success")
except ImportError as e:
    print(f"Direct import fail: {e}")

import flet as ft
try:
    dh = ft.DragHandle()
    print("ft.DragHandle success")
except AttributeError as e:
    print(f"ft.DragHandle fail: {e}")
