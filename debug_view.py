import flet as ft

def main(page: ft.Page):
    page.title = "View Test"
    print("Executing View Test Main")
    
    # Simple View Test
    try:
        tview = ft.View(
            "/",
            [
                ft.AppBar(title=ft.Text("Debug View")),
                ft.Container(
                    content=ft.Text("If you see this, Views are working.", size=20),
                    alignment=ft.Alignment(0, 0),
                    bgcolor=ft.Colors.AMBER_100,
                    expand=True
                )
            ]
        )
        page.views.append(tview)
        page.update()
        print("View appended and page updated")
    except Exception as e:
        print(f"Error adding view: {e}")

if __name__ == "__main__":
    ft.app(target=main)
