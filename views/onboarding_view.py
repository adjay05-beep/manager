import flet as ft
from services.channel_service import channel_service
from services.auth_service import auth_service
from db import has_service_key, app_logs, service_key

def get_onboarding_controls(page: ft.Page, navigate_to):
    current_user_id = page.session.get("user_id")
    
    # [Name Verification] Fetch User Name
    user_name = page.session.get("display_name")
    if not user_name:
        try:
             res = service_supabase.table("profiles").select("full_name").eq("id", current_user_id).single().execute()
             if res.data: user_name = res.data.get("full_name")
        except: user_name = "User"

    # State
    join_code_tf = ft.TextField(label="매장 초대 코드 (예: STORE-1234)", text_align=ft.TextAlign.CENTER)

    # [Business Verification]
    business_num_tf = ft.TextField(label="사업자 등록번호 (- 없이 입력)", text_align=ft.TextAlign.CENTER, input_filter=ft.InputFilter(regex_string=r"^[0-9]*$"))
    create_name_tf = ft.TextField(label="매장 이름 (자동 입력)", text_align=ft.TextAlign.CENTER, read_only=True, bgcolor="#F5F5F5")
    
    verified_biz_info = {"number": None, "owner": None}
    
    error_text = ft.Text("", color="red", size=12)

    def on_verify_biz(e):
        b_num = business_num_tf.value
        if not b_num or len(b_num) < 10:
            error_text.value = "올바른 사업자 번호 10자리를 입력해주세요."
            page.update()
            return
        
        # [MOCK API] Simulation of Hometax Lookup
        # In real world, use hometax API or crawling
        import asyncio
        async def verify_process():
            # Simulate network delay
            btn_verify.disabled = True; btn_verify.content = ft.ProgressRing(width=16, height=16); page.update()
            await asyncio.sleep(1.5)
            
            # Mock Result
            # Logic: 
            # Ends with '1': Mismatch (Hong Gil Dong)
            # Ends with '9': Match (Current User)
            # Others: Hong Gil Dong
            
            mock_owner = "홍길동"
            if b_num.endswith("9"):
                mock_owner = user_name
            
            if b_num.startswith("1") or b_num == "0000000000": 
                biz_name = f"(주)사업자_{b_num[-4:]}" 
                
                # Check Name Match
                is_match = (mock_owner == user_name)
                
                if not is_match:
                     error_text.value = f"❌ 명의 불일치: 사업자 대표({mock_owner})와 가입자({user_name})가 다릅니다."
                     error_text.color = "red"
                     create_name_tf.value = ""
                     verified_biz_info["number"] = None
                else:
                    create_name_tf.value = biz_name
                    create_name_tf.read_only = True
                    create_name_tf.bgcolor = "#E8F5E9" # Light Green
                    create_name_tf.label = "매장 이름 (인증됨)"
                    
                    verified_biz_info["number"] = b_num
                    verified_biz_info["owner"] = mock_owner
                    
                    error_text.value = "✅ 사업자 정보 및 본인 확인 완료."
                    error_text.color = "green"
            else:
                error_text.value = "❌ 등록되지 않은 사업자 번호입니다. (테스트: 1로 시작하면 성공)"
                error_text.color = "red"
                create_name_tf.value = ""
            
            btn_verify.disabled = False; btn_verify.content = ft.Text("조회"); page.update()

        page.run_task(verify_process)

    btn_verify = ft.ElevatedButton("조회", on_click=on_verify_biz, bgcolor="#455A64", color="white")
    
    def on_join(e):
        code = join_code_tf.value
        if not code:
            error_text.value = "초대 코드를 입력해주세요."
            page.update()
            return

        try:
            ch = channel_service.join_channel(current_user_id, code)
            complete_login(ch)
        except Exception as ex:
            error_text.value = f"가입 실패: {ex}"
            page.update()

    def on_create(e):
        name = create_name_tf.value
        if not name:
            error_text.value = "먼저 사업자 번호를 조회해주세요."
            page.update()
            return
            
        if not verified_biz_info["number"]:
             error_text.value = "사업자 인증이 필요합니다."
             page.update()
             return

        try:
            ch = channel_service.create_channel(
                current_user_id, 
                name,
                business_number=verified_biz_info["number"],
                business_owner=verified_biz_info["owner"]
            )
            complete_login(ch)
        except Exception as ex:
            error_text.value = f"생성 실패: {ex}"
            page.update()

    def complete_login(ch):
        page.session.set("channel_id", ch["id"])
        page.session.set("channel_name", ch["name"])
        page.session.set("user_role", ch["role"])
        page.snack_bar = ft.SnackBar(ft.Text(f"환영합니다! {ch['name']}에 접속했습니다."), open=True)
        page.update()
        navigate_to("home")

    # UI Components
    return [
        ft.SafeArea(expand=True, content=
        ft.Container(
            expand=True,
            bgcolor="white", # Clean White Theme
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.STOREFRONT_OUTLINED, size=64, color="#0A1929"),
                    ft.Text("환영합니다!", size=24, weight="bold", color="#0A1929"),
                    ft.Text("시작하려면 매장을 생성하거나 가입하세요.", size=14, color="grey"),
                    ft.Container(height=30),
                    
                    # Section 1: Create
                    ft.Container(
                        padding=20,
                        border=ft.border.all(1, "#EEEEEE"),
                        border_radius=10,
                        content=ft.Column([
                            ft.Text("새 매장 만들기 (사장님)", weight="bold", color="#0A1929"),
                            ft.Text("사업자 등록번호를 입력하여 매장을 개설하세요.", size=12, color="grey"),
                            ft.Row([business_num_tf, btn_verify], alignment="center"),
                            create_name_tf,
                            ft.ElevatedButton("매장 생성하기", on_click=on_create, width=200, height=45, bgcolor="#1565C0", color="white")
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                    ),
                    
                    ft.Text("OR", weight="bold", color="grey"),
                    
                    # Section 2: Join
                    ft.Container(
                        padding=20,
                        border=ft.border.all(1, "#EEEEEE"),
                        border_radius=10,
                        content=ft.Column([
                            ft.Text("기존 매장 합류 (직원)", weight="bold", color="#0A1929"),
                            join_code_tf,
                            ft.OutlinedButton("초대 코드로 입장", on_click=on_join, width=200, height=45, style=ft.ButtonStyle(color="#0A1929", side=ft.BorderSide(1, "#0A1929")))
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                    ),
                    
                    ft.Container(height=10),
                    error_text,
                    ft.TextButton("로그아웃", on_click=lambda _: navigate_to("login")),
                    
                    # [DEBUG DIAGNOSTIC]
                    ft.Divider(),
                    ft.Text(f"System Check (Temporary)", size=12, weight="bold", color="grey"),
                    ft.Text(f"Has Service Key: {has_service_key}", size=12, color="blue" if has_service_key else "red"),
                    ft.Text(f"Key Hint (Last 5): ...{service_key[-5:] if service_key else 'N/A'}", size=12, color="red" if service_key and service_key.endswith("sp5r0") else "green"),
                    ft.Text(f"Recent Log: {app_logs[-1] if app_logs else 'No logs'}", size=10, color="grey"),
                    ft.Text(f"User ID: {current_user_id}", size=10, color="grey")
                    
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20
            ),
            padding=20
        )
        )
    ]
