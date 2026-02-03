import flet as ft
import asyncio
from datetime import datetime
from views.styles import AppColors, AppLayout, AppTextStyles, AppButtons, AppGradients, AppShadows
from views.components.app_header import AppHeader
from services.attendance_service import attendance_service
from services.channel_service import channel_service
from db import service_supabase
import json
import math

class SelectableCard(ft.Container):
    def __init__(self, label, icon, value, selected=False, on_change=None):
        super().__init__()
        self.label = label
        self.icon_name = icon
        self.value = value
        self.selected = selected
        self.on_change = on_change
        
        self.icon_control = ft.Icon(
            self.icon_name, 
            color="white" if self.selected else AppColors.TEXT_SECONDARY, 
            size=28
        )
        self.text_control = ft.Text(
            self.label, 
            color="white" if self.selected else AppColors.TEXT_SECONDARY, 
            size=13, 
            weight="bold"
        )
        
        self.content = ft.Column([
            self.icon_control,
            self.text_control
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8)
        
        self.width = 140
        self.height = 90
        self.border_radius = 16
        self.alignment = ft.Alignment(0, 0)  # Center alignment (Flet 0.80+ compatible)
        self.on_click = self._handle_click
        self.animate = ft.Animation(300, ft.AnimationCurve.DECELERATE)
        self._update_style()

    def _update_style(self):
        if self.selected:
            self.gradient = AppGradients.PRIMARY_LINEAR
            self.shadow = AppShadows.GLOW
            self.border = None
        else:
            self.bgcolor = ft.Colors.with_opacity(0.1, ft.Colors.GREY_400)
            self.border = ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.GREY_400))
            self.shadow = None
            self.gradient = None

    def _handle_click(self, e):
        if not self.selected:
            if self.on_change:
                self.on_change(self.value)

    def set_selected(self, selected):
        self.selected = selected
        self._update_style()
        self.icon_control.color = "white" if self.selected else AppColors.TEXT_SECONDARY
        self.text_control.color = "white" if self.selected else AppColors.TEXT_SECONDARY
        self.update()

