import flet as ft
from services.auth_service import auth_service
import threading
import asyncio # Keep just in case, though mostly unused now.

def get_signup_controls(page: ft.Page, navigate_to):
    
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

    def set_loading(loading):
        state["loading"] = loading
        # Update button requires update_view call usually or direct prop update
        # For simplicity, we call update_view which respects loading state
        update_view()

    def _signup_thread():
        try:
            # Direct Sync Call
            role = role_dd.value
            res = auth_service.sign_up(state["email"], pw_tf.value, name_tf.value, role)
            
            if res.user and res.user.identities and len(res.user.identities) > 0:
                state["step"] = "verify"
            elif res.user and not res.user.identities:
                error_txt.value = "이미 가입된 계정일 수 있습니다."
            else:
                 if res.session:
                     # Need to navigate on main thread? Flet usually allows this.
                     # But safer to schedule it? No, navigate_to calls page.clean which is UI op.
                     # We can call it, but update_view handles UI logic.
                     pass
                 else:
                     state["step"] = "verify"
        except Exception as ex:
             msg = str(ex)
             if "이미 가입된" in msg:
                 # [Auto-Recovery] User likely crashed before verifying.
                 try:

                     # Attempt login with same credentials
                     user = auth_service.sign_in(state["email"], pw_tf.value)
                     if user:
                         # Miracle: They are already verified?

                         pass # Will fall through to session check navigation
                 except Exception as login_ex:
                     l_msg = str(login_ex)
                     if "Email not confirmed" in l_msg or "confirmed" in l_msg:
                         # Expected Limbo State -> Recover

                         try:
                            auth_service.resend_otp(state["email"])
                         except: pass
                         state["step"] = "verify"
                         verify_status.value = "⚠️ 가입이 중단되었던 계정입니다. 인증 코드를 재전송했습니다."
                         verify_status.color = "yellow"
                         error_txt.value = ""
                     else:
                         # Wrong password or other error
                         error_txt.value = "이미 가입된 이메일입니다."
             else:
                 error_txt.value = f"가입 오류: {ex}"
        finally:
            state["loading"] = False
            # If session exists, navigate
            try:
                # We need to check session status again cleanly
                # Logic simplified: if clean run, current display will be updated
                pass
            except: pass
            update_view()

    def do_signup(e):

        state["email"] = email_tf.value
        if not state["email"] or not pw_tf.value:
            error_txt.value = "모든 필드를 입력해주세요."; update_view(); return
        if pw_tf.value != pw_cf_tf.value:
            error_txt.value = "비밀번호가 일치하지 않습니다."; update_view(); return
        if len(pw_tf.value) < 6:
            error_txt.value = "비밀번호는 6자 이상이어야 합니다."; update_view(); return
        if not role_dd.value:
            error_txt.value = "가입 유형(사장님/직원)을 선택해주세요."; update_view(); return


        state["loading"] = True
        update_view() # Show spinner

        threading.Thread(target=_signup_thread, daemon=True).start()


    def _verify_thread(code):
        try:
            res = auth_service.verify_otp(state["email"], code)
            if res:
                verify_status.value = "인증 성공! 로그인 페이지로 이동합니다."
                verify_status.color = "green"
                update_view()
                # Wait and nav
                import time
                time.sleep(1.5)
                navigate_to("login")
            else:
                verify_status.value = "인증 실패: 코드를 확인하세요."
                verify_status.color = "red"
                update_view()
        except Exception as ex:
             verify_status.value = f"오류: {ex}"
             verify_status.color = "red"
             update_view()
        finally:
            state["loading"] = False
            update_view()

    def do_verify(e):
        code = otp_tf.value
        if not code: return
        state["loading"] = True
        update_view()
        threading.Thread(target=_verify_thread, args=(code,), daemon=True).start()
            
    def do_resend(e):
        threading.Thread(target=lambda: (auth_service.resend_otp(state["email"]), setattr(verify_status, 'value', "코드를 재전송했습니다."), page.update()), daemon=True).start()

    def update_view():
        card_content.controls = []
        if state["step"] == "form":
            submit_btn = ft.ElevatedButton("가입하기", on_click=do_signup, width=300, height=45, bgcolor="white", color="black", disabled=state["loading"])
            
            controls_list = [
                header, sub_header, ft.Container(height=20),
                email_tf, name_tf, pw_tf, pw_cf_tf,
                role_dd,
                ft.Container(height=10), error_txt,
                submit_btn,
                ft.TextButton("인증 코드가 이미 있으신가요?", on_click=lambda _: (state.update({"step": "verify"}), update_view())),
                ft.TextButton("이미 계정이 있으신가요? 로그인", on_click=lambda _: navigate_to("login"))
            ]
            
            if state["loading"]:
                controls_list.insert(9, ft.ProgressBar(width=300, color="#00C73C"))
                
            card_content.controls = controls_list
        else:
            verify_btn = ft.ElevatedButton("인증하기", on_click=do_verify, width=300, height=45, bgcolor="#00C73C", color="white", disabled=state["loading"])
            
            controls_list = [
                ft.Text("이메일 인증", size=24, weight="bold", color="white"),
                ft.Text(f"{state['email']}로 코드를 보냈습니다.", color="white70"),
                ft.Container(height=20),
                otp_tf, verify_status,
                ft.Container(height=20),
                verify_btn,
                ft.TextButton("코드 재전송", on_click=do_resend)
            ]
            
            if state["loading"]:
                controls_list.insert(5, ft.ProgressBar(width=300, color="#00C73C"))

            card_content.controls = controls_list
        try:
            page.update()
        except: pass

    card_content = ft.Column(
        alignment=ft.MainAxisAlignment.CENTER, 
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10
    )
    
    # Initialize
    update_view()

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
                alignment=ft.alignment.center,
                expand=True
            )
        ], expand=True)
    ]
