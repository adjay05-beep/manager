import flet as ft
from app_views import login_view
import traceback

def main(page: ft.Page):
    print("Executing Minimal Main")
    try:
        # 1. Test basic Text add (Working control)
        page.add(ft.Text("Step 1: Basic Text works", color="green", size=20))
        page.update()
        print("Step 1 rendered")
        
        # 2. Test Login View Content directly
        # Extract content from the View object (since page.add expects Controls, not View)
        view_obj = login_view(page)
        
        # login_view returns ft.View(route, controls=[...])
        # We need to add the *controls* of that View to the page
        print(f"View controls count: {len(view_obj.controls)}")
        
        for control in view_obj.controls:
             page.add(control)
        
        page.update()
        print("Step 2 (Login View) rendered")

    except Exception as e:
        print(f"Error in minimal main: {e}")
        traceback.print_exc()
        page.add(ft.Text(f"Error: {e}", color="red", size=30))

if __name__ == "__main__":
    ft.app(target=main)
