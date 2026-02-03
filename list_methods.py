import flet as ft
p = ft.Page(None, "")
with open("page_methods.txt", "w") as f:
    for m in dir(p):
        f.write(f"{m}\n")
print("Done")
