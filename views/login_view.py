import flet as ft
import asyncio
from services.auth_service import auth_service
from services.channel_service import channel_service
import json
from utils.logger import log_debug, log_info, log_error
from views.styles import AppColors, AppTextStyles, AppLayout, AppGradients, AppShadows
from components.premium_card import PremiumCard
from views.components.inputs import StandardTextField
from views.components.inputs import StandardTextField
from views.components.cards import AuthCard
from views.components.modal_overlay import ModalOverlay

# Safe shared_preferences wrapper for web mode compatibility (Flet 0.80+)
async def safe_storage_get(page: ft.Page, key: str, default=None):
    """Safely get value from shared_preferences (async), returns default if unavailable."""
    try:
        # 웹 환경: shared_preferences 사용 (Flet 0.80+)
        if hasattr(page, 'shared_preferences') and page.shared_preferences:
            return await page.shared_preferences.get(key)  # Flet 0.80+ uses get(), not get_async()
        # 데스크톱/모바일: flet.storage 사용(가능 시) 또는 기본값
        import flet as ft
        if hasattr(ft, 'storage') and ft.storage is not None:
            return ft.storage.get(key, default)
    except Exception as e:
        log_debug(f"safe_storage_get failed for '{key}': {e}")
    return default

async def safe_storage_set(page: ft.Page, key: str, value):
    """Safely set value in shared_preferences (async), silently fails if unavailable."""
    try:
        # 웹 환경: shared_preferences 사용 (Flet 0.80+)
        if hasattr(page, 'shared_preferences') and page.shared_preferences:
            await page.shared_preferences.set(key, value)  # Flet 0.80+ uses set(), not set_async()
            return True
        # 데스크톱/모바일: flet.storage 사용(가능 시)
        import flet as ft
        if hasattr(ft, 'storage') and ft.storage is not None:
            ft.storage.set(key, value)
            return True
    except Exception as e:
        log_debug(f"safe_storage_set failed for '{key}': {e}")
    return False

async def safe_storage_remove(page: ft.Page, key: str):
    """Safely remove value from shared_preferences (async), silently fails if unavailable."""
    try:
        # 웹 환경: shared_preferences 사용 (Flet 0.80+)
        if hasattr(page, 'shared_preferences') and page.shared_preferences:
            await page.shared_preferences.remove(key)  # Flet 0.80+ uses remove(), not remove_async()
            return True
        # 데스크톱/모바일: flet.storage 사용(가능 시)
        import flet as ft
        if hasattr(ft, 'storage') and ft.storage is not None:
            ft.storage.remove(key)
            return True
    except Exception as e:
        log_debug(f"safe_storage_remove failed for '{key}': {e}")
    return False

def safe_session_clear(page: ft.Page):
    """Safely clear session data using page.app_session dict."""
    try:
        if hasattr(page, 'app_session'):
            page.app_session.clear()
    except Exception as e:
        log_debug(f"session clear failed: {e}")

