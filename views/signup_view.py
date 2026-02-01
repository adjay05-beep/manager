import flet as ft
from services.auth_service import auth_service
import asyncio

async def get_signup_controls(page: ft.Page, navigate_to):
    
    # --- State ---
    state = {
        "step": "form", # form | verify
        "email": "",
        "loading": False
    }

    # --- Header ---
    header = ft.Text("회원가입", size=30, weight="bold", color="#0A1929")
    sub_header = ft.Text("The Manager에 오신 것을 환영합니다.", color="grey")

    # --- Form Controls ---
    email_tf = ft.TextField(label="이메일", width=300, color="black", border_color="grey")
    name_tf = ft.TextField(label="이름 (실명 추천)", width=300, color="black", border_color="grey")
    pw_tf = ft.TextField(label="비밀번호 (6자 이상)", password=True, width=300, color="black", border_color="grey")
    pw_cf_tf = ft.TextField(label="비밀번호 확인", password=True, width=300, color="black", border_color="grey")
    
    # [UPDATED] Role Selection (Dropdown, No Default)
    role_dd = ft.Dropdown(
        label="가입 유형 (필수)",
        width=300,
        options=[
            ft.dropdown.Option("owner", "사장님 (Owner)"),
            ft.dropdown.Option("staff", "직원 (Staff)"),
        ],
        bgcolor="white",
        color="black",
        border_color="grey",
    )
    
    error_txt = ft.Text("", color="red", size=12)

    # --- Verification Controls ---
    otp_tf = ft.TextField(label="인증코드 6자리", width=300, text_align="center", color="black", border_color="#00C73C", text_style=ft.TextStyle(letter_spacing=5))
    verify_status = ft.Text("이메일로 전송된 코드를 입력하세요.", color="white70", size=12)

    async def update_view():
        card_content.controls = []
        if state["step"] == "form":
            submit_btn = ft.ElevatedButton("가입하기", on_click=lambda e: asyncio.create_task(do_signup(e)), width=300, height=45, bgcolor="white", color="black", disabled=state["loading"])
            
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
                controls_list.insert(9, ft.ProgressBar(width=300, color="#00C73C"))
                
            card_content.controls = controls_list
        else:
            verify_btn = ft.ElevatedButton("인증하기", on_click=lambda e: asyncio.create_task(do_verify(e)), width=300, height=45, bgcolor="#00C73C", color="white", disabled=state["loading"])
            
            controls_list = [
                ft.Text("이메일 인증", size=24, weight="bold", color="#0A1929"),
                ft.Text(f"{state['email']}로 코드를 보냈습니다.", color="grey"),
                ft.Container(height=20),
                otp_tf, verify_status,
                ft.Container(height=20),
                verify_btn,
                ft.TextButton("코드 재전송", on_click=lambda e: asyncio.create_task(do_resend(e)))
            ]
            
            if state["loading"]:
                controls_list.insert(5, ft.ProgressBar(width=300, color="#00C73C"))

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
                error_txt.value = "이미 가입된 계정일 수 있습니다."
            else:
                 if not res.session:
                     state["step"] = "verify"
        except Exception as ex:
             msg = str(ex)
             if "이미 가입된" in msg:
                 try:
                     user = await asyncio.to_thread(lambda: auth_service.sign_in(state["email"], pw_tf.value))
                     if user:
                         pass
                 except Exception as login_ex:
                     l_msg = str(login_ex)
                     if "Email not confirmed" in l_msg or "confirmed" in l_msg:
                         try:
                            await asyncio.to_thread(lambda: auth_service.resend_otp(state["email"]))
                         except Exception:
                            pass
                         state["step"] = "verify"
                         verify_status.value = "⚠️ 가입이 중단되었던 계정입니다. 인증 코드를 재전송했습니다."
                         verify_status.color = "yellow"
                         error_txt.value = ""
                     else:
                         error_txt.value = "이미 가입된 이메일입니다."
             else:
                 error_txt.value = f"가입 오류: {ex}"
        finally:
            state["loading"] = False
            await update_view()

    async def do_signup(e):
        state["email"] = email_tf.value
        if not state["email"] or not pw_tf.value:
            error_txt.value = "모든 필드를 입력해주세요."; await update_view(); return
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
                async def close_and_go(e):
                    await page.close_async(dlg) if hasattr(page, "close_async") else page.close(dlg)
                    await navigate_to("login")

                dlg = ft.AlertDialog(
                    title=ft.Text("회원가입 완료! 🎉", size=20, weight="bold"),
                    content=ft.Text("회원가입이 성공적으로 완료되었습니다.\n로그인 후 이용해주세요.", size=16),
                    actions=[
                        ft.ElevatedButton("확인 (로그인하러 가기)", on_click=lambda e: asyncio.create_task(close_and_go(e)), bgcolor="#00C73C", color="white")
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                    on_dismiss=lambda e: asyncio.create_task(navigate_to("login")),
                    modal=True,
                    shape=ft.RoundedRectangleBorder(radius=10)
                )
                await page.open_async(dlg) if hasattr(page, "open_async") else page.open(dlg)
                page.update()
            else:
                verify_status.value = "인증 실패: 코드를 확인하세요."
                verify_status.color = "red"
                await update_view()
        except Exception as ex:
             verify_status.value = f"오류: {ex}"
             verify_status.color = "red"
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
            verify_status.color = "green"
            page.update()
        except Exception as e:
            verify_status.value = f"재전송 실패: {e}"
            verify_status.color = "red"
            page.update()

    async def do_resend(e):
        asyncio.create_task(handle_resend_work())

    async def set_step_verify():
        state.update({"step": "verify"})
        await update_view()

    card_content = ft.Column(
        alignment=ft.MainAxisAlignment.CENTER, 
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10,
        scroll=ft.ScrollMode.AUTO
    )
    
    # Initialize
    await update_view()

    return [
        ft.Stack([
            ft.Container(expand=True, bgcolor="white"),
            ft.Container(
                content=ft.Container(
                    content=card_content,
                    padding=40,
                    border_radius=16,
                    border=ft.border.all(1, "#DDDDDD"),
                    bgcolor="white",
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=10,
                        color=ft.Colors.with_opacity(0.1, "black"),
                        offset=ft.Offset(0, 4),
                    )
                ),
                alignment=ft.Alignment(0, 0),
                expand=True
            )
        ], expand=True)
    ]
