import flet as ft
import asyncio

async def main(page: ft.Page):
    page.title = "JavaScript Bridge Test"
    
    # Create bridge
    bridge = ft.TextField(
        opacity=0.1,  # Slightly visible for debugging
        width=100,
        height=40,
        hint_text="BRIDGE",
        border_color="red"
    )
    
    result_text = ft.Text("결과: 대기 중...", size=16)
    
    def on_bridge_change(e):
        result_text.value = f"브리지 수신: {e.control.value}"
        page.update()
    
    bridge.on_change = on_bridge_change
    
    async def test_js_via_launch_url(e):
        result_text.value = "테스트 중..."
        page.update()
        
        # Simple alert test
        js_code = "alert('JavaScript is working!'); document.querySelector('input[placeholder=\"BRIDGE\"]').value='SUCCESS'; document.querySelector('input[placeholder=\"BRIDGE\"]').dispatchEvent(new Event('input', {bubbles: true}));"
        
        try:
            await page.launch_url(f"javascript:void({js_code})")
            result_text.value = "launch_url 실행됨. 알림창이 나타났나요?"
        except Exception as ex:
            result_text.value = f"오류: {ex}"
        
        page.update()
    
    async def test_gps_direct(e):
        result_text.value = "GPS 테스트 중..."
        page.update()
        
        js_code = """
        navigator.geolocation.getCurrentPosition(
            (p) => {
                const b = document.querySelector('input[placeholder="BRIDGE"]');
                if (b) {
                    b.value = JSON.stringify({lat: p.coords.latitude, lng: p.coords.longitude});
                    b.dispatchEvent(new Event('input', {bubbles: true}));
                } else {
                    alert('Bridge not found!');
                }
            },
            (e) => {
                const b = document.querySelector('input[placeholder="BRIDGE"]');
                if (b) {
                    b.value = JSON.stringify({error: e.message});
                    b.dispatchEvent(new Event('input', {bubbles: true}));
                } else {
                    alert('Bridge not found! Error: ' + e.message);
                }
            },
            {enableHighAccuracy: true, timeout: 10000, maximumAge: 0}
        );
        """
        
        try:
            await page.launch_url(f"javascript:{js_code}")
            result_text.value = "GPS 요청 실행됨. 권한 요청이 나타났나요?"
        except Exception as ex:
            result_text.value = f"오류: {ex}"
        
        page.update()
    
    page.add(
        ft.Column([
            ft.Text("JavaScript Bridge 테스트", size=24, weight="bold"),
            ft.Divider(),
            bridge,
            ft.ElevatedButton("1. JavaScript 실행 테스트", on_click=test_js_via_launch_url),
            ft.ElevatedButton("2. GPS 직접 테스트", on_click=test_gps_direct),
            ft.Divider(),
            result_text,
            ft.Text("※ F12를 눌러 개발자 도구 콘솔을 확인하세요", color="grey", size=12)
        ], spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

if __name__ == "__main__":
    ft.app(target=main, port=8889, view=ft.AppView.WEB_BROWSER)
