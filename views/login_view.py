import flet as ft
from services.auth_service import auth_service
from services.channel_service import channel_service
import json
from utils.logger import log_debug, log_info, log_error
from views.styles import AppColors, AppTextStyles, AppLayout, AppGradients, AppShadows
from components.premium_card import PremiumCard

def handle_successful_login(page: ft.Page, user_data: dict, navigate_to, access_token: str = None):
    log_info(f"User logged in: {user_data.get('email')}")
    try:
        token = access_token or (auth_service.get_session().access_token if auth_service.get_session() else None)
        
        if token:
            sess_data = {"access_token": token, "refresh_token": "", "user": user_data}
            current_sess = auth_service.get_session()
            if current_sess and hasattr(current_sess, "refresh_token"):
                 sess_data["refresh_token"] = current_sess.refresh_token
            page.client_storage.set("supa_session", json.dumps(sess_data))

        channels = []
        try:
            channels = channel_service.get_user_channels(user_data['id'], token)
        except Exception as ch_err:
            log_error(f"Error fetching channels for login: {ch_err}")
        
        if hasattr(page, "splash"):
            page.splash = None
        page.update()
        
        if len(channels) == 1:
            target_ch = channels[0]
            page.session.set("user_id", user_data['id'])
            page.session.set("channel_id", target_ch["id"])
            page.session.set("channel_name", target_ch["name"])
            page.session.set("user_role", target_ch["role"])
            navigate_to("home")
            
        elif len(channels) > 1:
            # ... (Rest of multi-channel logic) ...
            def pick_channel(ch):
                page.close(ch_dialog)
                page.session.set("user_id", user_data['id'])
                page.session.set("channel_id", ch["id"])
                page.session.set("channel_name", ch["name"])
                page.session.set("user_role", ch["role"])
                navigate_to("home")

            ch_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
            for ch in channels:
                ch_list.controls.append(
                    PremiumCard(
                        content=ft.Row([
                            ft.Icon(ft.Icons.STORE_ROUNDED, color=AppColors.PRIMARY),
                            ft.Column([
                                ft.Text(ch["name"], weight="bold", size=16),
                                ft.Text(f"{ch['role']} • {ch.get('channel_code','-')}", size=12, color=AppColors.TEXT_MUTE)
                            ], spacing=2)
                        ]),
                        on_click=lambda e, c=ch: pick_channel(c),
                    )
                )
            
            ch_list.controls.append(ft.Divider(height=20))
            ch_list.controls.append(
                ft.TextButton(
                    "새 매장 추가하기",
                    icon=ft.Icons.ADD_BUSINESS_ROUNDED,
                    on_click=lambda _: (page.close(ch_dialog), navigate_to("onboarding"))
                )
            )

            ch_dialog = ft.AlertDialog(
                title=ft.Text("접속할 매장을 선택하세요", size=18, weight="bold"),
                content=ft.Container(content=ch_list, width=400, height=300),
            )
            page.open(ch_dialog)
            
        else:
            # No channels or error: go to onboarding
            page.session.set("user_id", user_data['id'])
            navigate_to("onboarding")

    except Exception as e:
        log_error(f"Login Logic Fatal Error: {e}")
        page.splash = None
        # In case of absolute failure, clear session and go to login
        page.session.clear()
        navigate_to("login")


def get_login_controls(page: ft.Page, navigate_to):
    # Auto-Login Logic (Deferred to prevent race condition)
    def check_auto_login():
        stored_session_json = page.client_storage.get("supa_session")
        if stored_session_json:
            try:
                sess_data = json.loads(stored_session_json)
                user = auth_service.recover_session(sess_data.get("access_token"), sess_data.get("refresh_token") or "dummy")
                if user:
                    handle_successful_login(page, sess_data["user"], navigate_to, sess_data.get("access_token"))
            except Exception as e:
                log_error(f"Auto-login failed: {e}")
                page.client_storage.remove("supa_session")

    # Start auto-login check after a small delay
    import threading
    threading.Timer(0.1, check_auto_login).start()

    email_tf = ft.TextField(
        label="이메일",
        width=320,
        text_size=14,
        border_radius=AppLayout.BORDER_RADIUS_MD,
        bgcolor=ft.Colors.WHITE,
        value=page.client_storage.get("saved_email") or ""
    )

    pw_tf = ft.TextField(
        label="비밀번호",
        password=True,
        can_reveal_password=True,
        width=320,
        text_size=14,
        border_radius=AppLayout.BORDER_RADIUS_MD,
        bgcolor=ft.Colors.WHITE,
        on_submit=lambda _: perform_login()
    )

    print("DEBUG: get_login_controls called")
    saved_email_val = False
    try:
        saved_email_val = bool(page.client_storage.get("saved_email"))
    except Exception as e:
        print(f"DEBUG: client_storage error: {e}")

    save_email_check = ft.Checkbox(
        label="이메일 저장",
        value=saved_email_val,
        label_style=ft.TextStyle(size=14, color=AppColors.TEXT_SECONDARY)
    )

    error_text = ft.Text("", color=AppColors.ERROR, size=12)
    
    def perform_login():
        if not email_tf.value or not pw_tf.value:
            error_text.value = "이메일과 비밀번호를 입력해주세요."
            page.update()
            return

        if hasattr(page, "splash"):
            page.splash = ft.ProgressBar(color=AppColors.PRIMARY)
        page.update()
        
        try:
            res = auth_service.sign_in(email_tf.value, pw_tf.value)
            
            if save_email_check.value:
                page.client_storage.set("saved_email", email_tf.value)
            else:
                page.client_storage.remove("saved_email")
            
            user_data = {"id": res.user.id, "email": res.user.email}
            handle_successful_login(page, user_data, navigate_to, res.session.access_token if res.session else None)

        except Exception as e:
            page.splash = None
            error_text.value = "로그인 정보가 올바르지 않거나 오류가 발생했습니다."
            page.update()

    login_card = ft.Container(
        content=ft.Column([
            ft.Image(src="images/logo.png", width=220, fit=ft.ImageFit.CONTAIN),
            ft.Container(height=AppLayout.MD),
            email_tf,
            pw_tf,
            ft.Container(
                content=ft.Row([save_email_check], alignment=ft.MainAxisAlignment.START),
                width=320
            ),
            error_text,
            ft.Container(height=AppLayout.SM),
            ft.ElevatedButton(
                "로그인",
                width=320, height=50,
                bgcolor=AppColors.PRIMARY, color=ft.Colors.WHITE,
                on_click=lambda _: perform_login(),
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=AppLayout.BORDER_RADIUS_MD)),
            ),
            ft.TextButton(
                "계정이 없으신가요? 회원가입",
                on_click=lambda _: navigate_to("signup"),
                style=ft.ButtonStyle(color=AppColors.TEXT_MUTE)
            )
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=AppLayout.XL,
        bgcolor=ft.Colors.WHITE,
        border_radius=AppLayout.BORDER_RADIUS_LG,
        shadow=AppShadows.MEDIUM,
    )
    
    return [
        ft.Container(
            expand=True,
            gradient=AppGradients.PRIMARY_LINEAR,
            content=ft.Stack([
                ft.Container(content=login_card, alignment=ft.alignment.center)
            ])
        )
    ]
