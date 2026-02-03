import flet as ft
import asyncio
import json
from views.styles import AppColors, AppLayout, AppTextStyles, AppButtons
from views.components.app_header import AppHeader
from utils.sys_logger import sys_log


async def get_gps_test_controls(page: ft.Page, navigate_to):
    """GPS 기능 테스트를 위한 전용 뷰"""
    
    # UI State
    gps_status = ft.Text(
        "대기 중...",
        size=16,
        color=AppColors.TEXT_SECONDARY,
        weight="w500"
    )
    
    gps_result = ft.Container(
        content=ft.Column([
            ft.Text("GPS 결과", size=14, weight="bold", color=AppColors.TEXT_PRIMARY),
            ft.Container(height=10),
            ft.Text("아직 GPS를 가져오지 않았습니다.", size=12, color=AppColors.TEXT_SECONDARY)
        ]),
        padding=20,
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.GREY_400),
        border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.GREY_400))
    )
    
    console_log = ft.Column(
        [],
        scroll=ft.ScrollMode.AUTO,
        spacing=5
    )
    
    console_container = ft.Container(
        content=console_log,
        padding=15,
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLACK),
        border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.GREY_400)),
        height=250
    )
    
    def add_log(message, log_type="info"):
        """콘솔에 로그 추가"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        color = AppColors.TEXT_SECONDARY
        icon = "ℹ️"
        if log_type == "success":
            color = AppColors.SUCCESS
            icon = "✓"
        elif log_type == "error":
            color = AppColors.ERROR
            icon = "✗"
        elif log_type == "info":
            color = AppColors.PRIMARY
            icon = "→"
        
        log_entry = ft.Row([
            ft.Text(f"{icon}", size=12),
            ft.Text(f"[{timestamp}]", size=11, color=ft.Colors.GREY_500),
            ft.Text(message, size=11, color=color)
        ], spacing=8)
        
        console_log.controls.append(log_entry)
        
        # Keep only last 20 logs
        if len(console_log.controls) > 20:
            console_log.controls.pop(0)
        
        console_container.update()
        sys_log(f"GPS_TEST: {message}")
    
    # GPS Bridge
    gps_event = asyncio.Event()
    gps_data_result = {"data": None}
    
    async def on_gps_bridge_change(e):
        val = e.control.value
        if not val or val == "GPS_TEST_BRIDGE_INIT":
            return
        gps_data_result["data"] = val
        gps_event.set()
    
    gps_bridge = ft.TextField(
        value="GPS_TEST_BRIDGE_INIT",
        hint_text="GPS_TEST_BRIDGE",
        width=1,
        height=1,
        opacity=0.01,
        on_change=on_gps_bridge_change
    )
    
    async def test_gps_basic(e):
        """기본 GPS 가져오기 테스트"""
        btn = e.control
        btn.disabled = True
        btn.text = "GPS 가져오는 중..."
        btn.update()
        
        gps_status.value = "GPS 위치 확인 중..."
        gps_status.color = AppColors.PRIMARY
        gps_status.update()
        
        add_log("GPS 테스트 시작...", "info")
        
        try:
            # Reset bridge
            gps_event.clear()
            gps_data_result["data"] = None
            gps_bridge.value = "GPS_TEST_BRIDGE_INIT"
            gps_bridge.update()
            
            add_log("JavaScript 브리지 호출 중...", "info")
            
            # Execute JavaScript
            await page.run_javascript(
                "(function(){"
                "  try {"
                "    const bridge = document.querySelector('input[placeholder=\"GPS_TEST_BRIDGE\"]');"
                "    if (!navigator.geolocation) {"
                "      if(bridge) { bridge.value = JSON.stringify({error: 'GPS를 지원하지 않는 브라우저입니다'}); bridge.dispatchEvent(new Event('input', {bubbles:true})); }"
                "      return;"
                "    }"
                "    navigator.geolocation.getCurrentPosition("
                "      (pos) => {"
                "        if(bridge) {"
                "          bridge.value = JSON.stringify({lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy});"
                "          bridge.dispatchEvent(new Event('input', {bubbles:true}));"
                "        }"
                "      },"
                "      (err) => {"
                "        if(bridge) {"
                "          bridge.value = JSON.stringify({error: err.message, code: err.code});"
                "          bridge.dispatchEvent(new Event('input', {bubbles:true}));"
                "        }"
                "      },"
                "      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }"
                "    );"
                "  } catch(e) { console.error('GPS Test JS Error:', e); }"
                "})()"
            )
            
            add_log("브라우저 응답 대기 중... (최대 15초)", "info")
            
            # Wait for response
            try:
                await asyncio.wait_for(gps_event.wait(), timeout=16.0)
                add_log("브리지 응답 수신 완료!", "success")
            except asyncio.TimeoutError:
                add_log("타임아웃! 브라우저가 응답하지 않습니다.", "error")
                gps_status.value = "❌ 타임아웃"
                gps_status.color = AppColors.ERROR
                gps_status.update()
                btn.disabled = False
                btn.text = "📍 GPS 가져오기"
                btn.update()
                return
            
            # Parse result
            if gps_data_result["data"]:
                try:
                    data = json.loads(gps_data_result["data"])
                    
                    if "error" in data:
                        error_msg = data["error"]
                        error_code = data.get("code", "알 수 없음")
                        add_log(f"GPS 오류: {error_msg} (코드: {error_code})", "error")
                        
                        gps_status.value = f"❌ 오류: {error_msg}"
                        gps_status.color = AppColors.ERROR
                        
                        gps_result.content = ft.Column([
                            ft.Text("GPS 오류", size=14, weight="bold", color=AppColors.ERROR),
                            ft.Container(height=5),
                            ft.Text(f"• 오류 메시지: {error_msg}", size=12, color=AppColors.TEXT_SECONDARY),
                            ft.Text(f"• 오류 코드: {error_code}", size=12, color=AppColors.TEXT_SECONDARY),
                            ft.Container(height=10),
                            ft.Text("💡 해결 방법:", size=12, weight="bold", color=AppColors.PRIMARY),
                            ft.Text("1. 브라우저 설정에서 위치 권한을 허용해주세요", size=11, color=AppColors.TEXT_SECONDARY),
                            ft.Text("2. HTTP가 아닌 HTTPS 환경에서 테스트해주세요", size=11, color=AppColors.TEXT_SECONDARY),
                            ft.Text("3. 위치 서비스가 켜져있는지 확인해주세요", size=11, color=AppColors.TEXT_SECONDARY),
                        ], spacing=5)
                    else:
                        lat = data.get("lat")
                        lng = data.get("lng")
                        accuracy = data.get("accuracy", "알 수 없음")
                        
                        add_log(f"✓ GPS 성공! 위도: {lat:.6f}, 경도: {lng:.6f}", "success")
                        add_log(f"정확도: {accuracy}m", "info")
                        
                        gps_status.value = f"✓ 성공!"
                        gps_status.color = AppColors.SUCCESS
                        
                        gps_result.content = ft.Column([
                            ft.Text("GPS 결과", size=14, weight="bold", color=AppColors.SUCCESS),
                            ft.Container(height=10),
                            ft.Container(
                                content=ft.Column([
                                    ft.Row([
                                        ft.Icon(ft.Icons.LOCATION_ON, size=16, color=AppColors.PRIMARY),
                                        ft.Text("위치 정보", size=12, weight="bold", color=AppColors.TEXT_PRIMARY)
                                    ], spacing=5),
                                    ft.Container(height=5),
                                    ft.Text(f"위도 (Latitude): {lat:.6f}", size=12, color=AppColors.TEXT_SECONDARY),
                                    ft.Text(f"경도 (Longitude): {lng:.6f}", size=12, color=AppColors.TEXT_SECONDARY),
                                    ft.Text(f"정확도: {accuracy}m", size=12, color=AppColors.TEXT_SECONDARY),
                                ], spacing=3),
                                padding=10,
                                border_radius=8,
                                bgcolor=ft.Colors.with_opacity(0.05, AppColors.SUCCESS)
                            )
                        ], spacing=5)
                    
                except json.JSONDecodeError as je:
                    add_log(f"JSON 파싱 오류: {je}", "error")
                    gps_status.value = "❌ 데이터 파싱 실패"
                    gps_status.color = AppColors.ERROR
            else:
                add_log("브리지 데이터가 비어있습니다", "error")
                gps_status.value = "❌ 데이터 없음"
                gps_status.color = AppColors.ERROR
            
        except Exception as ex:
            add_log(f"예외 발생: {ex}", "error")
            gps_status.value = f"❌ 오류: {ex}"
            gps_status.color = AppColors.ERROR
        
        finally:
            btn.disabled = False
            btn.text = "📍 GPS 가져오기"
            gps_status.update()
            gps_result.update()
            btn.update()
    
    async def clear_console(e):
        """콘솔 로그 지우기"""
        console_log.controls.clear()
        add_log("콘솔 초기화됨", "info")
        console_container.update()
    
    # Buttons
    btn_test_gps = ft.ElevatedButton(
        "📍 GPS 가져오기",
        bgcolor=AppColors.PRIMARY,
        color="white",
        height=50,
        on_click=lambda e: asyncio.create_task(test_gps_basic(e))
    )
    
    btn_clear = ft.OutlinedButton(
        "🗑️ 콘솔 지우기",
        height=50,
        on_click=clear_console
    )
    
    # Header
    header = AppHeader(
        title_text="GPS 테스트",
        on_back_click=lambda _: asyncio.create_task(navigate_to("home"))
    )
    
    # Main Content
    content = ft.Column([
        header,
        ft.Container(
            padding=20,
            expand=True,
            content=ft.Column([
                # Info Card
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.INFO_OUTLINE, size=20, color=AppColors.PRIMARY),
                            ft.Text("GPS 기능 테스트", size=16, weight="bold", color=AppColors.TEXT_PRIMARY)
                        ], spacing=10),
                        ft.Container(height=10),
                        ft.Text(
                            "이 페이지에서 GPS 기능이 정상적으로 작동하는지 테스트할 수 있습니다.",
                            size=12,
                            color=AppColors.TEXT_SECONDARY
                        )
                    ]),
                    padding=15,
                    border_radius=12,
                    bgcolor=ft.Colors.with_opacity(0.05, AppColors.PRIMARY)
                ),
                
                ft.Container(height=20),
                
                # Status
                ft.Container(
                    content=ft.Column([
                        ft.Text("상태", size=12, weight="bold", color=AppColors.TEXT_SECONDARY),
                        ft.Container(height=5),
                        gps_status
                    ]),
                    padding=15,
                    border_radius=12,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.GREY_400))
                ),
                
                ft.Container(height=20),
                
                # Result
                gps_result,
                
                ft.Container(height=20),
                
                # Buttons
                ft.Row([
                    btn_test_gps,
                    btn_clear
                ], spacing=10),
                
                ft.Container(height=20),
                
                # Console Log
                ft.Text("콘솔 로그", size=14, weight="bold", color=AppColors.TEXT_PRIMARY),
                ft.Container(height=5),
                console_container,
                
                # Bridge (hidden)
                gps_bridge
                
            ], scroll=ft.ScrollMode.AUTO)
        )
    ], spacing=0, expand=True)
    
    # Initialize log
    add_log("GPS 테스트 페이지 로드 완료", "success")
    add_log("준비 완료. '📍 GPS 가져오기' 버튼을 클릭하세요.", "info")
    
    return [
        ft.SafeArea(expand=True, content=content)
    ]
