import flet as ft

def get_closing_controls(page: ft.Page, navigate_to):
    checklist = ft.Column([
        ft.Container(
            content=ft.Checkbox(label="주방 가스 밸브 차단 확인", label_style=ft.TextStyle(color="white")),
            padding=15, bgcolor=ft.Colors.with_opacity(0.1, "white"), border_radius=10
        ),
        ft.Container(
            content=ft.Checkbox(label="홀 에어컨 및 조명 OFF 확인", label_style=ft.TextStyle(color="white")),
            padding=15, bgcolor=ft.Colors.with_opacity(0.1, "white"), border_radius=10
        ),
    ], spacing=10)

    header = ft.Row([
        ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW, icon_color="white", on_click=lambda _: navigate_to("home")),
        ft.Text("마감 안전 점검", size=24, weight="bold", color="white")
    ])

    return [
        ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_center,
                end=ft.alignment.bottom_center,
                colors=["#1A1A1A", "#2D3436"]
            ),
            padding=30,
            content=ft.Column([
                header,
                ft.Container(height=30),
                ft.Text("Safety Checklist", color="white70", size=14),
                checklist,
                ft.Container(height=40),
                ft.ElevatedButton(
                    "점검 완료 및 퇴근", 
                    on_click=lambda _: navigate_to("home"), 
                    width=400, height=60,
                    style=ft.ButtonStyle(
                        color="white",
                        bgcolor="#00C73C",
                        shape=ft.RoundedRectangleBorder(radius=12)
                    )
                )
            ])
        )
    ]
