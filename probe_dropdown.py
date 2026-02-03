import flet as ft
import inspect

def main(page: ft.Page):
    print("Dropdown Init Args:")
    try:
        sig = inspect.signature(ft.Dropdown.__init__)
        for param in sig.parameters.values():
            print(f" - {param.name}")
    except Exception as e:
        print(f"Error inspecting Dropdown: {e}")
    page.window_close()

if __name__ == "__main__":
    ft.app(target=main)
