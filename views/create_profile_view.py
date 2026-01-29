import flet as ft
from db import service_supabase as supabase

def get_create_profile_controls(page: ft.Page, navigate_to, user_id, user_email):
    """프로필 생성 화면"""
    
    name_input = ft.TextField(
        label="이름",
        hint_text="실명을 입력하세요",
        autofocus=True,
        width=300,
        text_align=ft.TextAlign.LEFT
    )
    
    role_dropdown = ft.Dropdown(
        label="역할",
        width=300,
        value="staff",
        options=[
            ft.dropdown.Option("staff", "직원"),
            ft.dropdown.Option("manager", "매니저"),
            ft.dropdown.Option("admin", "관리자")
        ]
    )
    
    status_text = ft.Text("", color="green", size=14, text_align=ft.TextAlign.CENTER)
    
    def create_profile(e):
        if not name_input.value:
            status_text.value = "❌ 이름을 입력해주세요"
            status_text.color = "red"
            page.update()
            return
        
        try:
            # 프로필 생성
            result = supabase.table("profiles").insert({
                "id": user_id,
                "full_name": name_input.value,
                "role": role_dropdown.value
            }).execute()
            
            if result.data:
                status_text.value = "✅ 프로필 생성 완료!"
                status_text.color = "green"
                page.update()
                
                # 2초 후 홈으로 이동
                import time
                time.sleep(2)
                navigate_to("home")
            else:
                status_text.value = "❌ 프로필 생성 실패"
                status_text.color = "red"
                page.update()
                
        except Exception as ex:
            error_msg = str(ex)
            if "duplicate" in error_msg or "already exists" in error_msg:
                status_text.value = "✅ 프로필이 이미 존재합니다!"
                status_text.color = "green"
                page.update()
                import time
                time.sleep(2)
                navigate_to("home")
            else:
                status_text.value = f"❌ 오류: {ex}"
                status_text.color = "red"
                page.update()
    
    return [
        ft.SafeArea(expand=True, content=
        ft.Container(
            content=ft.Column(
                [
                    ft.Container(height=60),
                    ft.Icon(ft.Icons.PERSON_ADD, size=50, color="#1565C0"),
                    ft.Text("프로필 만들기", size=28, weight="bold", color="#0A1929"),
                    ft.Text("가입을 완료하기 위해 프로필을 설정해주세요.", color="grey"),
                    ft.Text(f"환영합니다! {user_email}", size=14, color="#BDBDBD"),
                    ft.Container(height=30),
                    
                    name_input,
                    ft.Container(height=10),
                    role_dropdown,
                    ft.Container(height=20),
                    
                    ft.ElevatedButton(
                        "프로필 만들기",
                        on_click=create_profile,
                        width=300,
                        height=50,
                        bgcolor="white",
                        color="black",
                        border_color="grey",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=8)
                        )
                    ),
                    ft.Container(height=10),
                    status_text,
                    ft.Container(height=20),
                    ft.TextButton(
                        "나중에 하기",
                        on_click=lambda _: navigate_to("home"),
                        style=ft.ButtonStyle(color="#BDBDBD")
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.START
            ),
            expand=True,
            bgcolor="white",
            padding=20
        )
        )
    ]
