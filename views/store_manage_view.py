import flet as ft
from services.channel_service import channel_service
from services.auth_service import auth_service
from db import service_supabase
from postgrest import SyncPostgrestClient
import os
from utils.logger import log_debug, log_error, log_info
from views.styles import AppColors, AppTextStyles, AppLayout
from views.components.app_header import AppHeader

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
    except Exception as e:
        log_error(f"Failed to fetch user profile: {e}")

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
    
    profile_role_tf = ft.TextField(
        label="등급",
        value=user_profile.get("role", "staff") if user_profile else "staff",
        read_only=True,
        color="black",
        border_color="#E0E0E0",
        label_style=ft.TextStyle(color="grey"),
        height=45,
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
            
            from datetime import datetime, timezone
            expires = datetime.fromisoformat(latest["expires_at"].replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
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
                    "updated_at": "now()"
                }).execute()
            finally:
                try:
                    user_client.session.close()
                except Exception:
                    pass  # Session cleanup
            
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

    # === MEMBER MANAGEMENT (Owner Only) ===
    member_mgmt_col = ft.Column(spacing=10)
    current_members_data = [] # Store for transfer dialog

    def open_transfer_dialog(e):
        candidates = [m for m in current_members_data if m["user_id"] != user_id]
        if not candidates:
            page.snack_bar = ft.SnackBar(ft.Text("양도할 멤버가 없습니다."))
            page.snack_bar.open = True
            page.update()
            return
            
        selected_candidate = [None] # Mutable container
        
        def set_candidate(e):
            selected_candidate[0] = e.control.value

        def final_transfer_confirm(e):
            if not selected_candidate[0]: return
            try:
                # Call service logic
                token = auth_service.get_access_token()
                channel_service.transfer_channel_ownership(channel_id, selected_candidate[0], token=token)
                
                page.close(dlg_confirm)
                page.close(dlg_transfer)
                
                page.snack_bar = ft.SnackBar(ft.Text("매장 권한을 양도했습니다."))
                page.snack_bar.open = True
                page.update()
                
                navigate_to("home") 
            except Exception as ex:
                page.close(dlg_confirm)
                page.snack_bar = ft.SnackBar(ft.Text(f"양도 실패: {ex}"))
                page.snack_bar.open = True
                page.update()

        def do_transfer_check(e):
            if not selected_candidate[0]: 
                page.snack_bar = ft.SnackBar(ft.Text("새 대표를 선택해주세요."))
                page.snack_bar.open = True
                page.update()
                return
                
            # Find name for confirmation message
            target_name = "Unknown"
            for m in candidates:
                if m["user_id"] == selected_candidate[0]:
                    target_name = m.get("full_name", "Unknown")
                    break
            
            dlg_confirm = ft.AlertDialog(
                title=ft.Text("양도 확인"),
                content=ft.Text(f"정말 '{target_name}'님에게 매장 대표 권한을 양도하시겠습니까?\n\n양도 후 귀하는 '관리자' 등급으로 변경되며, 이 작업은 되돌릴 수 없습니다."),
                actions=[
                    ft.TextButton("취소", on_click=lambda _: page.close(dlg_confirm)),
                    ft.ElevatedButton("확인 (양도)", bgcolor="red", color="white", on_click=final_transfer_confirm)
                ]
            )
            # Make the variable available to the inner function by attaching it to page or similar referencing?
            # Actually inner function captures variables from enclosing scope. 
            # We need to register 'dlg_confirm' variable so we can close it. 
            # Since create_dialog is local, we need to pass it or declare it before.
            # Python closure will capture the variable name, but it must be assigned before use.
            # Let's use page.open(dlg_confirm) and rely on lambda capturing.
            
            page.open(dlg_confirm)

        dlg_transfer = ft.AlertDialog(
            title=ft.Text("매장 대표 권한 양도"),
            content=ft.Column([
                ft.Text("권한을 받을 새 대표를 선택하세요."),
                ft.Dropdown(
                    label="새 대표 선택",
                    width=280,
                    options=[
                        ft.dropdown.Option(m["user_id"], m.get("full_name") or "Unknown") 
                        for m in candidates
                    ],
                    on_change=set_candidate
                ),
                ft.Text("주의: 양도 후 귀하는 '관리자' 등급으로 변경됩니다.", color="red", size=12)
            ], height=150),
            actions=[
                ft.TextButton("취소", on_click=lambda _: page.close(dlg_transfer)),
                ft.ElevatedButton("양도 확인", bgcolor="red", color="white", on_click=do_transfer_check)
            ]
        )
        page.open(dlg_transfer)

    def load_members():
        print(f"DEBUG_VIEW: Inside load_members. Role={role}")
        if role != "owner": return
        try:
            # [Fix] Pass token for RLS
            token = auth_service.get_access_token()
            members = channel_service.get_channel_members_with_profiles(channel_id, access_token=token)
            
            # [Iteration 28 Refresh] Sort by rank precedence: owner(0) > manager(1) > staff(2)
            precedence = {"owner": 0, "manager": 1, "staff": 2}
            members.sort(key=lambda x: precedence.get(x.get("role"), 9))
            
            current_members_data.clear()
            items = []
            for m in members:
                uid = m["user_id"]
                u_role = m["role"]
                is_me = (uid == user_id)
                current_members_data.append(m) # Store for transfer
                
                # Role Display Mapping check
                if u_role == "owner": role_label = "대표"
                elif u_role == "manager": role_label = "관리자"
                else: 
                    role_label = "멤버"
                    # Normalize u_role for dropdown value matching
                    if u_role not in ["manager", "staff"]:
                        u_role = "staff" 
                
                # UI for Role Selection
                if u_role == "owner":
                    # Representative is shown as text, not a dropdown
                    role_selector = ft.Container(
                        content=ft.Text("대표", weight="bold", size=14, color="#2196F3"),
                        width=100, 
                        alignment=ft.alignment.center
                    )
                else:
                    role_selector = ft.Dropdown(
                        value=u_role,
                        options=[
                            ft.dropdown.Option("manager", "관리자"),
                            ft.dropdown.Option("staff", "멤버")
                        ],
                        width=110,
                        content_padding=ft.padding.symmetric(horizontal=10, vertical=0),
                        text_size=13,
                        text_style=ft.TextStyle(weight=ft.FontWeight.BOLD),
                        dense=True,
                        border_radius=8,
                        on_change=lambda e, uid=uid: update_member_role(uid, e.control.value),
                        disabled=is_me # Technically redundant if owner is filtered above, but keeps logic safe
                    )
                
                kick_btn = ft.IconButton(
                    ft.Icons.REMOVE_CIRCLE_OUTLINE, 
                    icon_color="red", 
                    tooltip="내보내기",
                    on_click=lambda e, uid=uid, name=m["full_name"]: confirm_kick(uid, name),
                    visible=(not is_me) # Cannot kick self
                )
                
                items.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Row([
                                    ft.Text(m["full_name"], weight="bold", size=14),
                                    ft.Container(
                                        content=ft.Text(role_label, size=10, color="white", weight="bold"),
                                        bgcolor="#2196F3" if u_role == "owner" else "#4CAF50" if u_role == "manager" else "#9E9E9E",
                                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                        border_radius=4
                                    )
                                ], spacing=5),
                                ft.Text(f"@{m.get('username')}" if m.get("username") else f"User #{m['user_id'][-4:]}", size=10, color="grey")
                            ], expand=True, spacing=2),
                            role_selector,
                            kick_btn
                        ], alignment="spaceBetween"),
                        padding=10,
                        border=ft.border.only(bottom=ft.border.BorderSide(1, "#EEEEEE")),
                        bgcolor="white"
                    )
                )

            # [Iteration 28] Ownership Transfer Section
            transfer_section = ft.Container(
                content=ft.Column([
                    ft.Text("매장 양도 (소유권 이전)", weight="bold", size=16),
                    ft.Text("대표 권한을 다른 멤버에게 넘깁니다. 이 작업은 되돌릴 수 없습니다.", size=12, color="grey"),
                    ft.ElevatedButton(
                        "양도할 멤버 선택 및 넘기기", 
                        icon=ft.Icons.PERSON_SEARCH,
                        bgcolor="#FF5252", color="white",
                        on_click=open_transfer_dialog
                    )
                ]),
                padding=20, border=ft.border.all(1, "#FFEBEE"), border_radius=10, bgcolor="#FFEBEE",
                visible=(len(items) > 1) # Only show if there are other members
            )
            items.append(transfer_section)
            # Check if only owner is present
            if len(items) <= 1:
                member_mgmt_col.controls = [
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=40, color="grey"),
                            ft.Text("아직 매장에 합류한 멤버가 없습니다.", size=14, weight="bold", color="grey"),
                            ft.Text("초대 코드를 공유하여 동료를 초대해보세요!", size=12, color="grey")
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                        padding=30,
                        alignment=ft.alignment.center,
                        bgcolor="#F5F5F5",
                        border_radius=10
                    )
                ]
            else:
                member_mgmt_col.controls = items
            
            page.update()
        except Exception as ex:
            log_error(f"Load Members Error: {ex}")

    def update_member_role(uid, new_role):
        try:
            token = auth_service.get_access_token()
            channel_service.update_member_role(channel_id, uid, new_role, user_id, token=token)
            page.snack_bar = ft.SnackBar(ft.Text("권한이 수정되었습니다."), bgcolor="green"); page.snack_bar.open=True; page.update()
        except PermissionError as perm_err:
            page.snack_bar = ft.SnackBar(ft.Text(str(perm_err)), bgcolor="red"); page.snack_bar.open=True; page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"오류: {ex}"), bgcolor="red"); page.snack_bar.open=True; page.update()

    def confirm_kick(uid, name):
        def do_kick(e):
            try:
                token = auth_service.get_access_token()
                channel_service.remove_member(channel_id, uid, user_id, token=token)
                page.close(dlg)
                load_members()
                page.snack_bar = ft.SnackBar(ft.Text(f"{name}님을 내보냈습니다."), bgcolor="green"); page.snack_bar.open=True; page.update()
            except PermissionError as perm_err:
                page.snack_bar = ft.SnackBar(ft.Text(str(perm_err)), bgcolor="red"); page.snack_bar.open=True; page.update()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"내보내기 실패: {ex}"), bgcolor="red"); page.snack_bar.open=True; page.update()
                log_error(f"Kick Error: {ex}")

        dlg = ft.AlertDialog(
            title=ft.Text("멤버 내보내기"),
            content=ft.Text(f"정말 {name}님을 매장에서 내보내시겠습니까?"),
            actions=[
                ft.TextButton("취소", on_click=lambda _: page.close(dlg)),
                ft.ElevatedButton("내보내기", bgcolor="red", color="white", on_click=do_kick)
            ]
        )
        page.open(dlg)

    print(f"DEBUG_VIEW: Checking Role for initial load. role={role}")
    if role == "owner":
        load_members()

    # Imports moved to top

    # ... (Previous imports kept if possible, but replace strict block)

    # === LAYOUT CONSTRUCTION ===

    header = AppHeader(
        title_text="설정",
        on_back_click=lambda _: navigate_to("home")
    )
    
    # Store Settings Only
    current_store_settings = ft.Container(
        padding=AppLayout.CONTENT_PADDING,
        content=ft.Column([
            ft.Text(f"'{current_ch['name']}' 관리", style=ft.TextStyle(size=18, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY)),
            ft.Container(height=10),
            
            ft.Text("매장 이름 수정", style=AppTextStyles.BODY_SMALL),
            ft.Row([
                ft.Container(store_name_tf, expand=True),
                ft.ElevatedButton("저장", on_click=save_store_changes, visible=(role=="owner"), bgcolor="#00C73C", color="white"),
            ]),
            
            ft.Container(height=20),
            
            # Invite Code
            ft.Text("직원 초대 코드", style=AppTextStyles.BODY_SMALL),
            ft.Container(
                padding=15, bgcolor=AppColors.SURFACE_VARIANT, border_radius=8,
                content=ft.Column([
                    ft.Row([ft.Icon(ft.Icons.QR_CODE, color=AppColors.SECONDARY), code_display]),
                    code_expiry,
                    ft.Row([generate_btn, ft.IconButton(ft.Icons.COPY, icon_color=AppColors.SECONDARY, on_click=copy_code)])
                ])
            ),
            
            ft.Container(height=20),
            ft.Text("매장 멤버 관리", style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY), visible=(role=="owner")),
            member_mgmt_col if role == "owner" else ft.Container()
        ])
    )

    return [
        ft.SafeArea(expand=True,
            content=ft.Container(
                expand=True,
                bgcolor=AppColors.SURFACE,
                content=ft.ListView(
                    controls=[
                        # Header
                        header,
                        
                        ft.Container(
                            content=current_store_settings, 
                        ),
                        
                        msg
                    ], expand=True, spacing=0)
            )
        )
    ]
