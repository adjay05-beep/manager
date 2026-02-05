import flet as ft
import re # [ADDED] For email validation
from services.auth_service import auth_service
import asyncio
from views.styles import AppColors, AppLayout
from views.components.inputs import StandardTextField, StandardDropdown
from views.components.cards import AuthCard
from views.components.modal_overlay import ModalOverlay

async def get_signup_controls(page: ft.Page, navigate_to):
    
    # --- State ---
    state = {
        "step": "form", # form | verify
        "email": "",
        "loading": False
    }

    # [FAUX DIALOG]
    overlay = ModalOverlay(page)

    # --- Header ---
    header = ft.Text("회원가입", size=30, weight="bold", color=AppColors.TEXT_MAIN)
    sub_header = ft.Text("The Manager에 오신 것을 환영합니다.", color=AppColors.TEXT_MUTE)

    # --- Form Controls ---
    email_tf = StandardTextField(label="이메일", width=300)
    name_tf = StandardTextField(label="이름 (실명 추천)", width=300)
    pw_tf = StandardTextField(label="비밀번호 (8자 이상)", password=True, width=300)
    pw_cf_tf = StandardTextField(label="비밀번호 확인", password=True, width=300)
    
    # [UPDATED] Role Selection (Dropdown, No Default)
    role_dd = StandardDropdown(
        label="가입 유형 (필수)",
        width=300,
        options=[
            ft.dropdown.Option("owner", "사장님 (Owner)"),
            ft.dropdown.Option("staff", "직원 (Staff)"),
        ]
    )
    
    error_txt = ft.Text("", color=AppColors.ERROR, size=12)

    # --- Verification Controls ---
    otp_tf = StandardTextField(
        label="인증코드 6자리", 
        width=300, 
        text_align="center", 
        text_style=ft.TextStyle(letter_spacing=5)
    )
    
    verify_status = ft.Text("이메일로 전송된 코드를 입력하세요.", color=AppColors.TEXT_MUTE, size=12)

    async def update_view():
        card_content.controls = []
        if state["step"] == "form":
            submit_btn = ft.ElevatedButton(
                "가입하기", 
                on_click=lambda e: asyncio.create_task(do_signup(e)), 
                width=300, height=45, 
                bgcolor=AppColors.PRIMARY, color=ft.Colors.WHITE, 
                disabled=state["loading"],
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=AppLayout.BORDER_RADIUS_MD))
            )
            
            controls_list = [
                header, sub_header, ft.Container(height=20),
                email_tf, name_tf, pw_tf, pw_cf_tf,
                role_dd,
                ft.Container(height=10), error_txt,
                submit_btn,
                ft.TextButton("인증 코드가 이미 있으신가요?", on_click=lambda _: asyncio.create_task(set_step_verify())),
                ft.TextButton("이미 계정이 있으신가요? 로그인", on_click=lambda _: asyncio.create_task(navigate_to("login")))
            ]
            
            if state["loading"]:
                controls_list.insert(9, ft.ProgressBar(width=300, color=AppColors.PRIMARY))
                
            card_content.controls = controls_list
        else:
            verify_btn = ft.ElevatedButton(
                "인증하기", 
                on_click=lambda e: asyncio.create_task(do_verify(e)), 
                width=300, height=45, 
                bgcolor=AppColors.SUCCESS, color=ft.Colors.WHITE, 
                disabled=state["loading"],
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=AppLayout.BORDER_RADIUS_MD))
            )
            
            controls_list = [
                ft.Text("이메일 인증", size=24, weight="bold", color=AppColors.TEXT_MAIN),
                ft.Text(f"{state['email']}로 코드를 보냈습니다.", color=AppColors.TEXT_MUTE),
                ft.Container(height=20),
                otp_tf, verify_status,
                ft.Container(height=20),
                verify_btn,
                ft.Container(height=10),
                # Ensure the entire button row is centered and doesn't spill out
                ft.Container(
                    content=ft.Row([
                        ft.TextButton("수정하기", on_click=lambda _: asyncio.create_task(set_step_form()), style=ft.ButtonStyle(color=AppColors.TEXT_MUTE)),
                        ft.TextButton("코드 재전송", on_click=lambda e: asyncio.create_task(do_resend(e)), style=ft.ButtonStyle(color=AppColors.TEXT_MUTE))
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                    width=300
                )
            ]
            
            if state["loading"]:
                controls_list.insert(5, ft.ProgressBar(width=300, color=AppColors.PRIMARY))
            
            card_content.controls = controls_list
            
        try:
            page.update()
        except Exception:
            pass

    async def handle_signup_work():
        try:
            role = role_dd.value
            email = state["email"]
            pw = pw_tf.value
            name = name_tf.value
            
            # Wrap Sync Call in to_thread
            res = await asyncio.to_thread(lambda: auth_service.sign_up(email, pw, name, role))
            
            if res.user and res.user.identities and len(res.user.identities) > 0:
                state["step"] = "verify"
            elif res.user and not res.user.identities:
                # This often happens when user already exists in Supabase
                raise Exception("이미 가입된 계정입니다.")
            else:
                 if res.session:
                     # [ADDED] Email Confirmation is OFF flow
                     from views.login_view import safe_storage_set, handle_successful_login
                     user_data = {"id": res.user.id, "email": res.user.email}
                     await handle_successful_login(page, user_data, navigate_to, res.session.access_token, overlay=overlay)
                     return
                 else:
                     state["step"] = "verify"
        except Exception as ex:
             msg = str(ex).lower()
             # Recovery logic for existing but unconfirmed users
             if "already registered" in msg or "이미 가입된" in msg:
                 try:
                     # Attempt to resend OTP to see if it's unconfirmed
                     await asyncio.to_thread(lambda: auth_service.resend_otp(state["email"]))
                     state["step"] = "verify"
                     verify_status.value = "이미 가입 진행 중인 계정입니다. 인증 코드를 다시 보냈습니다."
                     verify_status.color = AppColors.WARNING
                     error_txt.value = ""
                 except Exception:
                     # If resend fails, the user is likely already confirmed
                     error_txt.value = "이미 가입 완료된 계정입니다. 로그인해주세요."
             else:
                 error_txt.value = f"가입 오류: {ex}"
        finally:
            state["loading"] = False
            await update_view()

    async def do_signup(e):
        state["email"] = email_tf.value
        if not state["email"] or not pw_tf.value:
            error_txt.value = "모든 필드를 입력해주세요."; await update_view(); return
        
        # [ADDED] Email Regex Validation
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, state["email"]):
             error_txt.value = "유효하지 않은 이메일 형식입니다."; await update_view(); return

        if pw_tf.value != pw_cf_tf.value:
            error_txt.value = "비밀번호가 일치하지 않습니다."; await update_view(); return
        if len(pw_tf.value) < 8:
            error_txt.value = "비밀번호는 8자 이상이어야 합니다."; await update_view(); return
        if not role_dd.value:
            error_txt.value = "가입 유형(사장님/직원)을 선택해주세요."; await update_view(); return

        state["loading"] = True
        await update_view() # Show spinner
        asyncio.create_task(handle_signup_work())

    async def handle_verify_work(code):
        try:
            res = await asyncio.to_thread(lambda: auth_service.verify_otp(state["email"], code))
            if res:
                # [FAUX DIALOG] Success Message
                success_card = ft.Container(
                    width=300,
                    padding=20,
                    bgcolor="white",
                    border_radius=15,
                     on_click=lambda e: e.control.page.update(),
                    content=ft.Column([
                        ft.Text("회원가입 완료! 🎉", size=20, weight="bold", color=AppColors.TEXT_MAIN),
                        ft.Container(height=10),
                        ft.Text("회원가입이 성공적으로 완료되었습니다.\n로그인 후 이용해주세요.", size=14, color=AppColors.TEXT_SECONDARY),
                        ft.Container(height=20),
                        ft.Row([
                            ft.ElevatedButton("확인 (로그인하러 가기)", on_click=lambda e: asyncio.create_task(navigate_to("login")), bgcolor=AppColors.SUCCESS, color=ft.Colors.WHITE)
                        ], alignment=ft.MainAxisAlignment.END)
                    ], tight=True)
                )
                overlay.open(success_card)
                page.update()
            else:
                verify_status.value = "인증 실패: 코드를 확인하세요."
                verify_status.color = AppColors.ERROR
                await update_view()
        except Exception as ex:
             verify_status.value = f"오류: {ex}"
             verify_status.color = AppColors.ERROR
             await update_view()
        finally:
            state["loading"] = False
            try:
                page.update()
            except Exception:
                pass

    async def do_verify(e):
        code = otp_tf.value
        if not code: return
        state["loading"] = True
        await update_view()
        asyncio.create_task(handle_verify_work(code))
            
    async def handle_resend_work():
        try:
            await asyncio.to_thread(lambda: auth_service.resend_otp(state["email"]))
            verify_status.value = "코드를 재전송했습니다."
            verify_status.color = AppColors.SUCCESS
            page.update()
        except Exception as e:
            verify_status.value = f"재전송 실패: {e}"
            verify_status.color = AppColors.ERROR
            page.update()

    async def do_resend(e):
        asyncio.create_task(handle_resend_work())

    async def set_step_verify():
        state.update({"step": "verify"})
        await update_view()

    async def set_step_form():
        state.update({"step": "form"})
        error_txt.value = "" # Clear errors
        await update_view()

    card_content = ft.Column(
        alignment=ft.MainAxisAlignment.CENTER, 
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10,
        scroll=ft.ScrollMode.AUTO
    )
    
    # Initialize
    await update_view()

    # Use AuthCard
    auth_card = AuthCard(content=card_content)

    return [
        ft.Stack([
            ft.Container(expand=True, bgcolor=AppColors.BG_LIGHT),
            ft.Container(
                content=auth_card,
                alignment=ft.Alignment(0, 0),
                expand=True
            ),
            overlay # Modal Overlay Layer
        ], expand=True)
    ]
