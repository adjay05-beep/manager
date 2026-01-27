import flet as ft
from services.auth_service import auth_service
from services.channel_service import channel_service
import json
from utils.logger import log_debug, log_info, log_error

def handle_successful_login(page: ft.Page, user, navigate_to):
    log_info(f"User logged in: {user.email} ({user.id})")
    """
    Common logic for processing a logged-in user:
    1. Channel Routing (Smart Login)
    2. Session Setup
    3. Navigation
    """
    try:
        # Save session for Auto-Login
        # We need the session object. 
        # auth_service.sign_in returns User, but we need Session.
        # Let's get it from auth_service
        access_token = None
        session = auth_service.get_session() 
        if session:
            access_token = session.access_token
            # Serialize
            sess_data = {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "expires_at": session.expires_at,
                "token_type": session.token_type,
                "user": {"id": user.id, "email": user.email}
            }
            page.client_storage.set("supa_session", json.dumps(sess_data))

        # Explicitly pass token to ensure RLS works on Mobile/Web
        channels = channel_service.get_user_channels(user.id, access_token)
        page.splash = None
        
        if len(channels) == 1:
            # Case A: Single Channel
            target_ch = channels[0]
            page.session.set("user_id", user.id)
            page.session.set("user_email", user.email)
            page.session.set("channel_id", target_ch["id"])
            page.session.set("channel_name", target_ch["name"])
            page.session.set("user_role", target_ch["role"])
            navigate_to("home")
            
        elif len(channels) > 1:
            # Case B: Multi Channel
            def pick_channel(ch):
                page.close(ch_dialog)
                page.session.set("user_id", user.id)
                page.session.set("user_email", user.email)
                page.session.set("channel_id", ch["id"])
                page.session.set("channel_name", ch["name"])
                page.session.set("user_role", ch["role"])
                navigate_to("home")

            # Create New Store button handler
            def create_new_store(e):
                page.close(ch_dialog)
                navigate_to("onboarding")

            ch_list = ft.Column(spacing=10)
            for ch in channels:
                ch_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.STORE, color="white"),
                            ft.Column([
                                ft.Text(ch["name"], weight="bold", size=16),
                                ft.Text(f"{ch['role']} • {ch.get('channel_code','Unknown')}", size=12, color="white70")
                            ], spacing=2)
                        ]),
                        padding=15,
                        border_radius=10,
                        bgcolor="#1A237E",
                        on_click=lambda e, c=ch: pick_channel(c),
                        ink=True
                    )
                )
            
            # Add divider and "Create New Store" button at bottom
            ch_list.controls.append(ft.Divider(color="white30", height=20))
            ch_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.ADD_BUSINESS, color="green"),
                        ft.Text("새 매장 추가하기", weight="bold", size=15, color="green")
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    padding=12,
                    border_radius=10,
                    bgcolor=ft.Colors.with_opacity(0.05, "green"),
                    border=ft.border.all(2, "green"),
                    on_click=create_new_store,
                    ink=True
                )
            )

            ch_dialog = ft.AlertDialog(
                title=ft.Text("매장 선택 (Multi-Channel)"),
                content=ft.Container(
                    content=ch_list,
                    width=350,
                    height=min(len(channels) * 90 + 100, 400),  # Dynamic height with max cap
                ),
                modal=True
            )
            page.open(ch_dialog)
            
        else:
            # Case C: No Channel
            page.session.set("user_id", user.id)
            navigate_to("onboarding")

    except Exception as login_logic_err:
            print(f"Smart Login Error: {login_logic_err}")
            page.session.set("user_id", user.id)
            navigate_to("home")


