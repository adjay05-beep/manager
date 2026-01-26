import flet as ft
from views.closing_view import get_closing_controls

def get_work_controls(page: ft.Page, navigate_to):
    # Tabs: Labor Info, Tax Info, Closing Check
    
    # 1. Labor Info (No-mu)
    labor_content = ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text("2026년 최저시급안내", size=20, weight="bold", color="#333333"),
                ft.Container(height=10),
                ft.Row([
                    ft.Icon(ft.Icons.MONETIZATION_ON, color="green", size=30),
                    ft.Text("10,320원", size=30, weight="bold", color="green"),
                    ft.Text("(전년 대비 +1.7%)", size=14, color="grey")
                ], alignment="center"),
                ft.Divider(),
                ft.Text("주휴수당이란?", weight="bold", size=16),
                ft.Text("1주 동안 규정된 근무일수를 다 채운 근로자에게 유급 주휴일을 주는 것.", size=12, color="grey"),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Column([
                        ft.Text("주휴수당 계산법", weight="bold", color="white"),
                        ft.Text("(1주 근로시간 / 40) × 8 × 시급", color="white", size=16),
                        ft.Text("* 주 15시간 이상 근무 시 적용", size=12, color="white70")
                    ]),
                    bgcolor="#2196F3", padding=20, border_radius=10, width=400
                )
            ]),
            padding=20, bgcolor="white", border_radius=10, shadow=ft.BoxShadow(blur_radius=5, color="#05000000")
        )
    ], scroll=ft.ScrollMode.AUTO)

    # 2. Tax Info (Se-mu)
    tax_content = ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text("일반 vs 간이 과세자", size=20, weight="bold", color="#333333"),
                ft.Container(height=10),
                 ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("구분")),
                        ft.DataColumn(ft.Text("일반과세자")),
                        ft.DataColumn(ft.Text("간이과세자")),
                    ],
                    rows=[
                        ft.DataRow(cells=[ft.DataCell(ft.Text("기준")), ft.DataCell(ft.Text("연 1.04억 이상")), ft.DataCell(ft.Text("연 1.04억 미만"))]),
                        ft.DataRow(cells=[ft.DataCell(ft.Text("세율")), ft.DataCell(ft.Text("10%")), ft.DataCell(ft.Text("1.5~4%"))]),
                        ft.DataRow(cells=[ft.DataCell(ft.Text("신고")), ft.DataCell(ft.Text("1월, 7월")), ft.DataCell(ft.Text("1월"))]),
                    ],
                    width=400,
                ),
                ft.Divider(),
                ft.Text("주요 세무 일정", weight="bold", size=16),
                ft.ListTile(leading=ft.Icon(ft.Icons.CALENDAR_MONTH, color="red"), title=ft.Text("1월 25일"), subtitle=ft.Text("부가세 확정 신고 (모두)")),
                ft.ListTile(leading=ft.Icon(ft.Icons.CALENDAR_MONTH, color="blue"), title=ft.Text("5월 31일"), subtitle=ft.Text("종합소득세 신고")),
                ft.ListTile(leading=ft.Icon(ft.Icons.CALENDAR_MONTH, color="orange"), title=ft.Text("7월 25일"), subtitle=ft.Text("부가세 확정 신고 (일반)")),
            ]),
            padding=20, bgcolor="white", border_radius=10, shadow=ft.BoxShadow(blur_radius=5, color="#05000000")
        )
    ], scroll=ft.ScrollMode.AUTO)

    # 3. Closing Check (Existing View)
    # We need to wrap it specifically because get_closing_controls returns a list of controls [ft.Stack or Container]
    closing_controls_list = get_closing_controls(page, navigate_to)
    closing_content = closing_controls_list[0] # Assuming it returns one main container
    
    # 4. Contracts (Placeholder for next step)
    contract_content = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.HANDSHAKE, size=50, color="#EEEEEE"),
            ft.Text("근로계약서 관리", weight="bold"),
            ft.Text("직원별 계약서를 작성하고 급여를 자동 계산합니다.", color="grey"),
            ft.ElevatedButton("새 계약서 작성", on_click=lambda _: page.snack_bar.open.__setattr__("content", ft.Text("준비 중입니다.")) or page.update())
        ], horizontal_alignment="center", alignment="center"),
        alignment=ft.alignment.center, padding=50
    )


    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="노무 정보", icon=ft.Icons.WORK),
            ft.Tab(text="세무 가이드", icon=ft.Icons.ATTACH_MONEY),
            ft.Tab(text="마감 점검", icon=ft.Icons.CHECK_CIRCLE),
            ft.Tab(text="계약 관리", icon=ft.Icons.FOLDER_SHARED),
        ],
        expand=True
    )

    # We need to switch content based on Tab
    body = ft.Container(content=labor_content, expand=True)

    def on_tab_change(e):
        idx = e.control.selected_index
        if idx == 0: body.content = labor_content
        elif idx == 1: body.content = tax_content
        elif idx == 2: body.content = closing_content
        elif idx == 3: body.content = contract_content
        page.update()

    tabs.on_change = on_tab_change

    header = ft.Container(
        content=ft.Row([
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to("home")), 
                ft.Text("업무 지원", size=20, weight="bold")
            ]), 
        ], alignment="spaceBetween"), 
        padding=10, 
        border=ft.border.only(bottom=ft.border.BorderSide(1, "#EEEEEE"))
    )

    return [
        ft.Column([
            ft.Container(header, bgcolor="white"),
            tabs,
            ft.Container(body, expand=True, padding=10)
        ], spacing=0, expand=True)
    ]
