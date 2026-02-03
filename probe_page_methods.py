import flet as ft

def main(page: ft.Page):
    print("Methods in ft.Page:")
    for m in sorted(dir(page)):
        if "js" in m.lower() or "script" in m.lower() or "run" in m.lower():
            print(f" - {m}")
    page.window_close()

if __name__ == "__main__":
    ft.app(target=main)