def get_login_controls(page: ft.Page, navigate_to):
    # [Auto-Login Check]
    if not page.session.get("user_id"):
        # Check Client Storage
        try:
            stored_session_json = page.client_storage.get("supa_session")
            if stored_session_json:
                data = json.loads(stored_session_json)
                # Try to recover
                # We need auth_service to support set_session
                user = auth_service.recover_session(data["access_token"], data["refresh_token"])
                if user:
                    print("Auto-Login Successful")
                    handle_successful_login(page, user, navigate_to)
                    return [] # Redirecting
        except Exception as e:
            print(f"Auto-Login Failed: {e}")
            # Clear invalid session
            page.client_storage.remove("supa_session")

    # Already logged in check
    if page.session.get("user_id"):
        navigate_to("home")
        return []

    # Try to load saved credentials
    saved_email = page.client_storage.get("saved_email") or ""
    saved_password = page.client_storage.get("saved_password") or ""
    remember_me_checked = bool(saved_email and saved_password)

    email_tf = ft.TextField(
        label="이메일", 
        width=280, 
        text_align=ft.TextAlign.LEFT,
        border_color="#CCCCCC", 
        cursor_color="#1565C0", 
        color="black",
        keyboard_type=ft.KeyboardType.EMAIL,
        value=saved_email,
        label_style=ft.TextStyle(color="grey")
    )
    
    pw_tf = ft.TextField(
        label="비밀번호", 
        password=True, 
        width=280, 
        text_align=ft.TextAlign.LEFT,
        on_submit=lambda e: perform_login(),
        border_color="#CCCCCC",
        cursor_color="#1565C0",
        color="black",
        value=saved_password,
        label_style=ft.TextStyle(color="grey")
    )
    
    remember_checkbox = ft.Checkbox(
        label="아이디/비밀번호 기억하기",
        value=remember_me_checked,
        fill_color="#1565C0",
        check_color="white",
        label_style=ft.TextStyle(color="grey")
    )
    
    error_text = ft.Text("", color="red", size=12)
    
    def perform_login():
        if not email_tf.value or not pw_tf.value:
            error_text.value = "이메일과 비밀번호를 입력해주세요."
            page.update()
            return

        page.splash = ft.ProgressBar()
        page.update()
        
        try:
            user = auth_service.sign_in(email_tf.value, pw_tf.value)
            
            # Save or clear credentials based on checkbox
            if remember_checkbox.value:
                page.client_storage.set("saved_email", email_tf.value)
                page.client_storage.set("saved_password", pw_tf.value)
            else:
                page.client_storage.remove("saved_email")
                page.client_storage.remove("saved_password")
            
            # handle_successful_login will clear splash
            handle_successful_login(page, user, navigate_to)

        except Exception as e:
            page.splash = None
            msg = str(e)
            if "Invalid login credentials" in msg:
                error_text.value = "로그인 정보가 올바르지 않습니다."
            else:
                error_text.value = f"로그인 오류: {msg}"
            page.update()

    # Layout (Light Theme)
    login_card = ft.Container(
        content=ft.Column([
            ft.Text("THE MANAGER", size=32, weight="bold", color="#0A1929", style=ft.TextStyle(letter_spacing=2)),
            ft.Text("Restaurant Management OS", size=14, color="grey"),
            ft.Container(height=30),
            email_tf,
            pw_tf,
            ft.Container(
                content=remember_checkbox,
                alignment=ft.alignment.center,
                width=280
            ),
            ft.Container(height=10),
            error_text,
            ft.Container(height=20),
            ft.ElevatedButton(
                "로그인",
                width=300,
                height=45,
                bgcolor="#1565C0",
                color="white",
                on_click=lambda _: perform_login()
            ),
            ft.TextButton("계정이 없으신가요? 회원가입", on_click=lambda _: navigate_to("signup"), style=ft.ButtonStyle(color="grey"))
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=40,
        border_radius=16,
        bgcolor="white",
        border=ft.border.all(1, "#DDDDDD"),
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=10,
            color=ft.Colors.with_opacity(0.1, "black"),
            offset=ft.Offset(0, 4),
        )
    )
    
    return [
        ft.Stack([
            ft.Container(expand=True, bgcolor="white"),
            ft.Image(src="images/login_bg.png", fit=ft.ImageFit.COVER, opacity=0.7, expand=True),
            ft.Container(content=login_card, alignment=ft.alignment.center, expand=True, bgcolor=ft.Colors.with_opacity(0.3, "black"))
        ], expand=True)
    ]