async def handle_successful_login(page: ft.Page, user_data: dict, navigate_to, access_token: str = None, overlay=None):
    print(f"DEBUG: handle_successful_login called, route={page.route}")
    # [GUARD] If the page has already moved away from login, abort this flow.
    # This prevents auto-login dialogs from popping up on the home screen if user manually navigated.
    if page.route not in ["login", "/", "", None]:
        log_info(f"Aborting login handler: User already at {page.route}")
        return

    log_info(f"User logged in: {user_data.get('email')}")
    try:
        token = access_token or (auth_service.get_session().access_token if auth_service.get_session() else None)
        
        if token:
            sess_data = {"access_token": token, "refresh_token": "", "user": user_data}
            current_sess = auth_service.get_session()
            if current_sess and hasattr(current_sess, "refresh_token"):
                 sess_data["refresh_token"] = current_sess.refresh_token
            await safe_storage_set(page, "supa_session", json.dumps(sess_data))

        channels = []
        try:
            channels = await asyncio.to_thread(lambda: channel_service.get_user_channels(user_data['id'], token))
        except Exception as ch_err:
            log_error(f"Error fetching channels for login: {ch_err}")
        
        if hasattr(page, "splash"):
            page.splash = None
        page.update()
        
        if len(channels) == 1:
            target_ch = channels[0]
            try:
                page.app_session["user_id"] = user_data['id']
                page.app_session["channel_id"] = target_ch["id"]
                page.app_session["channel_name"] = target_ch["name"]
                page.app_session["user_role"] = target_ch["role"]
                await navigate_to("home")
            except Exception as nav_err:
                log_error(f"Error during navigation: {nav_err}")
                import traceback
                traceback.print_exc()
            
        elif len(channels) > 1:
            if not overlay:
                 log_error("CRITICAL: Overlay not passed to handle_successful_login during multi-channel selection")
                 # Fallback code or simply fail safely
                 page.app_session["user_id"] = user_data['id']
                 await navigate_to("onboarding")
                 return

            # Flet 0.80+: Create factory for async handlers with captured variables
            
            async def pick_channel(ch):
                await overlay.close()
                page.app_session["user_id"] = user_data['id']
                page.app_session["channel_id"] = ch["id"]
                page.app_session["channel_name"] = ch["name"]
                page.app_session["user_role"] = ch["role"]
                await navigate_to("home")

            def make_pick_handler(ch):
                async def handler(e):
                    await pick_channel(ch)
                return handler

            async def go_to_onboarding(e):
                await overlay.close()
                await navigate_to("onboarding")

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
                        on_click=make_pick_handler(ch),
                    )
                )

            ch_list.controls.append(ft.Divider(height=20))
            ch_list.controls.append(
                ft.TextButton(
                    "새 매장 추가하기",
                    icon=ft.Icons.ADD_BUSINESS_ROUNDED,
                    on_click=go_to_onboarding
                )
            )

            # [FAUX DIALOG] Channel Picker
            ch_dialog_card = ft.Container(
                 width=400, height=400,
                 padding=20,
                 bgcolor="white",
                 border_radius=15,
                 on_click=lambda e: e.control.page.update(),
                 content=ft.Column([
                     ft.Text("접속할 매장을 선택하세요", size=18, weight="bold", color=AppColors.TEXT_MAIN),
                     ft.Container(height=10),
                     ft.Container(content=ch_list, expand=True)
                 ], tight=True)
            )
            
            await overlay.open_async(ch_dialog_card) if hasattr(overlay, "open_async") else overlay.open(ch_dialog_card)
            
        else:
            # No channels or error: go to onboarding
            page.app_session["user_id"] = user_data['id']
            await navigate_to("onboarding")

    except Exception as e:
        log_error(f"Login Logic Fatal Error: {e}")
        page.splash = None
        # In case of absolute failure, clear session and go to login
        safe_session_clear(page)
        await navigate_to("login")


