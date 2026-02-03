import flet as ft
import os

def main(page: ft.Page):
    attrs = sorted(dir(page))
    with open("page_attrs.txt", "w") as f:
        f.write("\n".join(attrs))
    page.add(ft.Text("Probing done. Check page_attrs.txt"))
    page.update()
    page.window_destroy()

if __name__ == "__main__":
    ft.app(target=main)
