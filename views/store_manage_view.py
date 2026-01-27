import flet as ft
from services.channel_service import channel_service
from services.auth_service import auth_service
from db import service_supabase
from postgrest import SyncPostgrestClient
import os
from utils.logger import log_debug, log_error, log_info

def get_store_manage_controls(page: ft.Page, navigate_to):
    log_debug(f"Entering Store Manage. User: {page.session.get('user_id')}")
    """Unified Settings Page: Store Info + My Profile + Logout"""
    
    # 1. Get Context
    user_id = page.session.get("user_id")
    channel_id = page.session.get("channel_id")
    role = page.session.get("user_role")
    user_email = page.session.get("user_email") or "unknown@example.com"
    
    if not channel_id:
        return [ft.Text("매장 정보가 없습니다.")]

    # 2. Fetch Store Data
    # [FIX] Pass token for RLS
    from services.auth_service import auth_service
    token = auth_service.get_access_token()
    channels = channel_service.get_user_channels(user_id, token)
    current_ch = next((c for c in channels if c["id"] == channel_id), None)
    
    if not current_ch:
        return [ft.Text("매장 정보를 불러올 수 없습니다.")]

    # 3. Fetch User Profile Data
    user_profile = None
    try:
        res = service_supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        user_profile = res.data
    except:
        pass

    # === UI STATE ===
    
    # Store Section
    store_name_tf = ft.TextField(
        label="매장 이름", 
        value=current_ch["name"],
        read_only=(role != "owner"),
        color="black",
        border_color="#E0E0E0",
        label_style=ft.TextStyle(color="grey"),
        height=45,
        border_radius=8,
        content_padding=10,
        text_size=14
    )
    
    # Profile Section
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
    
    profile_role_dd = ft.Dropdown(
        label="내 권한",
        value=user_profile.get("role", "staff") if user_profile else "staff",
        options=[
            ft.dropdown.Option("owner", "사장님 (Owner)"),
            ft.dropdown.Option("manager", "매니저 (Manager)"),
            ft.dropdown.Option("staff", "직원 (Staff)")
        ],
        color="black",
        border_color="#E0E0E0",
        label_style=ft.TextStyle(color="grey"),
        border_radius=8,
        content_padding=10,
        text_size=14
    )
    
    # Invite Code Section
    active_codes = channel_service.get_active_invite_codes(channel_id)
    code_display = ft.Text("", selectable=True, color="#00BCD4", size=16, weight="bold")
    code_expiry = ft.Text("", size=12, color="grey")
    
    msg = ft.Text("", size=12)

    def update_code_display():
        if active_codes and len(active_codes) > 0:
            latest = active_codes[0]
            code_display.value = latest["code"]
            
            from datetime import datetime
            expires = datetime.fromisoformat(latest["expires_at"].replace("Z", "+00:00"))
            now = datetime.now(datetime.UTC)
            remaining = expires - now
            minutes = int(remaining.total_seconds() / 60)
            
            if minutes > 0:
                code_expiry.value = f"⏱ {minutes}분 후 만료 | 사용 횟수: {latest.get('used_count', 0)}회"
            else:
                code_expiry.value = "⚠ 만료됨"
                code_display.value = "만료된 코드"
        else:
            code_display.value = "생성된 코드가 없습니다"
            code_expiry.value = "새 코드를 생성하세요"
        
        page.update()
    
    update_code_display()

    # === EVENT HANDLERS ===
    
    def copy_code(e):
        if active_codes and code_display.value != "생성된 코드가 없습니다":
            page.set_clipboard(code_display.value)
            page.snack_bar = ft.SnackBar(ft.Text(f"초대 코드 복사 완료: {code_display.value}"))
            page.snack_bar.open = True
            page.update()

    def generate_new_code(e):
        log_debug(f"Generating new code for channel {channel_id} by {user_id}")
        try:
            new_code = channel_service.generate_invite_code(channel_id, user_id, duration_minutes=10)
            log_debug(f"New code generated: {new_code}")
            active_codes.clear()
            active_codes.extend(channel_service.get_active_invite_codes(channel_id))
            update_code_display()
            
            msg.value = f"새 초대 코드 생성됨: {new_code}"
            msg.color = "green"
            page.update()
        except Exception as ex:
            log_error(f"Generate Code Error: {ex}")
            msg.value = f"코드 생성 실패: {ex}"
            msg.color = "red"
            page.update()
    
    generate_btn = ft.ElevatedButton(
        "새 초대 코드 생성 (10분)", 
        icon=ft.Icons.REFRESH, 
        visible=(role in ["owner", "manager"]), 
        color="white", 
        bgcolor="#1565C0",
        height=40,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=30)),
        on_click=generate_new_code
    )

    def save_store_changes(e):
        if role != "owner":
            msg.value = "매장 정보 수정 권한이 없습니다."
            msg.color = "red"
            page.update()
            return

        try:
            channel_service.update_channel(channel_id, store_name_tf.value)
            page.session.set("channel_name", store_name_tf.value)
            msg.value = "매장 정보가 업데이트되었습니다."
            msg.color = "green"
            page.update()
        except Exception as ex:
            msg.value = f"업데이트 실패: {ex}"
            msg.color = "red"
            page.update()

    def save_profile_changes(e):
        try:
            headers = auth_service.get_auth_headers()
            if not headers:
                raise Exception("세션이 만료되었습니다. 다시 로그인해주세요.")
            
            url = os.environ.get("SUPABASE_URL")
            user_client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public", timeout=20)
            
            try:
                user_client.from_("profiles").upsert({
                    "id": user_id,
                    "full_name": profile_name_tf.value,
                    "role": profile_role_dd.value,
                    "updated_at": "now()"
                }).execute()
            finally:
                try: user_client.session.close()
                except: pass
            
            # Update session with new display name
            page.session.set("display_name", profile_name_tf.value)
            
            msg.value = f"프로필 저장 완료! (권한: {profile_role_dd.value})"
            msg.color = "green"
            page.update()
            
        except Exception as ex:
            msg.value = f"프로필 저장 실패: {ex}"
            msg.color = "red"
            page.update()

    def perform_logout(e):
        try:
            auth_service.sign_out()
            page.session.clear()
            page.client_storage.remove("supa_session")
            navigate_to("login")
        except Exception as ex:
            print(f"Logout error: {ex}")
            # Force logout anyway
            page.session.clear()
            navigate_to("login")

    # === CREATE NEW STORE DIALOG ===
    new_store_name = ft.TextField(label="새 매장 이름")
    
    def perform_create(e):
        if not new_store_name.value:
            return
        
        try:
            new_ch = channel_service.create_channel(user_id, new_store_name.value)
            page.session.set("channel_id", new_ch["id"])
            page.session.set("channel_name", new_ch["name"])
            page.session.set("user_role", "owner")
            
            page.close(create_dialog)
            page.snack_bar = ft.SnackBar(ft.Text(f"새 매장 '{new_ch['name']}'으로 전환되었습니다."))
            page.snack_bar.open = True
            navigate_to("home")
            
        except Exception as ex:
            print(f"Create Error: {ex}")

    create_dialog = ft.AlertDialog(
        title=ft.Text("새 매장 추가"),
        content=ft.Column([
            ft.Text("새로운 매장을 만들어 관리하세요."),
            new_store_name
        ], height=100),
        actions=[
            ft.TextButton("취소", on_click=lambda _: page.close(create_dialog)),
            ft.ElevatedButton("생성하기", on_click=perform_create)
        ]
    )

    def open_create_dialog(e):
        page.open(create_dialog)

    # === LAYOUT ===
    return [
        ft.Container(
            expand=True,
            bgcolor="white",
            padding=20,
            content=ft.Column([
                # Header
                ft.Row([
                    ft.IconButton(ft.Icons.ARROW_BACK, icon_color="black", on_click=lambda _: navigate_to("home")),
                    ft.Text("설정", size=24, weight="bold", color="#0A1929", expand=True),
                    ft.IconButton(
                        ft.Icons.LOGOUT, 
                        icon_color="red", 
                        on_click=perform_logout,
                        tooltip="로그아웃"
                    )
                ]),
                
                ft.Divider(color="#EEEEEE"),
                
                # === SECTION 1: STORE INFO ===
                ft.Container(
                    padding=20,
                    border=ft.border.all(1, "#EEEEEE"),
                    border_radius=10,
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.STORE, color="#0A1929"),
                            ft.Text("매장 정보", size=18, weight="bold", color="#0A1929")
                        ]),
                        ft.Container(height=10),
                        ft.Row([
                            ft.Container(store_name_tf, expand=True),
                            ft.ElevatedButton("저장", on_click=save_store_changes, visible=(role=="owner"), bgcolor="#00C73C", color="white", height=40, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=30))),
                        ]),
                        
                        ft.Container(height=10),
                        ft.Text("직원 초대 관리", size=16, weight="bold", color="#0A1929"),
                        ft.Text("초대 코드는 생성 후 10분간 유효합니다.", size=12, color="grey"),
                        ft.Container(
                            padding=15,
                            bgcolor=ft.Colors.with_opacity(0.05, "#1565C0"),
                            border_radius=8,
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.Icons.QR_CODE, color="cyan"),
                                    code_display
                                ]),
                                code_expiry,
                                ft.Row([
                                    generate_btn,
                                    ft.IconButton(ft.Icons.COPY, icon_color="cyan", on_click=copy_code, tooltip="코드 복사")
                                ])
                            ], spacing=5)
                        )
                    ])
                ),
                
                ft.Divider(color="white12", height=5),
                
                # === SECTION 2: MY PROFILE ===
                ft.Container(
                    padding=20,
                    border=ft.border.all(1, "white12"),
                    border_radius=10,
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.PERSON, color="#0A1929"),
                            ft.Text("내 프로필", size=18, weight="bold", color="#0A1929")
                        ]),
                        ft.Container(height=10),
                        ft.Text(f"이메일: {user_email}", size=12, color="grey"),
                        ft.Container(height=10),
                        ft.Row([
                            ft.Container(profile_name_tf, expand=True),
                            ft.Container(profile_role_dd, width=160),
                            ft.ElevatedButton("저장", on_click=save_profile_changes, bgcolor="#00C73C", color="white", height=40, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=30))),
                        ]),
                    ])
                ),
                
                msg,
                
                ft.Divider(color="white12", height=5),
                
                # === SECTION 3: ADD NEW STORE ===
                ft.Container(
                    padding=20,
                    bgcolor=ft.Colors.with_opacity(0.05, "#1565C0"),
                    border_radius=10,
                    content=ft.Row([
                        ft.Column([
                            ft.Text("또 다른 매장이 있으신가요?", weight="bold", color="grey"),
                            ft.Text("새로운 매장을 추가하고 간편하게 전환하세요.", size=12, color="grey")
                        ], expand=True),
                        ft.ElevatedButton("새 매장 추가하기", icon=ft.Icons.ADD_BUSINESS, on_click=open_create_dialog, bgcolor="#1565C0", color="white", height=40, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=30)))
                    ])
                )

            ], scroll=ft.ScrollMode.AUTO)
        )
    ]
