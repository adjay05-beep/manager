import flet as ft

def main(page: ft.Page):
    page.title = "Flet Test"
    page.add(ft.Text("Hello, Flet!", size=30, color="blue"))
    page.update()

if __name__ == "__main__":
    print("Running test app...")
    try:
        ft.app(target=main)
    except Exception as e:
        print(f"Error: {e}")
        input("Error... Press enter")
