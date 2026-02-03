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

    # GPS Bridge - TextField 기반 브릿지 (Safari 호환)
    gps_event = asyncio.Event()
    gps_result_data = {"value": None}

    def on_gps_bridge_change(e):
        val = e.control.value
        if val and val != "ATTENDANCE_GPS_BRIDGE_INIT":
            print(f"[GPS_BRIDGE] Received: {val[:100]}...")
            gps_result_data["value"] = val
            gps_event.set()

    gps_bridge = ft.TextField(
        value="ATTENDANCE_GPS_BRIDGE_INIT",
        hint_text="ATTENDANCE_GPS_BRIDGE",
        width=1,
        height=1,
        opacity=0,
        on_change=on_gps_bridge_change
    )

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

    # Attendance Log UI
    log_column = ft.Column(spacing=10)
    
    async def update_logs():
        log_column.controls.clear()
        try:
            logs = await attendance_service.get_recent_logs(user_id, channel_id, limit=7)
            if not logs:
                log_column.controls.append(
                    ft.Container(
                        content=ft.Text("최근 기록이 없습니다.", size=13, color=AppColors.TEXT_SECONDARY),
                        padding=20, alignment=ft.alignment.center
                    )
                )
            else:
                for log in logs:
                    # Parse UTC to local format
                    try:
                        dt = datetime.fromisoformat(log["created_at"].replace("Z", "+00:00"))
                        log_time = dt.strftime("%m/%d %H:%M")
                    except:
                        log_time = log["created_at"][:16]
                        
                    log_type = "출근" if log["type"] == "IN" else "퇴근"
                    log_color = AppColors.SUCCESS if log["type"] == "IN" else AppColors.ERROR
                    method = log.get("method", "---")
                    
                    log_column.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Container(
                                    content=ft.Text(log_type, size=12, weight="bold", color="white"),
                                    bgcolor=log_color,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                    border_radius=6
                                ),
                                ft.Text(log_time, size=13, color=AppColors.TEXT_PRIMARY, weight="w500"),
                                ft.VerticalDivider(width=1, color=ft.Colors.with_opacity(0.1, AppColors.TEXT_SECONDARY)),
                                ft.Text(method, size=11, color=AppColors.TEXT_SECONDARY),
                                ft.Container(expand=True),
                                ft.Icon(ft.Icons.CHEVRON_RIGHT, size=14, color=ft.Colors.with_opacity(0.2, AppColors.TEXT_SECONDARY))
                            ], alignment=ft.MainAxisAlignment.START, spacing=12),
                            padding=ft.padding.all(12),
                            border_radius=12,
                            bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.GREY_400),
                        )
                    )
            log_column.update()
        except Exception as log_err:
            print(f"Log Update Error: {log_err}")

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
    asyncio.create_task(update_logs())

    # [Bridge Removal] Removed gps_bridge TextField as we now use Title-Bridge via run_javascript(return_value=True)

    async def toggle_attendance(e):
        print("[DEBUG] toggle_attendance called")
        btn = e.control
        btn.disabled = True
        page.update()
        
        try:
            # Check for missing session data
            if not user_id or not channel_id:
                print(f"[DEBUG] Session missing: user={user_id}, channel={channel_id}")
                page.open(ft.SnackBar(ft.Text("❌ 세션 정보가 없습니다. 다시 로그인해주세요."), bgcolor="red"))
                return

            print(f"[DEBUG] Status: {state['status']}, Auth Mode: {channel_auth_mode}")
            if state["status"] == "OFF":
                # Check auth mode
                if channel_auth_mode == "wifi":
                    page.open(ft.SnackBar(ft.Text("❌ Wi-Fi 인증은 모바일 앱에서만 사용 가능합니다."), bgcolor="orange"))
                    return
                
                # GPS Authentication
                if channel_auth_mode == "location":
                    if not channel_lat or not channel_lng:
                        page.open(ft.SnackBar(ft.Text("❌ 매장 위치가 설정되지 않았습니다."), bgcolor="red"))
                        return
                    
                    print("[DEBUG] Triggering GPS request via TextField bridge...")
                    page.open(ft.SnackBar(
                        ft.Text("📍 위치 정보를 요청합니다. 허용 창이 뜨면 '허용'을 눌러주세요."),
                        duration=5000
                    ))

                    user_lat = None
                    user_lng = None

                    try:
                        # Reset bridge state
                        gps_event.clear()
                        gps_result_data["value"] = None
                        gps_bridge.value = "ATTENDANCE_GPS_BRIDGE_INIT"
                        gps_bridge.update()

                        # TextField 브릿지 방식 - Safari 호환
                        # JavaScript가 DOM에서 TextField를 찾아 값을 설정하면 on_change가 트리거됨
                        gps_script = (
                            "(function(){"
                            "  try {"
                            "    const bridge = document.querySelector('input[placeholder=\"ATTENDANCE_GPS_BRIDGE\"]');"
                            "    if (!bridge) { console.error('GPS Bridge not found'); return; }"
                            "    if (!navigator.geolocation) {"
                            "      bridge.value = JSON.stringify({error: 'GPS_NOT_SUPPORTED'});"
                            "      bridge.dispatchEvent(new Event('input', {bubbles:true}));"
                            "      return;"
                            "    }"
                            "    navigator.geolocation.getCurrentPosition("
                            "      (pos) => {"
                            "        bridge.value = JSON.stringify({lat: pos.coords.latitude, lng: pos.coords.longitude, acc: pos.coords.accuracy});"
                            "        bridge.dispatchEvent(new Event('input', {bubbles:true}));"
                            "      },"
                            "      (err) => {"
                            "        bridge.value = JSON.stringify({error: err.message || 'PERMISSION_DENIED', code: err.code});"
                            "        bridge.dispatchEvent(new Event('input', {bubbles:true}));"
                            "      },"
                            "      { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 }"
                            "    );"
                            "  } catch(e) { console.error('GPS JS Error:', e); }"
                            "})()"
                        )

                        # Execute JavaScript (no return value needed - result comes via TextField)
                        await page.run_javascript(gps_script)
                        print("[DEBUG] GPS script executed, waiting for bridge response...")

                        # Wait for TextField bridge response
                        try:
                            await asyncio.wait_for(gps_event.wait(), timeout=25.0)
                            print("[DEBUG] Bridge responded!")
                        except asyncio.TimeoutError:
                            print("[DEBUG] Bridge timeout!")
                            page.open(ft.SnackBar(
                                ft.Text("⏱️ GPS 응답 시간 초과. 위치 권한을 확인하고 다시 시도해주세요."),
                                bgcolor="orange"
                            ))
                            return

                        # Parse result
                        res_str = gps_result_data["value"]
                        if not res_str:
                            page.open(ft.SnackBar(
                                ft.Text("❌ GPS 데이터를 받지 못했습니다."),
                                bgcolor="red"
                            ))
                            return

                        gps_data = json.loads(res_str)
                        print(f"[DEBUG] GPS data: {gps_data}")

                        if "error" in gps_data:
                            error_msg = gps_data['error']
                            error_code = gps_data.get('code', '')

                            # 에러 코드별 안내 메시지
                            if error_code == 1 or 'denied' in error_msg.lower() or 'permission' in error_msg.lower():
                                page.open(ft.SnackBar(
                                    ft.Text("❌ 위치 권한이 거부되었습니다. 설정에서 위치 접근을 허용해주세요."),
                                    bgcolor="red"
                                ))
                            elif error_code == 2:
                                page.open(ft.SnackBar(
                                    ft.Text("❌ 위치를 확인할 수 없습니다. GPS 신호가 약합니다."),
                                    bgcolor="red"
                                ))
                            elif error_code == 3:
                                page.open(ft.SnackBar(
                                    ft.Text("❌ 위치 확인 시간 초과. 다시 시도해주세요."),
                                    bgcolor="orange"
                                ))
                            else:
                                page.open(ft.SnackBar(ft.Text(f"❌ GPS 오류: {error_msg}"), bgcolor="red"))
                            return

                        user_lat = gps_data.get("lat")
                        user_lng = gps_data.get("lng")
                        print(f"[DEBUG] Got GPS: lat={user_lat}, lng={user_lng}")

                    except json.JSONDecodeError as je:
                        print(f"[DEBUG] JSON parse error: {je}")
                        page.open(ft.SnackBar(ft.Text("❌ GPS 데이터 형식 오류"), bgcolor="red"))
                        return
                    except Exception as bridge_err:
                        import traceback
                        print(f"[DEBUG] GPS Error: {bridge_err}")
                        traceback.print_exc()
                        page.open(ft.SnackBar(ft.Text(f"❌ GPS 통신 오류: {bridge_err}"), bgcolor="red"))
                        return
                    
                    if not user_lat or not user_lng:
                        page.open(ft.SnackBar(ft.Text("❌ 위치를 가져올 수 없습니다"), bgcolor="red"))
                        return
                    
                    # Calculate distance
                    def calculate_distance(lat1, lon1, lat2, lon2):
                        R = 6371000
                        phi1, phi2 = math.radians(lat1), math.radians(lat2)
                        d_phi, d_lam = math.radians(lat2-lat1), math.radians(lon2-lon1)
                        a = math.sin(d_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(d_lam/2)**2
                        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                    
                    distance = calculate_distance(user_lat, user_lng, channel_lat, channel_lng)
                    if distance > 150:
                        page.open(ft.SnackBar(ft.Text(f"❌ 매장에서 너무 멉니다 (약 {int(distance)}m)"), bgcolor="red"))
                        return
                    
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
            
            # Refresh logs
            await update_logs()
            status_card.update()
            btn.update()
        except Exception as ex:
            import traceback
            print(f"[FATAL] toggle_attendance error: {ex}")
            traceback.print_exc()
            page.open(ft.SnackBar(ft.Text(f"🚨 시스템 오류: {ex}"), bgcolor="red"))
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
                # GPS Bridge (hidden TextField for Safari-compatible GPS communication)
                gps_bridge,
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
                ft.Container(height=30),
                # Recent Logs Section
                ft.Row([
                    ft.Text("최근 7회 기록", size=16, weight="bold", color=AppColors.TEXT_PRIMARY),
                    ft.Container(expand=True),
                    ft.TextButton("새로고침", icon=ft.Icons.REFRESH, on_click=lambda _: page.run_task(update_logs))
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=10),
                log_column,
                ft.Container(height=30),
                ft.Container(
                    content=action_button,
                    width=float("inf"),
                    padding=ft.padding.only(bottom=10)
                ),
            ], scroll=ft.ScrollMode.HIDDEN)
        )
    ], spacing=0, expand=True)

    return [
        ft.SafeArea(expand=True, content=content)
    ]
