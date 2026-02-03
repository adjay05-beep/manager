import flet as ft
import asyncio

async def main(page: ft.Page):
    page.title = "JavaScript Bridge 상세 테스트"
    page.theme_mode = ft.ThemeMode.DARK
    
    # Create bridge
    bridge = ft.TextField(
        value="",
        hint_text="SYSTEM_JS_BRIDGE",
        width=300,
        height=50,
        border_color="blue",
        label="JavaScript Bridge"
    )
    
    log_text = ft.Column([], scroll=ft.ScrollMode.AUTO, height=400)
    
    def add_log(msg, color="white"):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_text.controls.append(
            ft.Text(f"[{timestamp}] {msg}", color=color, size=12)
        )
        if len(log_text.controls) > 50:
            log_text.controls.pop(0)
        page.update()
        print(f"[{timestamp}] {msg}")
    
    def on_bridge_change(e):
        val = e.control.value
        add_log(f"브리지 수신: {val}", "green")
    
    bridge.on_change = on_bridge_change
    
    async def test_1_simple_alert(e):
        add_log("=== 테스트 1: 간단한 alert ===", "yellow")
        js = "alert('JavaScript 실행됨!');"
        
        try:
            add_log(f"launch_url 호출 중...", "cyan")
            await page.launch_url(f"javascript:{js}")
            add_log("✓ launch_url 실행 완료", "green")
        except Exception as ex:
            add_log(f"✗ 오류: {ex}", "red")
    
    async def test_2_write_to_bridge(e):
        add_log("=== 테스트 2: 브리지에 쓰기 ===", "yellow")
        bridge.value = ""  # Reset
        
        js = """
        (function() {
            console.log('[TEST] Finding bridge...');
            const b = document.querySelector('input[hint_text="SYSTEM_JS_BRIDGE"]');
            if (!b) {
                alert('Bridge not found!');
                return;
            }
            console.log('[TEST] Bridge found:', b);
            b.value = 'TEST_SUCCESS_' + Date.now();
            b.dispatchEvent(new Event('input', {bubbles: true}));
            console.log('[TEST] Event dispatched');
        })();
        """
        
        try:
            add_log("launch_url 호출 중...", "cyan")
            await page.launch_url(f"javascript:{js}")
            add_log("✓ launch_url 실행 완료", "green")
            
            # Wait for response
            add_log("브리지 응답 대기 중 (5초)...", "cyan")
            for i in range(10):
                await asyncio.sleep(0.5)
                if bridge.value:
                    add_log(f"✓ 브리지 응답 받음: {bridge.value}", "green")
                    return
            add_log("✗ 타임아웃 - 브리지 응답 없음", "red")
        except Exception as ex:
            add_log(f"✗ 오류: {ex}", "red")
    
    async def test_3_gps(e):
        add_log("=== 테스트 3: GPS 가져오기 ===", "yellow")
        bridge.value = ""  # Reset
        
        js = """
        (function() {
            console.log('[GPS] Starting...');
            if (!navigator.geolocation) {
                alert('Geolocation not supported');
                return;
            }
            
            navigator.geolocation.getCurrentPosition(
                function(p) {
                    console.log('[GPS] Success:', p.coords);
                    const b = document.querySelector('input[hint_text="SYSTEM_JS_BRIDGE"]');
                    if (b) {
                        const data = JSON.stringify({lat: p.coords.latitude, lng: p.coords.longitude});
                        b.value = data;
                        b.dispatchEvent(new Event('input', {bubbles: true}));
                        console.log('[GPS] Sent to bridge:', data);
                    } else {
                        alert('Bridge not found!');
                    }
                },
                function(e) {
                    console.error('[GPS] Error:', e);
                    alert('GPS Error: ' + e.message);
                },
                {enableHighAccuracy: true, timeout: 10000, maximumAge: 0}
            );
        })();
        """
        
        try:
            add_log("launch_url 호출 중...", "cyan")
            await page.launch_url(f"javascript:{js}")
            add_log("✓ launch_url 실행 완료", "green")
            add_log("권한 요청 확인 후 승인해주세요", "yellow")
            
            # Wait for response
            add_log("GPS 응답 대기 중 (15초)...", "cyan")
            for i in range(30):
                await asyncio.sleep(0.5)
                if bridge.value:
                    add_log(f"✓ GPS 데이터 받음: {bridge.value}", "green")
                    return
            add_log("✗ 타임아웃 - GPS 응답 없음", "red")
        except Exception as ex:
            add_log(f"✗ 오류: {ex}", "red")
    
    async def open_debug_page(e):
        try:
            await page.launch_url("http://localhost:8888/static/gps_debug.html")
            add_log("✓ 디버그 페이지 열림", "green")
        except Exception as ex:
            add_log(f"✗ 오류: {ex}", "red")
    
    page.add(
        ft.Column([
            ft.Text("JavaScript Bridge 상세 테스트", size=24, weight="bold"),
            ft.Divider(),
            
            ft.Text("브리지 요소 (아래 필드에 JS가 데이터를 씁니다):", size=14),
            bridge,
            
            ft.Divider(),
            ft.Text("테스트:", size=16, weight="bold"),
            ft.Row([
                ft.ElevatedButton("1️⃣ Alert 테스트", on_click=test_1_simple_alert),
                ft.ElevatedButton("2️⃣ 브리지 쓰기", on_click=test_2_write_to_bridge),
                ft.ElevatedButton("3️⃣ GPS 테스트", on_click=test_3_gps),
            ]),
            ft.ElevatedButton("🔍 HTML 디버그 페이지 열기", on_click=open_debug_page, color="orange"),
            
            ft.Divider(),
            ft.Text("로그:", size=16, weight="bold"),
            ft.Container(
                content=log_text,
                bgcolor="#1a1a1a",
                padding=10,
                border_radius=8
            ),
            
            ft.Text("※ F12를 눌러 브라우저 콘솔도 확인하세요", color="grey", size=12)
        ], spacing=15, scroll=ft.ScrollMode.AUTO)
    )
    
    add_log("✓ 테스트 앱 시작됨", "green")
    add_log("힌트: 먼저 테스트 1번으로 JavaScript 실행 여부를 확인하세요", "yellow")

if __name__ == "__main__":
    print("\n" + "="*50)
    print("TEST APP STARTING ON: http://localhost:8890")
    print("="*50 + "\n")
    ft.app(target=main, port=8890, view=ft.AppView.WEB_BROWSER)
