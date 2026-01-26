import flet as ft
from services.auth_service import auth_service

def get_login_controls(page: ft.Page, navigate_to):
    # [REAL AUTH] Replaced "1234" with Supabase Auth
    
    # [FIX] Auto-redirect if already logged in (prevents flash on app start)
    if page.session.get("user_id"):
        navigate_to("home")
        return []  # Return empty controls since we're redirecting
    
    email_tf = ft.TextField(
        label="이메일", 
        width=280, 
        text_align=ft.TextAlign.LEFT,
        border_color="white", 
        cursor_color="white", 
        color="white",
        keyboard_type=ft.KeyboardType.EMAIL
    )
    
    pw_tf = ft.TextField(
        label="비밀번호", 
        password=True, 
        width=280, 
        text_align=ft.TextAlign.LEFT,
        on_submit=lambda e: perform_login(),
        border_color="white",
        cursor_color="white",
        color="white"
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
            page.splash = None
            if user:
                # [STATE] Set Global User Context
                page.session.set("user_id", user.id)
                page.session.set("user_email", user.email)
                navigate_to("home")
            else:
                error_text.value = "로그인 실패: 이메일/비밀번호를 확인하세요."
                page.update()
        except Exception as e:
            page.splash = None
            # Extract clean error message
            msg = str(e)
            if "Invalid login credentials" in msg:
                error_text.value = "로그인 정보가 올바르지 않습니다."
            else:
                error_text.value = f"로그인 오류: {msg}"
            page.update()

    # Layout
    login_card = ft.Container(
        content=ft.Column([
            ft.Text("THE MANAGER", size=32, weight="bold", color="white", style=ft.TextStyle(letter_spacing=2)),
            ft.Text("Restaurant Management OS", size=14, color="white70"),
            ft.Container(height=30),
            email_tf,
            pw_tf,
            ft.Container(height=10),
            error_text,
            ft.Container(height=20),
            ft.ElevatedButton(
                "로그인", 
                on_click=lambda _: perform_login(), 
                width=280, height=45,
                style=ft.ButtonStyle(
                    color="black",
                    bgcolor="white",
                    shape=ft.RoundedRectangleBorder(radius=8)
                )
            ),
            ft.TextButton("계정이 없으신가요? 회원가입", on_click=lambda _: navigate_to("signup"))
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=40,
        border_radius=30,
        bgcolor=ft.Colors.with_opacity(0.2, "white"),
        border=ft.border.all(1, ft.Colors.with_opacity(0.2, "white")),
    )
    
    return [
        ft.Stack([
            ft.Container(expand=True, bgcolor="#0A1929"),
            ft.Image(src="images/login_bg.png", fit=ft.ImageFit.COVER, opacity=0.7, expand=True),
            ft.Container(content=login_card, alignment=ft.alignment.center, expand=True, bgcolor=ft.Colors.with_opacity(0.3, "black"))
        ], expand=True)
    ]
