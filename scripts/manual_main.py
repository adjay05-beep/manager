import flet as ft
import traceback

def main(page: ft.Page):
    print("Executing Manual Main")
    page.title = "Manual Router Test"
    
    # 1. Define content functions (Returning Lists of Controls, NOT Views)
    def get_login_controls():
        return [
            ft.Text("MANUAL ROUTER: LOGIN", size=30, color="blue"),
            ft.Text("If you see this, ft.View was the problematic component.", size=20),
            ft.ElevatedButton("Go Home", on_click=lambda e: go_to("home"))
        ]

    def get_home_controls():
        return [
            ft.Text("MANUAL ROUTER: HOME", size=30, color="green"),
            ft.Text("Welcome to the home screen.", size=20),
            ft.ElevatedButton("Go Back", on_click=lambda e: go_to("login"))
        ]

    # 2. Manual Navigation Function
    def go_to(route_name):
        print(f"Navigating to {route_name}...")
        try:
            page.clean() # Clear existing controls
            
            if route_name == "login":
                page.add(*get_login_controls())
            elif route_name == "home":
                page.add(*get_home_controls())
            
            page.update()
            print("Page updated.")
        except Exception as e:
            print(f"Error navigating: {e}")
            traceback.print_exc()

    # 3. Start
    go_to("login")

if __name__ == "__main__":
    try:
        ft.app(target=main, view=ft.AppView.WEB_BROWSER)
    except Exception as e:
        print(f"Critical: {e}")
