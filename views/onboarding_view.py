import flet as ft
from services.channel_service import channel_service
from services.auth_service import auth_service

def get_onboarding_controls(page: ft.Page, navigate_to):
    current_user_id = page.session.get("user_id")
    
    # State
    join_code_tf = ft.TextField(label="매장 초대 코드 (예: STORE-1234)", text_align=ft.TextAlign.CENTER)
    create_name_tf = ft.TextField(label="새 매장 이름", text_align=ft.TextAlign.CENTER)
    
    error_text = ft.Text("", color="red", size=12)
    
    def on_join(e):
        code = join_code_tf.value
        if not code:
            error_text.value = "초대 코드를 입력해주세요."
            page.update()
            return

        try:
            ch = channel_service.join_channel(current_user_id, code)
            complete_login(ch)
        except Exception as ex:
            error_text.value = f"가입 실패: {ex}"
            page.update()

    def on_create(e):
        name = create_name_tf.value
        if not name:
            error_text.value = "매장 이름을 입력해주세요."
            page.update()
            return

        try:
            ch = channel_service.create_channel(current_user_id, name)
            complete_login(ch)
        except Exception as ex:
            error_text.value = f"생성 실패: {ex}"
            page.update()

    def complete_login(ch):
        page.session.set("channel_id", ch["id"])
        page.session.set("channel_name", ch["name"])
        page.session.set("user_role", ch["role"])
        page.snack_bar = ft.SnackBar(ft.Text(f"환영합니다! {ch['name']}에 접속했습니다."), open=True)
        page.update()
        navigate_to("home")

    # UI Components
    return [
        ft.Container(
            expand=True,
            bgcolor="white", # Clean White Theme
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.STOREFRONT_OUTLINED, size=64, color="#0A1929"),
                    ft.Text("환영합니다!", size=24, weight="bold", color="#0A1929"),
                    ft.Text("시작하려면 매장을 생성하거나 가입하세요.", size=14, color="grey"),
                    ft.Container(height=30),
                    
                    # Section 1: Create
                    ft.Container(
                        padding=20,
                        border=ft.border.all(1, "#EEEEEE"),
                        border_radius=10,
                        content=ft.Column([
                            ft.Text("새 매장 만들기 (사장님)", weight="bold", color="#0A1929"),
                            create_name_tf,
                            ft.ElevatedButton("매장 생성하기", on_click=on_create, width=200, height=45, bgcolor="#1565C0", color="white")
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                    ),
                    
                    ft.Text("OR", weight="bold", color="grey"),
                    
                    # Section 2: Join
                    ft.Container(
                        padding=20,
                        border=ft.border.all(1, "#EEEEEE"),
                        border_radius=10,
                        content=ft.Column([
                            ft.Text("기존 매장 합류 (직원)", weight="bold", color="#0A1929"),
                            join_code_tf,
                            ft.OutlinedButton("초대 코드로 입장", on_click=on_join, width=200, height=45, style=ft.ButtonStyle(color="#0A1929", side=ft.BorderSide(1, "#0A1929")))
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                    ),
                    
                    ft.Container(height=10),
                    error_text,
                    ft.TextButton("로그아웃", on_click=lambda _: navigate_to("login"))
                    
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20
            ),
            padding=20
        )
    ]