async def get_login_controls(page: ft.Page, navigate_to):
    # [FAUX DIALOG]
    overlay = ModalOverlay(page)

    # Start auto-login check after a small delay
    async def check_auto_login_task():
        await asyncio.sleep(0.1)
        await check_auto_login()

    async def check_auto_login():
        # [GUARD] Ensure we are still on login page when this runs
        if page.route not in ["login", "/", ""]:
            return
            
        stored_session_json = await safe_storage_get(page, "supa_session")
        if stored_session_json:
            try:
                # SharedPreferences may return string or dict depending on storage
                if isinstance(stored_session_json, str):
                    sess_data = json.loads(stored_session_json)
                elif isinstance(stored_session_json, dict):
                    sess_data = stored_session_json
                else:
                    log_error(f"Auto-login failed: Unexpected session type {type(stored_session_json)}")
                    await safe_storage_remove(page, "supa_session")
                    return
                    
                user = auth_service.recover_session(sess_data.get("access_token"), sess_data.get("refresh_token") or "dummy")
                if user:
                    await handle_successful_login(page, sess_data["user"], navigate_to, sess_data.get("access_token"), overlay=overlay)
            except Exception as e:
                log_error(f"Auto-login failed: {e}")
                await safe_storage_remove(page, "supa_session")

    # [Standardized] UI Components 선언을 위로 올림
    email_tf = StandardTextField(
        label="이메일",
        width=320,
        value=await safe_storage_get(page, "saved_email", "") or ""
    )

    pw_tf = StandardTextField(
        label="비밀번호",
        password=True,
        can_reveal_password=True,
        width=320
    )

    # [TEST HOOK] Handle direct login via query parameters for automation
    async def check_test_hook():
        test_user = None
        test_pw = None
        
        try:
            test_user = page.query.get("test_user")
        except (KeyError, AttributeError):
            pass
        
        try:
            test_pw = page.query.get("test_pw")
        except (KeyError, AttributeError):
            pass
            
        if test_user and test_pw:
            log_info(f"Test Hook: Attempting auto-login for {test_user}")
            email_tf.value = test_user
            pw_tf.value = test_pw
            await perform_login()

    # [DEV AUTO-LOGIN] Automatically login with test account on localhost
    async def check_dev_auto_login():
        import os
        await asyncio.sleep(0.5)  # Wait longer to let check_auto_login run first
        
        # [GUARD] Skip if we're no longer on login page (already logged in)
        if page.route not in ["login", "/", ""]:
            return
        
        # [GUARD] Skip if session already exists (check_auto_login succeeded)
        stored_session = await safe_storage_get(page, "supa_session")
        if stored_session:
            log_info("DEV MODE: Session exists, skipping dev auto-login")
            return
        
        # Check if we're on localhost
        is_localhost = any(host in page.url for host in ["localhost", "127.0.0.1"])
        
        # Check if dev auto-login is enabled (default: true)
        dev_auto_enabled = os.environ.get("DEV_AUTO_LOGIN", "true").lower() == "true"
        
        if is_localhost and dev_auto_enabled:
            log_info("DEV MODE: Auto-login activated for localhost environment")
            email_tf.value = "adjay@naver.com"
            pw_tf.value = "wogns0519"
            await perform_login()

    # Re-enabled tasks
    asyncio.create_task(check_auto_login_task())
    asyncio.create_task(check_test_hook())
    asyncio.create_task(check_dev_auto_login())

    # print("DEBUG: get_login_controls called")
    saved_email_val = bool(await safe_storage_get(page, "saved_email"))

    save_email_check = ft.Checkbox(
        label="이메일 저장",
        value=saved_email_val,
        label_style=ft.TextStyle(size=14, color=AppColors.TEXT_SECONDARY)
    )

    error_text = ft.Text("", color=AppColors.ERROR, size=12)
    
    async def perform_login(e=None):
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
                await safe_storage_set(page, "saved_email", email_tf.value)
            else:
                await safe_storage_remove(page, "saved_email")

            user_data = {"id": res.user.id, "email": res.user.email}
            await handle_successful_login(page, user_data, navigate_to, res.session.access_token if res.session else None, overlay=overlay)

        except Exception as ex:
            log_error(f"Login failed: {ex}")
            print(f"DEBUG LOGIN ERROR: {ex}")
            page.splash = None
            error_text.value = f"로그인 오류: {ex}"
            page.update()

    # Set on_submit after perform_login is defined
    pw_tf.on_submit = perform_login

    # Debounce lock to prevent multiple concurrent login attempts
    _login_in_progress = {"lock": False}

    async def on_login_click(e):
        if _login_in_progress["lock"]:
            return  # Already processing
        _login_in_progress["lock"] = True
        try:
            await perform_login(e)
        finally:
            _login_in_progress["lock"] = False

    async def on_signup_click(e):
        await navigate_to("signup")

    login_column = ft.Column([
            ft.Image(src="images/logo.png", width=220, fit="contain"),
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
                on_click=lambda e: asyncio.create_task(on_login_click(e)),
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=AppLayout.BORDER_RADIUS_MD)),
            ),
            ft.TextButton(
                "계정이 없으신가요? 회원가입",
                on_click=lambda e: asyncio.create_task(on_signup_click(e)),
                style=ft.ButtonStyle(color=AppColors.TEXT_MUTE)
            )
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
    # Use AuthCard
    login_card = AuthCard(content=login_column)
    
    return [
        ft.Container(
            expand=True,
            gradient=AppGradients.PRIMARY_LINEAR,
            content=ft.Stack([
                ft.Container(content=login_card, alignment=ft.Alignment(0, 0)),
                overlay
            ])
        )
    ]
