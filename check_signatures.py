import flet as ft
import inspect

def probe():
    print(f"Flet Version: {ft.__version__}")
    try:
        sig = inspect.signature(ft.Page.launch_url)
        print(f"launch_url signature: {sig}")
    except Exception as e:
        print(f"Error getting signature: {e}")

if __name__ == "__main__":
    probe()
