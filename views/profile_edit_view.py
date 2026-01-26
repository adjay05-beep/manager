import flet as ft
from services.auth_service import auth_service
from db import service_supabase

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
    role_dd = ft.Dropdown(
        label="권한 (Role)",
        width=300,
        options=[
            ft.dropdown.Option("owner", "사장님 (Owner)"),
            ft.dropdown.Option("staff", "직원 (Staff)"),
        ],
        value=profile_data.get("role", "staff")
    )
    
    msg = ft.Text("", size=12)

    def save(e):
        try:
            print(f"DEBUG: Updating profile for {user.id} -> Role: {role_dd.value}")
            
            # 1. Update
            res_update = service_supabase.table("profiles").update({
                "full_name": name_tf.value,
                "role": role_dd.value
            }).eq("id", user.id).execute()
            
            # 2. Verify Update (Read back)
            # Use 'supabase' (standard client) to verify RLS visibility if desired, 
            # but let's stick to service_supabase to confirm DATA persistence first.
            res_verify = service_supabase.table("profiles").select("role").eq("id", user.id).single().execute()
            
            new_role = res_verify.data.get("role") if res_verify.data else "unknown"
            print(f"DEBUG: Verification Read -> Role: {new_role}")

            if new_role != role_dd.value:
                raise Exception(f"업데이트 실패: DB 값이 변경되지 않았습니다. ({new_role})")

            msg.value = f"저장 완료! (현재 권한: {new_role})"
            msg.color = "green"
            page.update()
            
            import time
            time.sleep(1)
            navigate_to("home")
            
        except Exception as ex:
            print(f"ERROR: Profile Update Failed: {ex}")
            msg.value = f"API 오류: {ex}"
            msg.color = "red"
            page.update()

    return [
        ft.Column([
            ft.Container(height=40),
            ft.Text("프로필 수정", size=30, weight="bold", color="white"),
            ft.Text("잘못된 권한을 여기서 수정할 수 있습니다.", color="white70"),
            ft.Container(height=20),
            name_tf,
            role_dd,
            ft.Container(height=20),
            ft.ElevatedButton("저장하기", on_click=save, bgcolor="#00C73C", color="white", width=300, height=45),
            ft.TextButton("취소", on_click=lambda _: navigate_to("home")),
            msg
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    ]
