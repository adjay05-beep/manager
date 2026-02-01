import flet as ft
all_names = dir(ft)
# Filter for anything reorder or drag related
reorder_related = [name for name in all_names if "reorder" in name.lower() or "drag" in name.lower() or "handle" in name.lower()]
print("Reorder/Drag related in ft:", reorder_related)