async def get_attendance_controls(page: ft.Page, navigate_to):
    # Get Current Session Info
    user_id = page.app_session.get("user_id")
    channel_id = page.app_session.get("channel_id")
    user_role = page.app_session.get("role") or "staff"

    # Get Channel Settings (auth_mode, location)
    channel_auth_mode = "location"  # default
    channel_lat, channel_lng = None, None
    channel_wifi_ssid = None
    
    try:
        channel_res = service_supabase.table("channels").select("auth_mode, location_lat, location_lng, wifi_ssid").eq("id", channel_id).single().execute()
        if channel_res.data:
            channel_auth_mode = channel_res.data.get("auth_mode", "location")
            channel_lat = channel_res.data.get("location_lat")
            channel_lng = channel_res.data.get("location_lng")
            channel_wifi_ssid = channel_res.data.get("wifi_ssid")
    except Exception as e:
        print(f"Failed to load channel settings: {e}")

    # Local State
    state = await attendance_service.get_status(user_id, channel_id)
    
    # UI Refs
    status_text = ft.Text(
        "출근 전" if state["status"] == "OFF" else "근무 중",
        style=ft.TextStyle(size=32, weight="bold", color="white" if state["status"] == "ON" else AppColors.TEXT_PRIMARY)
    )
    
    time_text = ft.Text(
        datetime.now().strftime("%H:%M:%S"),
        style=ft.TextStyle(size=48, weight="bold", font_family="monospace", color="white" if state["status"] == "ON" else AppColors.TEXT_PRIMARY)
    )
    
    date_text = ft.Text(
        datetime.now().strftime("%Y년 %m월 %d일"),
        style=ft.TextStyle(size=14, color="white" if state["status"] == "ON" else AppColors.TEXT_SECONDARY)
    )

    async def update_time():
        while True:
            now = datetime.now()
            time_text.value = now.strftime("%H:%M:%S")
            try:
                time_text.update()
            except:
                break
            await asyncio.sleep(1)
            
    asyncio.create_task(update_time())

    # [BRIDGE] 
    gps_event = asyncio.Event()
    gps_result = {"data": None}

    async def on_gps_bridge_change(e):
        val = e.control.value
        if not val or val == "ATTENDANCE_GPS_BRIDGE_INIT": return
        gps_result["data"] = val
        gps_event.set()

    gps_bridge = ft.TextField(
        value="ATTENDANCE_GPS_BRIDGE_INIT",
        hint_text="ATTENDANCE_GPS_HINT", # Unique selector for JS
        width=1, height=1, opacity=0.01, # Minimal presence to ensure DOM rendering
        on_change=on_gps_bridge_change
    )

    async def toggle_attendance(e):
        print("[DEBUG] toggle_attendance called")
        btn = e.control
        btn.disabled = True
        page.update()
        
        try:
            print(f"[DEBUG] Status: {state['status']}, Auth Mode: {channel_auth_mode}")
            if state["status"] == "OFF":
                # Check auth mode
                if channel_auth_mode == "wifi":
                    print("[DEBUG] WiFi mode - showing error")
                    page.open(ft.SnackBar(ft.Text("❌ Wi-Fi 인증은 모바일 앱에서만 사용 가능합니다."), bgcolor="orange"))
                    return
                
                # GPS Authentication
                if channel_auth_mode == "location":
                    # Validate channel location is set
                    if not channel_lat or not channel_lng:
                        page.open(ft.SnackBar(ft.Text("❌ 매장 위치가 설정되지 않았습니다. 관리자에게 문의하세요."), bgcolor="red"))
                        return
                    
                    # Get user's current location
                    gps_event.clear()
                    gps_result["data"] = None
                    gps_bridge.value = "ATTENDANCE_GPS_BRIDGE_INIT"
                    gps_bridge.update()

                    # JS Bridge Trigger
                    print("[DEBUG] Requesting GPS location...")
                    await page.run_javascript(
                        "(function(){"
                        "  try {"
                        "    const bridge = document.querySelector('input[placeholder=\"ATTENDANCE_GPS_HINT\"]');"
                        "    if (!navigator.geolocation) {"
                        "      if(bridge) { bridge.value = JSON.stringify({error: 'GPS를 지원하지 않는 브라우저입니다'}); bridge.dispatchEvent(new Event('input', {bubbles:true})); }"
                        "      return;"
                        "    }"
                        "    console.log('Requesting geolocation...');"
                        "    navigator.geolocation.getCurrentPosition("
                        "      (pos) => {"
                        "        console.log('GPS success:', pos.coords.latitude, pos.coords.longitude);"
                        "        if(bridge) {"
                        "          bridge.value = JSON.stringify({lat: pos.coords.latitude, lng: pos.coords.longitude});"
                        "          bridge.dispatchEvent(new Event('input', {bubbles:true}));"
                        "        }"
                        "      },"
                        "      (err) => {"
                        "        console.error('GPS error:', err.message);"
                        "        if(bridge) {"
                        "          bridge.value = JSON.stringify({error: err.message});"
                        "          bridge.dispatchEvent(new Event('input', {bubbles:true}));"
                        "        }"
                        "      },"
                        "      { enableHighAccuracy: true, timeout: 30000, maximumAge: 0 }"
                        "    );"
                        "  } catch(e) { console.error('Attendance GPS JS Error:', e); }"
                        "})()"
                    )
                    
                    # Wait for bridge event (increased timeout)
                    try:
                        print("[DEBUG] Waiting for GPS response (35s timeout)...")
                        await asyncio.wait_for(gps_event.wait(), timeout=35.0)
                        print("[DEBUG] GPS response received")
                    except asyncio.TimeoutError:
                        print("[DEBUG] GPS timeout")
                        page.open(ft.SnackBar(ft.Text("⏱️ 위치 정보를 가져오는데 시간이 너무 오래 걸립니다. 브라우저 위치 권한을 확인하거나 모바일에서 테스트해주세요."), bgcolor="orange"))
                        return

                    # Parse GPS result
                    user_lat, user_lng = None, None
                    if gps_result["data"]:
                        try:
                            gps_data = json.loads(gps_result["data"])
                            if "error" in gps_data:
                                page.open(ft.SnackBar(ft.Text(f"❌ GPS 오류: {gps_data['error']}"), bgcolor="red"))
                                return
                            user_lat, user_lng = gps_data["lat"], gps_data["lng"]
                        except Exception as parse_err:
                            page.open(ft.SnackBar(ft.Text(f"❌ 위치 데이터 파싱 오류"), bgcolor="red"))
                            return
                    
                    if not user_lat or not user_lng:
                        page.open(ft.SnackBar(ft.Text("❌ 위치를 가져올 수 없습니다"), bgcolor="red"))
                        return
                    
                    # Calculate distance (Haversine formula)
                    def calculate_distance(lat1, lon1, lat2, lon2):
                        R = 6371000  # Earth radius in meters
                        phi1 = math.radians(lat1)
                        phi2 = math.radians(lat2)
                        delta_phi = math.radians(lat2 - lat1)
                        delta_lambda = math.radians(lon2 - lon1)
                        
                        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
                        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                        
                        return R * c
                    
                    distance = calculate_distance(user_lat, user_lng, channel_lat, channel_lng)
                    
                    # Check distance (100m threshold)
                    if distance > 100:
                        page.open(ft.SnackBar(
                            ft.Text(f"❌ 매장에서 너무 멀리 떨어져 있습니다. (약 {int(distance)}m)"), 
                            bgcolor="red"
                        ))
                        return
                    
                    # Success - proceed with clock in
                    lat, lng = user_lat, user_lng
                
                # 2. Call Service
                success, message = await attendance_service.clock_in(
                    user_id, channel_id, 
                    method="GPS", 
                    lat=lat, lng=lng
                )
            
                if not success:
                    page.open(ft.SnackBar(ft.Text(f"❌ 출근 실패: {message}"), bgcolor="red"))
                    return

                state["status"] = "ON"
                btn.text = "퇴근하기"
                btn.bgcolor = AppColors.ERROR
                status_text.value = "근무 중"
                status_card.gradient = AppGradients.PRIMARY_LINEAR
                status_card.shadow = AppShadows.GLOW
                status_text.color = "white"
                time_text.color = "white"
                date_text.color = ft.Colors.with_opacity(0.8, "white")
                page.open(ft.SnackBar(ft.Text(f"✅ {message}"), bgcolor="green"))
            else:
                # Clock out
                await attendance_service.clock_out(user_id, channel_id)
                state["status"] = "OFF"
                btn.text = "출근하기"
                btn.bgcolor = AppColors.SUCCESS
                status_text.value = "출근 전"
                status_card.gradient = None
                status_card.bgcolor = AppColors.SURFACE_LIGHT if page.theme_mode == ft.ThemeMode.LIGHT else AppColors.SURFACE_DARK
                status_card.shadow = AppShadows.MEDIUM
                status_text.color = AppColors.TEXT_PRIMARY
                time_text.color = AppColors.TEXT_PRIMARY
                date_text.color = AppColors.TEXT_SECONDARY
                page.open(ft.SnackBar(ft.Text("✅ 퇴근 처리되었습니다"), bgcolor="green"))
            
            status_card.update()
            btn.update()
        finally:
            btn.disabled = False
            page.update()

    action_button = ft.ElevatedButton(
        "퇴근하기" if state["status"] == "ON" else "출근하기",
        bgcolor=AppColors.ERROR if state["status"] == "ON" else AppColors.SUCCESS,
        color="white",
        height=65,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=18),
            elevation=8,
            shadow_color=ft.Colors.with_opacity(0.3, "black")
        ),
        on_click=lambda e: page.run_task(toggle_attendance, e)
    )

    status_card = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.AUTO_AWESOME_OUTLINED, color="white" if state["status"] == "ON" else AppColors.PRIMARY, size=20),
                ft.Text("Smart Attendance", size=12, weight="w500", color="white" if state["status"] == "ON" else AppColors.PRIMARY)
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=10),
            status_text,
            time_text,
            date_text,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
        padding=30,
        border_radius=24,
        gradient=AppGradients.PRIMARY_LINEAR if state["status"] == "ON" else None,
        bgcolor=AppColors.SURFACE_LIGHT if page.theme_mode == ft.ThemeMode.LIGHT else AppColors.SURFACE_DARK if state["status"] == "OFF" else None,
        shadow=AppShadows.GLOW if state["status"] == "ON" else AppShadows.MEDIUM,
        animate=ft.Animation(600, ft.AnimationCurve.EASE_OUT)
    )

    header = AppHeader(
        title_text="출퇴근 기록",
        on_back_click=lambda e: page.run_task(navigate_to, "home")
    )

    # Auth mode info
    auth_mode_text = "📍 GPS 위치 인증" if channel_auth_mode == "location" else "📶 Wi-Fi 인증"
    auth_info_text = "매장 위치 100m 이내에서 출근 가능합니다." if channel_auth_mode == "location" else "매장 Wi-Fi에 연결 후 출근 가능합니다. (모바일 앱 전용)"
    
    content = ft.Column([
        header,
        ft.Container(
            padding=20,
            expand=True,
            content=ft.Column([
                status_card,
                ft.Container(height=30),
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.INFO_OUTLINE, size=18, color=AppColors.PRIMARY),
                            ft.Text("출퇴근 인증 방식", weight="bold", size=14, color=AppColors.TEXT_PRIMARY)
                        ], spacing=8),
                        ft.Container(height=5),
                        ft.Text(auth_mode_text, size=16, weight="bold", color=AppColors.PRIMARY),
                        ft.Text(auth_info_text, size=12, color=AppColors.TEXT_SECONDARY),
                    ], spacing=5),
                    padding=15,
                    border_radius=12,
                    bgcolor=ft.Colors.with_opacity(0.05, AppColors.PRIMARY),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.1, AppColors.PRIMARY))
                ),
                ft.Container(height=20),
                ft.Container(
                    content=ft.Column([
                        ft.Row([ft.Icon(ft.Icons.TIPS_AND_UPDATES_OUTLINED, size=16, color=AppColors.TEXT_SECONDARY), ft.Text("안내사항", weight="bold", size=14, color=AppColors.TEXT_SECONDARY)], spacing=5),
                        ft.Text("• 관리자가 설정한 인증 방식으로만 출퇴근이 가능합니다.", size=12, color=AppColors.TEXT_SECONDARY),
                        ft.Text("• GPS 인증 시 위치 권한을 허용해주세요.", size=12, color=AppColors.TEXT_SECONDARY),
                    ], spacing=8),
                    padding=15,
                    border_radius=12,
                    bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.GREY_400)
                ),
                ft.Container(expand=True),
                ft.Container(
                    content=action_button,
                    width=float("inf"),
                    padding=ft.padding.only(bottom=10)
                ),
                gps_bridge # Add bridge here
            ], scroll=ft.ScrollMode.AUTO)
        )
    ], spacing=0, expand=True)

    return [
        ft.SafeArea(expand=True, content=content)
    ]
