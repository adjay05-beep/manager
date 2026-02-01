import flet as ft

async def get_order_controls(page: ft.Page, navigate_to):
    # [Placeholder] Order Management View
    
    return [
        ft.Container(
            expand=True,
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to("home"), icon_color="black"),
                        ft.Text("발주 관리", size=24, weight="bold", color="#0A1929"),
                    ]),
                    padding=10,
                    border=ft.border.only(bottom=ft.border.BorderSide(1, "#EEEEEE"))
                ),
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Column([
                        ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=64, color="grey"),
                        ft.Text("발주/재고 관리 기능 준비 중입니다.", size=16, color="grey"),
                        ft.ElevatedButton("홈으로 돌아가기", on_click=lambda _: navigate_to("home"), height=40, bgcolor="#1565C0", color="white")
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20, scroll=ft.ScrollMode.AUTO, expand=True)
                )
            ])
        )
    ]
