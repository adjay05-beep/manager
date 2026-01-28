import flet as ft
from services.channel_service import channel_service
from services.auth_service import auth_service
from db import service_supabase
import os

def get_profile_controls(page: ft.Page, navigate_to):
    """Profile View: User Profile + Store List"""
    
    user_id = page.session.get("user_id")
    channel_id = page.session.get("channel_id")
    user_email = page.session.get("user_email") or "unknown@example.com"
    
    # Fetch User Profile
    user_profile = None
    try:
        res = service_supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        user_profile = res.data
    except: pass

    # Fetch User Channles
    token = auth_service.get_access_token()
    channels = channel_service.get_user_channels(user_id, token)

    # UI Components
    profile_name_tf = ft.TextField(
        label="내 이름",
        value=user_profile.get("full_name", "") if user_profile else "",
        color="black",
        border_color="#E0E0E0",
        label_style=ft.TextStyle(color="grey"),
        height=45,
        border_radius=8,
        content_padding=10,
        text_size=14
    )

    def save_profile_changes(e):
        try:
            service_supabase.table("profiles").upsert({
                "id": user_id,
                "full_name": profile_name_tf.value,
                "updated_at": "now()"
            }).execute()
            page.session.set("display_name", profile_name_tf.value)
            page.snack_bar = ft.SnackBar(ft.Text("프로필이 저장되었습니다."), bgcolor="green"); 
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            print(ex)

    def perform_logout(e):
        auth_service.sign_out()
        page.session.clear()
        page.client_storage.remove("supa_session")
        navigate_to("login")

    def perform_create_store(e):
        # Open Create Store Dialog (Reusing logic or navigating)
        # For simplicity, navigate to a create store page or open dialog here.
        # Ideally, reuse the dialog from store_manage_view or make it shared.
        # I'll just navigate to onboarding for now or implement a simple dialog.
        # Since I am creating a new file, I'll implement a simple dialog.
        pass # To be implemented if needed, or link to Onboarding

    # 1. Profile Card
    profile_card = ft.Container(
        padding=20,
        content=ft.Row([
            ft.Container(
                content=ft.Icon(ft.Icons.PERSON, size=40, color="white"),
                width=70, height=70, bgcolor="#E0E0E0", border_radius=35,
                alignment=ft.alignment.center
            ),
            ft.Container(width=10),
            ft.Column([
                 ft.Row([
                     ft.Text(user_profile.get("full_name", "이름 없음"), size=20, weight="bold", color="#1A1A1A"),
                     ft.IconButton(ft.Icons.EDIT, icon_color="grey", icon_size=18, tooltip="이름 수정", on_click=lambda _: page.open(edit_profile_dialog)) 
                 ], spacing=0, alignment=ft.MainAxisAlignment.START),
                 ft.Container(
                     content=ft.Text(f"{user_profile.get('role', 'staff')}", size=12, color="white"),
                     bgcolor="grey", padding=ft.padding.symmetric(horizontal=8, vertical=2), border_radius=10
                 ),
            ], spacing=5),
        ])
    )

    edit_profile_dialog = ft.AlertDialog(
        title=ft.Text("프로필 수정"),
        content=profile_name_tf,
        actions=[
            ft.TextButton("저장", on_click=lambda e: [save_profile_changes(e), page.close(edit_profile_dialog)])
        ]
    )

    # 2. Store List
    store_list_items = []
    if channels:
        for ch in channels:
            is_current = (ch['id'] == channel_id)
            store_list_items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.STORE, color="#1565C0" if is_current else "grey"),
                        ft.Text(ch['name'], weight="bold" if is_current else "normal", color="black"),
                        ft.Container(expand=True),
                         ft.Text("현재 접속 중" if is_current else "", size=12, color="#1565C0")
                    ]),
                    padding=10,
                    border=ft.border.only(bottom=ft.border.BorderSide(1, "#EEEEEE")),
                    # Logic to switch store could be added here
                    on_click=lambda e, cid=ch['id'], cname=ch['name']: switch_store(cid, cname)
                )
            )
    else:
        store_list_items.append(ft.Text("가입된 매장이 없습니다.", color="grey"))

    def switch_store(cid, cname):
        page.session.set("channel_id", cid)
        page.session.set("channel_name", cname)
        # Refresh role?
        # Ideally we fetch role for new channel.
        # For now just reload
        navigate_to("home")

    return [
        ft.SafeArea(
            ft.Container(
                expand=True,
                bgcolor="white",
                content=ft.Column([
                    # Header
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=10, vertical=10),
                        content=ft.Row([
                            ft.IconButton(ft.Icons.ARROW_BACK, icon_color="black", on_click=lambda _: navigate_to("home")),
                            ft.Text("내 프로필", size=20, weight="bold", expand=True, color="black"),
                            ft.TextButton("로그아웃", icon=ft.Icons.LOGOUT, icon_color="red", style=ft.ButtonStyle(color="red"), on_click=perform_logout)
                        ])
                    ),
                    ft.Divider(color="#EEEEEE", height=1),
                    
                    profile_card,
                    ft.Divider(color="#EEEEEE", thickness=5),
                    
                    ft.Container(
                        padding=20,
                        content=ft.Column([
                            ft.Text("내 매장 목록", size=16, weight="bold", color="#0A1929"),
                            ft.Column(store_list_items, spacing=0),
                            ft.Container(height=10),
                            ft.OutlinedButton("새 매장 만들기", icon=ft.Icons.ADD, on_click=lambda _: navigate_to("onboarding"), width=200)
                        ])
                    )
                ], scroll=ft.ScrollMode.AUTO)
            )
        )
    ]
