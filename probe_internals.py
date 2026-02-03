import flet as ft

async def main(page: ft.Page):
    print("Page object analysis:")
    print(f" - dir(page): {dir(page)}")
    
    if hasattr(page, "session"):
        print(f" - page.session: {page.session}")
        print(f" - dir(page.session): {dir(page.session)}")
    
    # Try to find invoke or send methods
    for attr in dir(page):
        if "invoke" in attr.lower() or "send" in attr.lower() or "method" in attr.lower():
            print(f" - Found method: {attr}")

    page.window_close()

if __name__ == "__main__":
    ft.app(target=main)
