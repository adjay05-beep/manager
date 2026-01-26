import flet as ft
from db import service_supabase
import asyncio
import os

def get_work_controls(page: ft.Page, navigate_to):
    # Tabs: Contracts, Labor Info, Tax Info
    
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

    # [REMOVED] Closing Check (Moved to separate view)
    
    # 4. Contracts Logic & UI
    contract_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    
    # Form Inputs (Black Text)
    c_name = ft.TextField(label="직원 이름", width=150, color="black", label_style=ft.TextStyle(color="grey"))
    c_type = ft.Dropdown(label="근로 형태", width=150, options=[ft.dropdown.Option("full", "정규직"), ft.dropdown.Option("part", "아르바이트")], value="part", color="black", label_style=ft.TextStyle(color="grey"))
    c_wage = ft.TextField(label="시급 (원)", width=150, value="10320", color="black", label_style=ft.TextStyle(color="grey"))
    c_hours = ft.TextField(label="일 근무시간", width=150, value="8", color="black", label_style=ft.TextStyle(color="grey"))
    
    # Days Selector (0=Mon, 6=Sun)
    days_map = {0:"월", 1:"화", 2:"수", 3:"목", 4:"금", 5:"토", 6:"일"}
    selected_days = []
    
    def toggle_day(e):
        day_idx = e.control.data
        if day_idx in selected_days: selected_days.remove(day_idx); e.control.bgcolor = None; e.control.color = "black"
        else: selected_days.append(day_idx); e.control.bgcolor = "green"; e.control.color = "white"
        e.control.update()
        
    day_buttons = ft.Row([ft.Container(content=ft.Text(label), data=idx, width=40, height=40, border_radius=20, alignment=ft.alignment.center, border=ft.border.all(1, "grey"), on_click=toggle_day, ink=True) for idx, label in days_map.items()], alignment="center")

    async def load_contracts_async():
        user_id = page.session.get("user_id")
        if not user_id: return
        
        try:
            # [FIX] Use Authenticated Client (Bypass RLS)
            from services.auth_service import auth_service
            from postgrest import SyncPostgrestClient
            
            headers = auth_service.get_auth_headers()
            if not headers:
                print("ERROR: No auth headers, cannot load contracts")
                return
            
            url = os.environ.get("SUPABASE_URL")
            client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public", timeout=20)
            
            res = await asyncio.to_thread(lambda: client.from_("labor_contracts").select("*").eq("user_id", user_id).order("created_at", desc=True).execute())
            contracts = res.data or []
            
            contract_list.controls.clear()
            for c in contracts:
                w_days = [days_map[d] for d in c.get('work_days', []) if d in days_map]
                day_str = ",".join(w_days)
                
                contract_list.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(c['employee_name'], weight="bold", size=16),
                                ft.Container(content=ft.Text("알바" if c['employee_type']=='part' else "정규", size=10, color="white"), bgcolor="orange", padding=5, border_radius=5)
                            ], alignment="spaceBetween"),
                            ft.Text(f"시급: {c['hourly_wage']:,}원 | {day_str} 근무", size=12, color="grey"),
                            ft.Text(f"계약일: {c['contract_start_date']}", size=10, color="grey")
                        ]),
                        padding=15, bgcolor="white", border_radius=10, border=ft.border.all(1, "#EEEEEE")
                    )
                )
            page.update()
        except Exception as e:
            print(f"Load Error: {e}")

    def save_contract_click(e):
        async def _save():
            if not c_name.value: return
            user_id = page.session.get("user_id")
            if not user_id: 
                page.snack_bar = ft.SnackBar(ft.Text("로그인이 필요합니다.")); page.snack_bar.open=True; page.update(); return
            
            data = {
                "user_id": user_id,
                "employee_name": c_name.value,
                "employee_type": c_type.value,
                "hourly_wage": int(c_wage.value),
                "daily_work_hours": float(c_hours.value),
                "work_days": selected_days,
                "contract_start_date": "2026-01-01" # Default for now
            }
            try:
                # [FIX] Use Authenticated Client
                from services.auth_service import auth_service
                from postgrest import SyncPostgrestClient
                
                headers = auth_service.get_auth_headers()
                if not headers:
                    raise Exception("세션이 만료되었습니다. 다시 로그인해주세요.")
                
                url = os.environ.get("SUPABASE_URL")
                client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers, schema="public", timeout=20)
                
                await asyncio.to_thread(lambda: client.from_("labor_contracts").insert(data).execute())
                await load_contracts_async()
                c_name.value = ""
                page.update()
                
                # Show Preview
                day_labels = [days_map[d] for d in selected_days]
                preview_text = (
                    f"========== 근로계약서 (예시) ==========\n\n"
                    f"성명: {data['employee_name']}\n"
                    f"유형: {'아르바이트' if data['employee_type']=='part' else '정규직'}\n"
                    f"시급: {data['hourly_wage']:,}원\n"
                    f"근무시간: 일 {data['daily_work_hours']}시간\n"
                    f"근무요일: {', '.join(day_labels)}\n\n"
                    f"위 조건으로 2026년 근로 계약을 체결합니다.\n"
                    f"====================================="
                )
                
                def close_dlg(e):
                    dlg_preview.open = False
                    page.update()
                    
                dlg_preview = ft.AlertDialog(
                    title=ft.Text("계약서 생성 완료"),
                    content=ft.Text(preview_text, size=14, font_family="monospace"),
                    actions=[ft.TextButton("확인", on_click=close_dlg)]
                )
                
                # [FIX] Legacy Dialog Open for Compatibility
                page.dialog = dlg_preview
                dlg_preview.open = True
                page.update()

            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"저장 실패: {ex}")); page.snack_bar.open=True; page.update()
        
        page.run_task(_save)

    contract_content = ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text("직원 등록 (근로계약 정보)", weight="bold", size=16, color="black"),
                ft.Container(height=10),
                ft.Row([c_name, c_type]),
                ft.Row([c_wage, c_hours]),
                ft.Text("근무 요일 선택", size=12, color="grey"),
                day_buttons,
                ft.Container(height=10),
                ft.ElevatedButton("저장 및 계약 생성", on_click=save_contract_click, width=300, bgcolor="#1A237E", color="white")
            ]),
            padding=20, bgcolor="white", border_radius=10, shadow=ft.BoxShadow(blur_radius=5, color="#05000000")
        ),
        ft.Divider(),
        ft.Text("나의 직원 리스트", weight="bold"),
        contract_list
    ], scroll=ft.ScrollMode.AUTO)


    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="계약 관리", icon=ft.Icons.FOLDER_SHARED),
            ft.Tab(text="노무 정보", icon=ft.Icons.WORK),
            ft.Tab(text="세무 가이드", icon=ft.Icons.ATTACH_MONEY),
        ],
        expand=True
    )

    # We need to switch content based on Tab
    # Initial: Contract (Index 0)
    body = ft.Container(content=contract_content, expand=True)
    # Trigger load for initial
    page.run_task(load_contracts_async)

    def on_tab_change(e):
        idx = e.control.selected_index
        if idx == 0: 
            body.content = contract_content
            page.run_task(load_contracts_async)
        elif idx == 1: body.content = labor_content
        elif idx == 2: body.content = tax_content
        page.update()

    tabs.on_change = on_tab_change

    header = ft.Container(
        content=ft.Row([
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to("home")), 
                ft.Text("직원 관리", size=20, weight="bold")
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
