import flet as ft
from utils.logger import log_debug
from views.components.custom_checkbox import CustomCheckbox

def get_closing_controls(page: ft.Page, navigate_to):
    log_debug(f"Entering Closing View. User: {page.session.get('user_id')}")
    checklist = ft.Column([
        ft.Container(
            content=CustomCheckbox(label="주방 가스 밸브 차단 확인", label_style=ft.TextStyle(color="black")),
            padding=15, bgcolor="#EEEEEE", border_radius=10
        ),
        ft.Container(
            content=CustomCheckbox(label="홀 에어컨 및 조명 OFF 확인", label_style=ft.TextStyle(color="black")),
            padding=15, bgcolor="#EEEEEE", border_radius=10
        ),
    ], spacing=10)
    
    is_confirmed = ft.Ref[CustomCheckbox]()
    complete_button = ft.Ref[ft.ElevatedButton]()
    
    def toggle_confirm(e):
        if is_confirmed.current.value:
            complete_button.current.disabled = False
        else:
            complete_button.current.disabled = True
        page.update()

    header = ft.Row([
        ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW, icon_color="black", on_click=lambda _: navigate_to("home")),
        ft.Text("체크리스트", size=24, weight="bold", color="#0A1929")
    ])

    return [
        ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_center,
                end=ft.alignment.bottom_center,
                colors=["white", "#F5F5F5"]
            ),
            padding=30,
            content=ft.Column([
                header,
                ft.Container(height=10),
                ft.Text("Safety Checklist", color="grey", size=14),
                checklist,
                ft.Container(height=40),
                CustomCheckbox(
                    ref=is_confirmed,
                    label="마감 확인 (위 내용을 모두 확인했습니다)",
                    value=False, # Initially unchecked
                    on_change=toggle_confirm,
                    label_style=ft.TextStyle(color="black")
                ),
                ft.ElevatedButton(
                    ref=complete_button,
                    text="점검 완료 및 퇴근", 
                    on_click=lambda _: navigate_to("home"), 
                    width=400, height=45,
                    disabled=True, 
                    style=ft.ButtonStyle(
                        color="white",
                        bgcolor="#00C73C",
                        shape=ft.RoundedRectangleBorder(radius=8)
                    )
                )
            ], scroll=ft.ScrollMode.AUTO, expand=True)
        )
    ]
