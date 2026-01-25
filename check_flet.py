import flet as ft
print(f"Flet Version: {ft.__version__ if hasattr(ft, '__version__') else 'unknown'}")
print("DragHandle:", hasattr(ft, "DragHandle"))
print("ReorderableDragStartListener:", hasattr(ft, "ReorderableDragStartListener"))
print("ReorderableDelayedDragStartListener:", hasattr(ft, "ReorderableDelayedDragStartListener"))
print("BuildDefaultDragHandles property:", hasattr(ft.ReorderableListView, "build_default_drag_handles"))
