import flet as ft

async def main(page: ft.Page):
    print(f"Executing in VENV: Flet {ft.__version__}")
    if hasattr(page, "run_javascript"):
        print("SUCCESS: page.run_javascript EXISTS natively!")
    else:
        print("FAILURE: page.run_javascript still missing.")
    page.window_close()

if __name__ == "__main__":
    ft.run(main)
