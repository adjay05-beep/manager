import flet as ft

def get_home_controls(page: ft.Page, navigate_to):
    def action_btn(label, icon_path, route):
        return ft.Container(
            content=ft.Column([
                ft.Image(src=icon_path, width=80, height=80),
                ft.Text(label, weight="bold", size=16, color="white"),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=165, height=180,
            bgcolor=ft.Colors.with_opacity(0.1, "white"),
            border_radius=25,
            on_click=lambda _: navigate_to(route),
            alignment=ft.alignment.center,
            ink=True,
            border=ft.border.all(0.5, ft.Colors.with_opacity(0.1, "white"))
        )

    from db import has_service_key
    
    debug_badge = ft.Container(
        content=ft.Text(
            "Service Key: OK" if has_service_key else "Service Key: Missing (Bypass OFF)",
            size=10, color="white" if has_service_key else "orange", weight="bold"
        ),
        bgcolor=ft.Colors.with_opacity(0.1, "green" if has_service_key else "red"),
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
        border_radius=5
    )

    header = ft.Container(
        padding=ft.padding.only(left=20, right=20, top=40, bottom=20),
        content=ft.Row([
            ft.Column([
                ft.Text("Welcome back,", size=14, color="white70"),
                ft.Text("The Manager", size=24, weight="bold", color="white"),
                debug_badge
            ], spacing=2),
            ft.IconButton(ft.Icons.LOGOUT_ROUNDED, icon_color="white", on_click=lambda _: navigate_to("login"))
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    )


    grid = ft.Column([
        ft.Row([
            action_btn("팀 스레드", "images/icon_chat.png", "chat"),
            action_btn("마감 점검", "images/icon_check.png", "closing"),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
        ft.Row([
            action_btn("음성 메모", "images/icon_voice.png", "order"),
            action_btn("근무 캘린더", "images/icon_calendar.png", "calendar"),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
        ft.Row([
            action_btn("노무/세무", "images/icon_check.png", "work"), # Placeholder icon
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
        ft.Container(height=10),
        ft.Container(
            content=ft.ElevatedButton(
                "🆕 프로필 만들기",
                on_click=lambda _: navigate_to("create_profile"),
                width=340,
                height=50,
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.with_opacity(0.15, "#2E7D32"),
                    color="#4CAF50",
                    shape=ft.RoundedRectangleBorder(radius=12)
                )
            ),
            alignment=ft.alignment.center
        )
    ], spacing=15)

    # Remove background image if set previously
    page.decoration_image = None
    page.update()

    return [
        ft.Stack([
            # Dark Gradient Background
            ft.Container(
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_left,
                    end=ft.alignment.bottom_right,
                    colors=["#1A1A1A", "#2D3436"]
                ),
                expand=True
            ),
            ft.Column([
                header,
                ft.Container(content=grid, padding=20, expand=True)
            ], scroll=ft.ScrollMode.AUTO)
        ], expand=True)
    ]
