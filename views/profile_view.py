import flet as ft
import asyncio
from services.channel_service import channel_service
from services.auth_service import auth_service
from db import service_supabase
from views.components.app_header import AppHeader
from views.styles import AppColors, AppLayout
import os

async def get_profile_controls(page: ft.Page, navigate_to):
    """Profile View: User Profile + Store List"""
    
    user_id = page.app_session.get("user_id")
    channel_id = page.app_session.get("channel_id")
    user_email = page.app_session.get("user_email") or "unknown@example.com"
    
    # Fetch User Profile
    user_profile = None
    try:
        res = await asyncio.to_thread(lambda: service_supabase.table("profiles").select("*").eq("id", user_id).single().execute())
        user_profile = res.data
    except Exception:
        pass  # Profile fetch failed

    # Fetch User Channels
    token = auth_service.get_access_token()
    channels = await asyncio.to_thread(lambda: channel_service.get_user_channels(user_id, token))

    # --- [NEW] Contract Info Fetching ---
    contract_info_container = ft.Column(spacing=10)
    
    def get_contract_ui(contract):
        if not contract:
            return ft.Container(
                content=ft.Text("등록된 계약 내용이 없습니다.", color="grey", size=13),
                padding=10
            )
        
        days_map = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}
        w_days = [days_map[d] for d in contract.get('work_days', []) if d in days_map]
        day_str = ", ".join(w_days) if w_days else "없음"
        
        wage_type_kr = "시급" if contract.get("wage_type") == "hourly" else "월급"
        wage_val = contract.get("hourly_wage") or contract.get("monthly_wage") or 0
        emp_type_kr = "정규직" if contract.get("employee_type") == "full" else "아르바이트"

        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Text(emp_type_kr, size=12, weight="bold", color="white"),
                    ]), 
                    bgcolor=AppColors.PRIMARY, 
                    padding=ft.padding.symmetric(horizontal=8, vertical=2), 
                    border_radius=5,
                    width=80 if emp_type_kr == "정규직" else 90 # Adjust width for label
                ),
                ft.Row([
                    ft.Icon(ft.Icons.PAYMENTS_OUTLINED, size=16, color="grey"),
                    ft.Text(f"{wage_type_kr}: {wage_val:,}원", size=14, color="black", weight="bold"),
                ]),
                ft.Row([
                    ft.Icon(ft.Icons.CALENDAR_MONTH_OUTLINED, size=16, color="grey"),
                    ft.Text(f"근무 요일: {day_str}", size=14, color="black"),
                ]),
                ft.Row([
                    ft.Icon(ft.Icons.PLAY_ARROW_OUTLINED, size=16, color="grey"),
                    ft.Text(f"근무 시작일: {contract.get('contract_start_date', '-')}", size=14, color="black"),
                ]),
            ], spacing=8),
            padding=15,
            border=ft.border.all(1, "#EEEEEE"),
            border_radius=10,
            bgcolor="#F9FAFB"
        )

    async def load_contract_async():
        try:
            # We filter by both user_id and channel_id to get the contract for THIS store
            res = service_supabase.table("labor_contracts")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("channel_id", channel_id)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            contract = res.data[0] if res.data else None
            contract_info_container.controls = [get_contract_ui(contract)]
            page.update()
        except Exception as ex:
            print(f"Profile Contract Fetch Error: {ex}")
            contract_info_container.controls = [ft.Text("계약 정보를 불러오는 중 오류가 발생했습니다.", color="red", size=12)]
            page.update()

    asyncio.create_task(load_contract_async())
    # ------------------------------------

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

    async def save_profile_changes(e):
        try:
            await asyncio.to_thread(lambda: service_supabase.table("profiles").upsert({
                "id": user_id,
                "full_name": profile_name_tf.value,
                "updated_at": "now()"
            }).execute())
            page.app_session["display_name"] = profile_name_tf.value
            page.snack_bar = ft.SnackBar(ft.Text("프로필이 저장되었습니다."), bgcolor="green");
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            print(ex)

    def perform_logout(e):
        auth_service.sign_out()
        # Clear app_session dict
        page.app_session.clear()
        try:
            page.client_storage.remove("supa_session")
        except:
            pass
        asyncio.create_task(navigate_to("login"))

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
                alignment=ft.Alignment(0, 0)
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
            ft.TextButton("저장", on_click=lambda e: asyncio.create_task(save_profile_changes(e) if hasattr(save_profile_changes, '__await__') else save_profile_changes(e)))
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
                    on_click=lambda e, cid=ch['id'], cname=ch['name']: asyncio.create_task(switch_store(cid, cname))
                )
            )
    else:
        store_list_items.append(ft.Text("가입된 매장이 없습니다.", color="grey"))

    async def switch_store(cid, cname):
        page.app_session["channel_id"] = cid
        page.app_session["channel_name"] = cname
        # Refresh role?
        # Ideally we fetch role for new channel.
        # For now just reload
        await navigate_to("home")

    return [
        ft.SafeArea(expand=True, content=
            ft.Container(
                expand=True,
                bgcolor="white",
                content=ft.Column([
                    # Header
                    AppHeader("내 프로필", on_back_click=lambda _: asyncio.create_task(page.go_back() if hasattr(page, "go_back") else navigate_to("home"))),
                    
                    profile_card,
                    
                    # [NEW] Contract Section
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=20, vertical=10),
                        content=ft.Column([
                            ft.Text("나의 계약 정보", size=16, weight="bold", color="#0A1929"),
                            contract_info_container
                        ])
                    ),

                    ft.Divider(color="#EEEEEE", thickness=5),
                    
                    ft.Container(
                        padding=20,
                        content=ft.Column([
                            ft.Text("내 매장 목록", size=16, weight="bold", color="#0A1929"),
                            ft.Column(store_list_items, spacing=0),
                            ft.Container(height=10),
                            ft.OutlinedButton("새 매장 만들기", icon=ft.Icons.ADD, on_click=lambda _: asyncio.create_task(navigate_to("onboarding")), width=200)
                        ])
                    )
                ], scroll=ft.ScrollMode.AUTO)
            )
        )
    ]
