import flet as ft

def get_login_controls(page: ft.Page, navigate_to):
    pw = ft.TextField(
        label="PIN CODE", 
        password=True, 
        text_align=ft.TextAlign.CENTER, 
        width=240, 
        on_submit=lambda e: navigate_to("home") if pw.value=="1234" else None,
        border_color="white",
        cursor_color="white",
        color="white"
    )
    
    login_card = ft.Container(
        content=ft.Column([
            ft.Text("THE MANAGER", size=32, weight="bold", color="white", style=ft.TextStyle(letter_spacing=2)),
            ft.Text("Restaurant Management OS", size=14, color="white70"),
            ft.Container(height=40),
            pw,
            ft.ElevatedButton(
                "출근하기", 
                on_click=lambda _: navigate_to("home") if pw.value=="1234" else None, 
                width=240, height=50,
                style=ft.ButtonStyle(
                    color="black",
                    bgcolor="white",
                    shape=ft.RoundedRectangleBorder(radius=10)
                )
            )
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=40,
        border_radius=30,
        bgcolor=ft.Colors.with_opacity(0.2, "white"),
        border=ft.border.all(1, ft.Colors.with_opacity(0.2, "white")),
    )
    
    return [
        ft.Stack([
            # 1. Background Color
            ft.Container(expand=True, bgcolor="#0A1929"),
            
            # 2. Background Image
            ft.Image(
                src="images/login_bg.png",
                fit=ft.ImageFit.COVER,
                opacity=0.7,
                expand=True
            ),
            
            # 3. Login Overlay
            ft.Container(
                content=login_card, 
                alignment=ft.alignment.center, 
                expand=True,
                bgcolor=ft.Colors.with_opacity(0.3, "black")
            )
        ], expand=True)
    ]
