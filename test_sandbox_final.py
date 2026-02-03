import flet as ft
import asyncio
import json

async def main(page: ft.Page):
    page.title = "Final Pulse Sandbox"
    page.theme_mode = ft.ThemeMode.DARK

    log_column = ft.Column(scroll=ft.ScrollMode.AUTO, height=400, spacing=5)
    
    def add_log(msg, color="white"):
        from datetime import datetime
        log_column.controls.append(
            ft.Text(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", color=color, size=13)
        )
        page.update()

    def process_data(val):
        try:
            if val.startswith("RESULT:"): val = val[7:]
            data = json.loads(val)
            if "lat" in data:
                add_log(f"🎯 위치 수집 성공: {data['lat']}, {data['lng']}", "green")
            elif "error" in data:
                add_log(f"❌ GPS 오류 수신: {data['error']}", "red")
        except:
            add_log(f"❓ 분석 실패 (수동 입력 필드 활용하세요)", "yellow")

    # --- 펄스 수신기 (Pulse Sensor) ---
    async def pulse_monitor():
        # Flet 0.8.x에서 JS를 실행해 데이터를 타이틀로 가져오는 스크립트
        # 저장소에 flet_gps_data가 있으면 타이틀을 RESULT:... 로 바꿉니다.
        script = """
        var data = localStorage.getItem('flet_gps_data');
        if (data) {
            document.title = "RESULT:" + data;
            localStorage.removeItem('flet_gps_data');
        }
        """
        while True:
            # 매 0.5초마다 브라우저 타이틀을 강제 동기화
            page.title = f"JS:{script}"
            page.update()
            
            # 만약 타이틀이 데이터로 바뀌어 있다면 낚아챔
            # (Flet은 브라우저에서 바뀐 타이틀을 다시 Python page.title로 가져옵니다)
            await asyncio.sleep(0.5)
            if page.title.startswith("RESULT:"):
                add_log("📥 펄스 감지! 데이터 자동 회수됨", "orange")
                process_data(page.title)
                page.title = "Final Pulse Sandbox"
                page.update()
            
            await asyncio.sleep(0.5)

    def on_manual_submit(e):
        if e.control.value:
            add_log("📥 수동 입력 수신됨", "cyan")
            process_data(e.control.value)
            e.control.value = ""
            page.update()

    page.add(
        ft.Container(
            content=ft.Column([
                ft.Text("Pulse Bridge Sandbox (8896)", size=24, weight="bold"),
                ft.Text("보안 차단이 불가능한 '자기암시(Self-Title)' 방식", color="grey"),
                ft.Divider(),
                
                ft.ElevatedButton(
                    "📍 GPS 정보 가져오기 (자동 전송 보장)", 
                    url="/gps_bridge.html",
                    bgcolor="blue", 
                    color="white",
                    height=60, width=350
                ),
                
                ft.Divider(),
                ft.Text("방법 2: 복사한 데이터를 아래에 직접 붙여넣기", size=16),
                ft.TextField(
                    label="수동 입력",
                    hint_text='{"lat": ...}',
                    on_submit=on_manual_submit,
                    width=450
                ),
                
                ft.Divider(),
                ft.Text("실시간 수신 로그:", size=16, weight="bold"),
                ft.Container(content=log_column, bgcolor="#1a1a1a", padding=15, border_radius=10, expand=True)
            ], spacing=20),
            padding=30
        )
    )

    # 펄스 시작
    asyncio.create_task(pulse_monitor())
    add_log("✓ 무선 펄스 감지기 가동 중...")

if __name__ == "__main__":
    ft.app(target=main, port=8896, assets_dir="assets", view=ft.AppView.WEB_BROWSER)
