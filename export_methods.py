import flet as ft

def main(page: ft.Page):
    with open("page_methods.txt", "w") as f:
        for m in dir(page):
            f.write(f"{m}\n")
    page.window_close()

ft.app(target=main)
