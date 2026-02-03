import flet as ft
import asyncio
import json
import re

async def main(page: ft.Page):
    page.title = "Title Bridge Sandbox"
    page.theme_mode = ft.ThemeMode.DARK

    # --- UI Components define early ---
    log_column = ft.Column(scroll=ft.ScrollMode.AUTO, height=400, spacing=5)
    
    def add_log(msg, color="white"):
        from datetime import datetime
        log_column.controls.append(
            ft.Text(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", color=color, size=13)
        )
        page.update()

    # --- Attribute Inspection ---
    add_log("🔍 Page 속성 조사 중...", "yellow")
    page_attrs = dir(page)
    js_related = [a for a in page_attrs if "js" in a.lower() or "run" in a.lower() or "eval" in a.lower()]
    add_log(f"발견된 관련 속성: {', '.join(js_related)}", "cyan")
    
    if "run_javascript" in page_attrs:
        add_log("✅ 이 버전은 run_javascript를 지원합니다!", "green")
    else:
        add_log("❌ run_javascript 속성이 없습니다.", "red")

    # --- Title Bridge Implementation ---
    page._js_result = None
    page._js_event = asyncio.Event()

    async def on_title_change(e):
        if page.title and page.title.startswith("RESULT:"):
            res_json = page.title[7:]
            add_log(f"📥 Title Bridge 데이터 수신: {res_json[:100]}...", "green")
            page._js_result = res_json
            page._js_event.set()
            page.title = "Title Bridge Sandbox" # Restore
            page.update()

    page.on_title_change = on_title_change

    # Create a hidden container for JS injection
    js_container = ft.Column(width=0, height=0)
    page.overlay.append(js_container)

    async def run_js(script, return_value=False):
        minified = re.sub(r"\s+", " ", script).strip()
        if return_value:
            wrapped = (
                f"(async()=>{{try{{"
                f"let r=await({minified});"
                f"document.title='RESULT:'+(typeof r==='object'?JSON.stringify(r):String(r));"
                f"}}catch(e){{"
                f"document.title='RESULT:'+JSON.stringify({{error:e.toString()}});"
                f"}}}}).call();"
            )
        else:
            wrapped = minified

        add_log(f"🚀 JS 주입 시도 (Markdown Injection)...", "cyan")
        injection_html = f"<img src='x' onerror=\"{wrapped}\" style='display:none;'>"
        
        try:
            js_container.controls.clear()
            js_container.controls.append(
                ft.Markdown(
                    value=injection_html,
                    extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                )
            )
            page.update()
            add_log("✓ Injection 요소 생성됨", "blue")
        except Exception as ex:
            add_log(f"✗ 주입 실패: {ex}", "red")
            return None

        if return_value:
            page._js_event.clear()
            page._js_result = None
            try:
                await asyncio.wait_for(page._js_event.wait(), timeout=10.0)
                return page._js_result
            except asyncio.TimeoutError:
                add_log("✗ 타임아웃: 실행되지 않았거나 응답이 없습니다.", "red")
                return None
        return None

    # --- Action Functions ---
    async def test_alert(e):
        add_log("테스트: 단순 Alert 실행 중...", "yellow")
        await run_js("alert('Injected JS!')")

    async def test_bridge(e):
        add_log("테스트: 브리지 통신 확인 중...", "yellow")
        res = await run_js("Date.now()", return_value=True)
        if res:
            add_log(f"✅ 통신 성공! 수신값: {res}", "green")

    async def test_gps(e):
        add_log("테스트: GPS 권한 요청 및 데이터 수신...", "yellow")
        js_gps = """
        new Promise((resolve, reject) => {
            if (!navigator.geolocation) return resolve({error: 'GPS지원안함'});
            navigator.geolocation.getCurrentPosition(
                (p) => resolve({lat: p.coords.latitude, lng: p.coords.longitude}),
                (e) => resolve({error: e.message}),
                {enableHighAccuracy: true, timeout: 10000}
            );
        })
        """
        res = await run_js(js_gps, return_value=True)
        if res:
            add_log(f"🎯 GPS 수신 완료: {res}", "green")
            try:
                data = json.loads(res)
                if "lat" in data:
                    add_log(f"📍 위도: {data['lat']}, 경도: {data['lng']}", "white")
            except: pass

    page.add(
        ft.Container(
            content=ft.Column([
                ft.Text("Title Bridge Sandbox", size=28, weight="bold"),
                ft.Text("Flet 0.80.5 JavaScript 통신 검증 도구", color="grey"),
                ft.Divider(),
                ft.Text("5. 팝업 브리지 테스트 (최종 해결책):", size=16, weight="bold"),
                ft.ElevatedButton(
                    "📍 팝업으로 GPS 가져오기 (Direct Link)", 
                    url="/static/gps_bridge.html",
                    bgcolor="red", 
                    color="white",
                    height=50
                ),
                ft.Divider(),
                ft.Text("실행 로그:", size=16, weight="bold"),
                ft.Container(
                    content=log_column,
                    bgcolor="#1a1a1a",
                    padding=15,
                    border_radius=10,
                    expand=True,
                    border=ft.border.all(1, "#333")
                ),
            ]),
            padding=30,
            expand=True
        )
    )
    add_log("✓ 샌드박스 준비 완료. 포트 8895 접속.", "green")
    add_log("주의: 8895 포트로 접속하고 버튼을 누른 뒤 새 창이 뜨는지 보세요.", "yellow")

if __name__ == "__main__":
    ft.app(target=main, port=8895, assets_dir="static", view=ft.AppView.WEB_BROWSER)
