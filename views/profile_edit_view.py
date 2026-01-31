import flet as ft
import os
from services.auth_service import auth_service
from db import service_supabase, url
from postgrest import SyncPostgrestClient

def get_profile_edit_controls(page: ft.Page, navigate_to):
    user = auth_service.get_user()
    if not user:
        navigate_to("login")
        return []

    # Fetch current profile
    profile_data = {}
    try:
        res = service_supabase.table("profiles").select("*").eq("id", user.id).single().execute()
        if res.data: profile_data = res.data
    except Exception as e:
        print(f"Profile Load Error: {e}")

    # Controls
    name_tf = ft.TextField(label="이름", value=profile_data.get("full_name", ""), width=300)
    # [SECURITY] role은 표시만 하고 수정 불가 (채널 주인만 멤버 등급 변경 가능)
    current_role = profile_data.get("role", "staff")
    role_display = ft.TextField(
        label="권한 (Role)",
        width=300,
        value="사장님 (Owner)" if current_role == "owner" else "매니저 (Manager)" if current_role == "manager" else "직원 (Staff)",
        read_only=True,
        hint_text="등급 변경은 채널 관리에서 가능합니다"
    )
    
    msg = ft.Text("", size=12)

    def save(e):
        try:
            # [FIX] Use Authenticated Request via AuthService
            # This handles session retrieval and formatting centrally
            headers = auth_service.get_auth_headers()
            if not headers:
                raise Exception("세션이 만료되었습니다. 다시 로그인해주세요.")
            
            # Use this client for the upsert
            user_client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public", timeout=20)
            
            try:
                # [SECURITY] role은 제외 - 이름만 업데이트
                res_update = user_client.from_("profiles").upsert({
                    "id": user.id,
                    "full_name": name_tf.value,
                    "updated_at": "now()"
                }).execute()
            finally:
                try: user_client.session.close()
                except Exception: pass

            msg.value = "저장 완료!"
            msg.color = "green"
            page.update()

            navigate_to("home")
            
        except Exception as ex:
            print(f"ERROR: Profile Update Failed: {ex}")
            msg.value = f"API 오류: {ex}"
            msg.color = "red"
            page.update()

    return [
        ft.Container(
            expand=True,
            bgcolor="white",
            padding=20,
            content=ft.Column([
                ft.Container(height=40),
                ft.Text("프로필 수정", size=30, weight="bold", color="#0A1929"),
                ft.Text("이름을 수정할 수 있습니다.", color="black"),
                ft.Container(height=20),
                name_tf,
                role_display,
                ft.Container(height=20),
                ft.ElevatedButton("저장하기", on_click=save, bgcolor="#00C73C", color="white", width=300, height=45),
                ft.TextButton("취소", on_click=lambda _: navigate_to("home")),
                msg
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
    ]
