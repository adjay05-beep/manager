import flet as ft
import asyncio
from services.channel_service import channel_service
from services.auth_service import auth_service
from db import service_supabase
from postgrest import SyncPostgrestClient
import os
from datetime import datetime, timezone
from utils.logger import log_debug, log_error, log_info
from views.styles import AppColors, AppTextStyles, AppLayout, AppButtons
from views.components.app_header import AppHeader
import requests
from dotenv import load_dotenv

load_dotenv()


async def get_store_manage_controls(page: ft.Page, navigate_to):
    """Unified Settings Page: Store Info + My Profile + Logout"""
    log_debug(f"Entering Store Manage. User: {page.app_session.get('user_id')}")

    # === 1. GET CONTEXT ===
    user_id = page.app_session.get("user_id")
    channel_id = page.app_session.get("channel_id")
    user_email = page.app_session.get("user_email") or "unknown@example.com"

    if not channel_id:
        return [ft.Text("매장 정보가 없습니다.")]

    # === 2. FETCH STORE DATA ===
    try:
        token = auth_service.get_access_token()
        channels = channel_service.get_user_channels(user_id, token)
        current_ch = next((c for c in channels if c["id"] == channel_id), None)
    except Exception as e:
        log_error(f"Failed to fetch channels: {e}")
        return [ft.Text("매장 정보를 불러올 수 없습니다.")]

    if not current_ch:
        return [ft.Text("매장 정보를 불러올 수 없습니다.")]

    # [FIX] Use fresh role from DB, not stale session
    role = current_ch.get("role", "staff")

    # === 3. FETCH USER PROFILE DATA ===
    user_profile = None
    try:
        res = service_supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        user_profile = res.data
    except Exception as e:
        log_error(f"Failed to fetch user profile: {e}")

    # === UI STATE ===
    msg = ft.Text("", size=12)

    # Invite Code Section
    try:
        active_codes = channel_service.get_active_invite_codes(channel_id)
    except Exception:
        active_codes = []

    code_display = ft.Text("", selectable=True, color="#00BCD4", size=16, weight="bold")
    code_expiry = ft.Text("", size=12, color="grey")

    def update_code_display():
        try:
            if active_codes and len(active_codes) > 0:
                latest = active_codes[0]
                code_display.value = latest["code"]

                expires = datetime.fromisoformat(latest["expires_at"].replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                remaining = expires - now
                minutes = int(remaining.total_seconds() / 60)

                if minutes > 0:
                    code_expiry.value = f"⏱ {minutes}분 후 만료 | 사용 횟수: {latest.get('used_count', 0)}회"
                else:
                    code_expiry.value = "⚠ 만료됨"
                    code_display.value = "만료된 코드"
            else:
                code_display.value = "생성된 코드가 없습니다"
                code_expiry.value = "새 코드를 생성하세요"
        except Exception as e:
            log_error(f"Update code display error: {e}")
            code_display.value = "코드 로드 실패"
            code_expiry.value = ""

    update_code_display()

    # === EVENT HANDLERS ===

    async def copy_code(e):
        if active_codes and code_display.value not in ["생성된 코드가 없습니다", "만료된 코드", "코드 로드 실패"]:
            page.set_clipboard(code_display.value)
            page.open(ft.SnackBar(ft.Text(f"초대 코드 복사 완료: {code_display.value}")))
            page.update()

    async def generate_new_code(e):
        log_debug(f"Generating new code for channel {channel_id} by {user_id}")
        try:
            new_code = await asyncio.to_thread(channel_service.generate_invite_code, channel_id, user_id, 10)
            log_debug(f"New code generated: {new_code}")
            active_codes.clear()
            new_codes = await asyncio.to_thread(channel_service.get_active_invite_codes, channel_id)
            active_codes.extend(new_codes)
            update_code_display()

            msg.value = f"새 초대 코드 생성됨: {new_code}"
            msg.color = "green"
            page.update()
        except PermissionError as pe:
            msg.value = str(pe)
            msg.color = "red"
            page.update()
        except Exception as ex:
            log_error(f"Generate Code Error: {ex}")
            msg.value = f"코드 생성 실패: {ex}"
            msg.color = "red"
            page.update()

    generate_btn = ft.ElevatedButton(
        "새 초대 코드 생성 (10분)",
        icon=ft.Icons.REFRESH,
        visible=(role in ["owner", "manager"]),
        style=AppButtons.PRIMARY(),
        height=40,
        on_click=lambda e: asyncio.create_task(generate_new_code(e))
    )

    # === MEMBER MANAGEMENT (Owner Only) ===
    member_mgmt_col = ft.Column(spacing=10)
    current_members_data = []  # Store for transfer dialog

    async def perform_transfer_and_logout(new_owner_id: str, target_name: str, dlg_confirm, dlg_transfer):
        """양도 실행 및 로그아웃 처리 - 안정적인 순차 실행"""
        try:
            # 1. 양도 실행
            log_info(f"[Transfer] Starting ownership transfer to {new_owner_id}")
            token = auth_service.get_access_token()
            channel_service.transfer_channel_ownership(channel_id, new_owner_id, token=token)
            log_info("[Transfer] Ownership transferred successfully")

            # 2. 다이얼로그 닫기 (먼저)
            try:
                await page.close_async(dlg_confirm) if hasattr(page, "close_async") else page.close(dlg_confirm)
                await page.close_async(dlg_transfer) if hasattr(page, "close_async") else page.close(dlg_transfer)
            except Exception:
                pass

            # 3. 성공 메시지 표시
            page.open(ft.SnackBar(
                ft.Text(f"매장 대표가 '{target_name}'님으로 변경되었습니다."),
                bgcolor="green"
            ))
            page.update()

            # 4. 세션 및 스토리지 정리
            log_info("[Transfer] Starting session cleanup")
            try:
                auth_service.sign_out()
                log_info("[Transfer] sign_out completed")
            except Exception as logout_err:
                log_error(f"[Transfer] Logout error (non-critical): {logout_err}")

            try:
                # Clear app_session dict
                page.app_session.clear()
                log_info("[Transfer] session cleared")
            except Exception as session_err:
                log_error(f"[Transfer] Session clear error: {session_err}")

            try:
                page.shared_preferences.remove("supa_session")
                log_info("[Transfer] shared_preferences cleared")
            except Exception as storage_err:
                log_error(f"[Transfer] Storage clear error: {storage_err}")

            # 5. 로그인 페이지로 이동
            log_info("[Transfer] Navigating to login...")
            await navigate_to("login")
            log_info("[Transfer] navigate_to('login') completed")

        except Exception as ex:
            log_error(f"[Transfer] Transfer failed: {ex}")
            try:
                page.close(dlg_confirm)
            except Exception:
                pass
            page.open(ft.SnackBar(ft.Text(f"양도 실패: {ex}"), bgcolor="red"))
            page.update()

    async def open_transfer_dialog(e):
        candidates = [m for m in current_members_data if m["user_id"] != user_id]
        if not candidates:
            page.open(ft.SnackBar(ft.Text("양도할 멤버가 없습니다.")))
            page.update()
            return

        selected_candidate = [None]  # Mutable container

        def set_candidate(ev):
            selected_candidate[0] = ev.control.value

        async def do_transfer_check(ev):
            if not selected_candidate[0]:
                page.open(ft.SnackBar(ft.Text("새 대표를 선택해주세요.")))
                page.update()
                return

            # Find name for confirmation message
            target_name = "Unknown"
            for m in candidates:
                if m["user_id"] == selected_candidate[0]:
                    target_name = m.get("full_name", "Unknown")
                    break

            # [SECURITY] Password Verification Dialog
            confirm_btn = ft.ElevatedButton(
                "확인 (양도)",
                bgcolor="red",
                color="white",
                disabled=True
            )

            password_tf = ft.TextField(
                label="비밀번호 확인",
                password=True,
                can_reveal_password=True,
                hint_text="본인 확인을 위해 비밀번호를 입력하세요.",
                text_align=ft.TextAlign.CENTER
            )

            async def on_password_change(pw_ev):
                password_tf.error_text = None
                password_tf.update()
                confirm_btn.disabled = not bool(password_tf.value)
                confirm_btn.update()

            password_tf.on_change = on_password_change

            async def final_transfer_confirm(confirm_ev):
                log_info("[Transfer] final_transfer_confirm called")
                if not password_tf.value:
                    log_info("[Transfer] No password entered")
                    return

                # Disable button to prevent double-click
                confirm_btn.disabled = True
                confirm_btn.text = "처리 중..."
                confirm_btn.update()

                # [SECURITY] Verify Password
                try:
                    current_email = auth_service.get_user().email
                    log_info(f"[Transfer] Verifying password for {current_email}")
                    if not current_email:
                        raise Exception("사용자 이메일 정보를 찾을 수 없습니다.")

                    # Attempt Re-login to verify password
                    auth_service.sign_in(current_email, password_tf.value)
                    log_info("[Transfer] Password verified successfully")
                except Exception as pwd_err:
                    log_error(f"[Transfer] Password verification failed: {pwd_err}")
                    password_tf.error_text = "잘못된 비밀번호입니다."
                    password_tf.update()
                    confirm_btn.disabled = False
                    confirm_btn.text = "확인 (양도)"
                    confirm_btn.update()
                    return

                # Execute transfer
                await perform_transfer_and_logout(
                    selected_candidate[0],
                    target_name,
                    dlg_confirm,
                    dlg_transfer
                )

            confirm_btn.on_click = lambda e: asyncio.create_task(final_transfer_confirm(e))

            dlg_confirm = ft.AlertDialog(
                title=ft.Text("양도 확인 (최종)", text_align=ft.TextAlign.CENTER),
                content=ft.Column([
                    ft.Text(f"정말 '{target_name}'님에게 매장 대표 권한을 양도하시겠습니까?", weight="bold"),
                    ft.Text(
                        "양도 후 귀하는 '관리자' 등급으로 변경되며,\n이 작업은 되돌릴 수 없습니다.",
                        color="red",
                        size=12,
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Container(height=5),
                    password_tf
                ], height=180, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                actions=[
                    ft.TextButton("취소", on_click=lambda _: asyncio.create_task(page.close_async(dlg_confirm) if hasattr(page, "close_async") else page.close(dlg_confirm))),
                    confirm_btn
                ],
                actions_alignment=ft.MainAxisAlignment.CENTER
            )

            page.open(dlg_confirm)
            page.update()

        dlg_transfer = ft.AlertDialog(
            title=ft.Text("매장 대표 권한 양도"),
            content=ft.Column([
                ft.Text("권한을 받을 새 대표를 선택하세요."),
                ft.Dropdown(
                    label="새 대표 선택",
                    width=280,
                    options=[
                        ft.dropdown.Option(m["user_id"], m.get("full_name") or "Unknown")
                        for m in candidates
                    ],
                    on_change=set_candidate
                ),
                ft.Text("주의: 양도 후 귀하는 '관리자' 등급으로 변경됩니다.", color="red", size=12)
            ], height=150),
            actions=[
                ft.TextButton("취소", on_click=lambda _: asyncio.create_task(page.close_async(dlg_transfer) if hasattr(page, "close_async") else page.close(dlg_transfer))),
                ft.ElevatedButton("양도 확인", bgcolor="red", color="white", on_click=lambda e: asyncio.create_task(do_transfer_check(e)))
            ]
        )
        page.open(dlg_transfer)
        page.update()

    async def load_members():
        if role != "owner":
            return
        try:
            token = auth_service.get_access_token()
            members = channel_service.get_channel_members_with_profiles(channel_id, access_token=token)

            # Sort by rank precedence: owner(0) > manager(1) > staff(2)
            precedence = {"owner": 0, "manager": 1, "staff": 2}
            members.sort(key=lambda x: precedence.get(x.get("role"), 9))

            current_members_data.clear()
            member_items = []
            other_members_count = 0

            for m in members:
                uid = m["user_id"]
                u_role = m["role"]
                is_me = (uid == user_id)
                current_members_data.append(m)

                if not is_me:
                    other_members_count += 1

                # Role Display Mapping
                if u_role == "owner":
                    role_label = "대표"
                elif u_role == "manager":
                    role_label = "관리자"
                else:
                    role_label = "멤버"
                    if u_role not in ["manager", "staff"]:
                        u_role = "staff"

                # UI for Role Selection
                if u_role == "owner":
                    role_selector = ft.Container(
                        content=ft.Text("대표", weight="bold", size=14, color="#2196F3"),
                        width=100,
                        alignment=ft.Alignment(0, 0)
                    )
                else:
                    role_selector = ft.Dropdown(
                        value=u_role,
                        options=[
                            ft.dropdown.Option("manager", "관리자"),
                            ft.dropdown.Option("staff", "멤버")
                        ],
                        width=110,
                        content_padding=ft.padding.symmetric(horizontal=10, vertical=0),
                        text_size=13,
                        text_style=ft.TextStyle(weight=ft.FontWeight.BOLD),
                        border_radius=8,
                        on_change=lambda ev, uid=uid: asyncio.create_task(update_member_role(uid, ev.control.value)),
                        disabled=is_me
                    )

                kick_btn = ft.IconButton(
                    ft.Icons.REMOVE_CIRCLE_OUTLINE,
                    icon_color="red",
                    tooltip="내보내기",
                    on_click=lambda ev, uid=uid, name=m.get("full_name", "Unknown"): asyncio.create_task(confirm_kick(uid, name)),
                    visible=(not is_me and u_role != "owner")
                )

                member_items.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Row([
                                    ft.Text(m.get("full_name", "Unknown"), weight="bold", size=14),
                                    ft.Container(
                                        content=ft.Text(role_label, size=10, color="white", weight="bold"),
                                        bgcolor="#2196F3" if u_role == "owner" else "#4CAF50" if u_role == "manager" else "#9E9E9E",
                                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                        border_radius=4
                                    )
                                ], spacing=5),
                                ft.Text(
                                    f"@{m.get('username')}" if m.get("username") else f"User #{uid[-4:]}",
                                    size=10,
                                    color="grey"
                                )
                            ], expand=True, spacing=2),
                            role_selector,
                            kick_btn
                        ], alignment="spaceBetween"),
                        padding=10,
                        border=ft.border.only(bottom=ft.border.BorderSide(1, "#EEEEEE")),
                        bgcolor="white"
                    )
                )

            # Ownership Transfer Section (only if there are other members)
            transfer_section = ft.Container(
                content=ft.Column([
                    ft.Text("매장 양도 (소유권 이전)", weight="bold", size=16),
                    ft.Text("대표 권한을 다른 멤버에게 넘깁니다. 이 작업은 되돌릴 수 없습니다.", size=12, color="grey"),
                    ft.ElevatedButton(
                        "양도할 멤버 선택 및 넘기기",
                        icon=ft.Icons.PERSON_SEARCH,
                        bgcolor="#FF5252",
                        color="white",
                        on_click=lambda e: asyncio.create_task(open_transfer_dialog(e))
                    )
                ]),
                padding=20,
                border=ft.border.all(1, "#FFEBEE"),
                border_radius=10,
                bgcolor="#FFEBEE",
                visible=(other_members_count > 0)
            )

            # Build final controls
            if other_members_count == 0:
                member_mgmt_col.controls = [
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=40, color="grey"),
                            ft.Text("아직 매장에 합류한 멤버가 없습니다.", size=14, weight="bold", color="grey"),
                            ft.Text("초대 코드를 공유하여 동료를 초대해보세요!", size=12, color="grey")
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                        padding=30,
                        alignment=ft.Alignment(0, 0),
                        bgcolor="#F5F5F5",
                        border_radius=10
                    )
                ]
            else:
                member_items.append(ft.Container(height=30))
                member_items.append(ft.Divider())
                member_items.append(transfer_section)
                member_mgmt_col.controls = member_items

            page.update()
        except Exception as ex:
            log_error(f"Load Members Error: {ex}")

    async def update_member_role(uid, new_role):
        try:
            token = auth_service.get_access_token()
            channel_service.update_member_role(channel_id, uid, new_role, user_id, token=token)
            page.open(ft.SnackBar(ft.Text("권한이 수정되었습니다."), bgcolor="green"))
            page.update()
        except PermissionError as perm_err:
            page.open(ft.SnackBar(ft.Text(str(perm_err)), bgcolor="red"))
            page.update()
        except Exception as ex:
            page.open(ft.SnackBar(ft.Text(f"오류: {ex}"), bgcolor="red"))
            page.update()

    async def confirm_kick(uid, name):
        async def do_kick(ev):
            try:
                token = auth_service.get_access_token()
                channel_service.remove_member(channel_id, uid, user_id, token=token)
                await page.close_async(dlg) if hasattr(page, "close_async") else page.close(dlg)
                await load_members()
                page.open(ft.SnackBar(ft.Text(f"{name}님을 내보냈습니다."), bgcolor="green"))
                page.update()
            except PermissionError as perm_err:
                page.open(ft.SnackBar(ft.Text(str(perm_err)), bgcolor="red"))
                page.update()
            except Exception as ex:
                page.open(ft.SnackBar(ft.Text(f"내보내기 실패: {ex}"), bgcolor="red"))
                page.update()
                log_error(f"Kick Error: {ex}")

        dlg = ft.AlertDialog(
            title=ft.Text("멤버 내보내기"),
            content=ft.Text(f"정말 {name}님을 매장에서 내보내시겠습니까?"),
            actions=[
                ft.TextButton("취소", on_click=lambda _: page.close(dlg)),
                ft.ElevatedButton("내보내기", bgcolor="red", color="white", on_click=lambda e: asyncio.create_task(do_kick(e)))
            ]
        )
        page.open(dlg)
        page.update()

    async def confirm_leave_store(e):
        """매장 탈퇴 확인 다이얼로그"""
        async def do_leave(ev):
            try:
                token = auth_service.get_access_token()
                channel_service.remove_member(channel_id, user_id, user_id, token=token)

                # Cleanup session specific to this channel
                page.app_session["channel_id"] = None
                page.app_session["channel_name"] = None
                page.app_session["user_role"] = None

                await page.close_async(dlg_leave) if hasattr(page, "close_async") else page.close(dlg_leave)
                page.open(ft.SnackBar(ft.Text("매장을 탈퇴했습니다."), bgcolor="green"))
                page.update()
                await navigate_to("home")
            except PermissionError as pe:
                page.open(ft.SnackBar(ft.Text(str(pe)), bgcolor="red"))
                page.update()
                await page.close_async(dlg_leave) if hasattr(page, "close_async") else page.close(dlg_leave)
            except Exception as ex:
                log_error(f"Leave Store Error: {ex}")
                page.open(ft.SnackBar(ft.Text(f"탈퇴 실패: {ex}"), bgcolor="red"))
                page.update()

        dlg_leave = ft.AlertDialog(
            title=ft.Text("매장 탈퇴"),
            content=ft.Text("정말 이 매장에서 나가시겠습니까?\n이 작업은 되돌릴 수 없습니다."),
            actions=[
                ft.TextButton("취소", on_click=lambda _: asyncio.create_task(page.close_async(dlg_leave) if hasattr(page, "close_async") else page.close(dlg_leave))),
                ft.ElevatedButton("탈퇴하기", bgcolor="red", color="white", on_click=lambda e: asyncio.create_task(do_leave(e)))
            ]
        )
        page.open(dlg_leave)
        page.update()

    async def toggle_theme(e):
        # Toggle theme mode
        page.theme_mode = ft.ThemeMode.LIGHT if page.theme_mode == ft.ThemeMode.DARK else ft.ThemeMode.DARK
        # Save preference to shared_preferences (Flet 0.80+)
        try:
            await page.shared_preferences.set("theme_mode", "dark" if page.theme_mode == ft.ThemeMode.DARK else "light")  # Flet 0.80+ uses set()
        except Exception as ex:
            log_error(f"Failed to save theme preference: {ex}")
        page.update()

    theme_switch = ft.Switch(
        label="다크 모드",
        value=(page.theme_mode == ft.ThemeMode.DARK),
        active_color=AppColors.PRIMARY,
        on_change=lambda e: asyncio.create_task(toggle_theme(e))
    )

    # === ATTENDANCE AUTHENTICATION SETTINGS (Owner/Manager only) ===
    
    # Get saved attendance auth data
    saved_lat, saved_lng, saved_address, saved_wifi, saved_auth_mode = None, None, "", "", "location"
    try:
        loc_res = service_supabase.table("channels").select("location_lat, location_lng, location_address, wifi_ssid, auth_mode").eq("id", channel_id).single().execute()
        if loc_res.data:
            saved_lat = loc_res.data.get("location_lat")
            saved_lng = loc_res.data.get("location_lng")
            saved_address = loc_res.data.get("location_address", "")
            saved_wifi = loc_res.data.get("wifi_ssid", "")
            saved_auth_mode = loc_res.data.get("auth_mode", "location")  # default: location
    except Exception as e:
        log_error(f"Failed to load attendance auth data: {e}")
    
    # Auth mode state
    auth_mode = ft.RadioGroup(
        value=saved_auth_mode,
        content=ft.Row([
            ft.Radio(value="location", label="📍 위치(GPS) 인증"),
            ft.Radio(value="wifi", label="📶 Wi-Fi 인증")
        ])
    )
    
    # UI Controls
    gps_display = ft.Text(
        f"저장된 위치: {saved_lat:.5f}, {saved_lng:.5f}" if saved_lat and saved_lng else "위치 설정 필요",
        color="grey",
        size=12
    )
    
    tf_address = ft.TextField(
        label="매장 주소",
        value=saved_address,
        hint_text="예: 서울시 강남구 테헤란로 123",
        expand=True
    )
    
    tf_wifi = ft.TextField(
        label="매장 Wi-Fi SSID",
        value=saved_wifi,
        hint_text="예: Store_WiFi_5G",
        expand=True
    )
    
    # Map image (Kakao Static Map API)
    def get_map_url(lat, lng, width=300, height=200):
        """Generate Kakao Static Map URL
        Note: Kakao uses lng,lat order (not lat,lng)
        """
        api_key = os.getenv("KAKAO_REST_API_KEY")
        # Kakao Static Map API: https://apis.map.kakao.com/web/documentation/#StaticMap
        return f"https://dapi.kakao.com/v2/maps/staticmap?center={lng},{lat}&level=3&marker={lng},{lat}&size={width}x{height}&appkey={api_key}"
    
    # Map placeholder (web version - show coordinates)
    # Note: Mobile app will use native map widget
    map_container = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.LOCATION_ON, size=40, color=AppColors.PRIMARY),
            ft.Text("위치 설정 필요", size=12, color="grey", text_align=ft.TextAlign.CENTER)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
        width=300,
        height=150,
        bgcolor="#F5F5F5",
        border_radius=10,
        border=ft.border.all(1, "#DDDDDD"),
        alignment=ft.alignment.center,
        padding=20
    )
    
    # Kakao Map link (opens in browser)
    map_link_btn = ft.TextButton(
        "🗺️ 카카오맵에서 보기",
        visible=False,
        on_click=lambda e: page.launch_url(f"https://map.kakao.com/link/map/{gps_display.data[0]},{gps_display.data[1]}") if hasattr(gps_display, "data") and gps_display.data else None
    )
    
    # === KAKAO ADDRESS SEARCH ===
    async def search_address_and_get_coords(e):
        """Search address using Kakao Local API and get coordinates"""
        log_debug("search_address_and_get_coords CALLED")
        try:
            address_query = tf_address.value.strip()
            if not address_query:
                page.open(ft.SnackBar(ft.Text("주소를 입력해주세요"), bgcolor="orange"))
                page.update()
                return
            
            e.control.disabled = True
            e.control.text = "주소 검색 중..."
            page.update()
            
            # Call Kakao Local API
            api_key = os.getenv("KAKAO_REST_API_KEY")
            url = "https://dapi.kakao.com/v2/local/search/address.json"
            headers = {"Authorization": f"KakaoAK {api_key}"}
            params = {"query": address_query}
            
            log_debug(f"Kakao API request: {url}?query={address_query}")
            response = await asyncio.to_thread(requests.get, url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                log_debug(f"Kakao API response: {data}")
                
                if data.get("documents") and len(data["documents"]) > 0:
                    doc = data["documents"][0]
                    address_info = doc.get("address") or doc.get("road_address")
                    
                    if address_info:
                        lat = float(address_info["y"])
                        lng = float(address_info["x"])
                        address_name = address_info.get("address_name", address_query)
                        
                        # Update UI
                        gps_display.value = f"위치: {lat:.5f}, {lng:.5f}"
                        gps_display.color = AppColors.PRIMARY
                        gps_display.data = (lat, lng)
                        tf_address.value = address_name
                        
                        # Update map container
                        map_container.content = ft.Column([
                            ft.Icon(ft.Icons.LOCATION_ON, size=50, color=AppColors.PRIMARY),
                            ft.Text(f"위도: {lat:.5f}", size=12, weight="bold"),
                            ft.Text(f"경도: {lng:.5f}", size=12, weight="bold"),
                            ft.Text("✓ 위치 설정 완료", size=11, color="green")
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
                        
                        # Show map link button
                        map_link_btn.visible = True
                        
                        page.open(ft.SnackBar(ft.Text("✅ 위치를 찾았습니다!"), bgcolor="green"))
                        log_debug(f"Address found: {address_name} ({lat}, {lng})")
                    else:
                        page.open(ft.SnackBar(ft.Text("❌ 좌표를 찾을 수 없습니다"), bgcolor="red"))
                else:
                    page.open(ft.SnackBar(ft.Text("❌ 주소를 찾을 수 없습니다. 정확한 주소를 입력해주세요."), bgcolor="orange"))
            else:
                log_error(f"Kakao API error: {response.status_code} - {response.text}")
                page.open(ft.SnackBar(ft.Text(f"API 오류: {response.status_code}"), bgcolor="red"))
                
        except Exception as ex:
            log_error(f"Address search error: {ex}")
            import traceback
            log_error(traceback.format_exc())
            page.open(ft.SnackBar(ft.Text(f"오류: {ex}"), bgcolor="red"))
        finally:
            e.control.disabled = False
            e.control.text = "🔍 주소로 위치 찾기"
            page.update()
    
    btn_search_address = ft.ElevatedButton(
        "🔍 주소로 위치 찾기",
        on_click=search_address_and_get_coords,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        expand=True
    )
    
    # Location auth container (conditional)
    location_auth_container = ft.Container(
        content=ft.Column([
            map_container,
            gps_display,
            map_link_btn,
            ft.Row([tf_address]),
            ft.Row([btn_search_address]),
            ft.Text("※ 매장 주소를 입력하고 검색하면 위치가 자동으로 설정됩니다.", size=11, color="grey"),
        ], spacing=10),
        visible=(saved_auth_mode == "location")
    )
    
    # WiFi auth container (conditional)
    wifi_auth_container = ft.Container(
        content=ft.Column([
            ft.Row([tf_wifi]),
            ft.Text("※ 매장 Wi-Fi 이름을 정확히 입력하세요.", size=11, color="grey"),
        ], spacing=10),
        visible=(saved_auth_mode == "wifi")
    )
    
    # Radio button change handler
    def on_auth_mode_change(e):
        selected_mode = auth_mode.value
        location_auth_container.visible = (selected_mode == "location")
        wifi_auth_container.visible = (selected_mode == "wifi")
        page.update()
    
    auth_mode.on_change = on_auth_mode_change
    
    async def save_attendance_settings(e):
        """Save attendance authentication settings"""
        try:
            e.control.disabled = True
            page.update()
            
            selected_mode = auth_mode.value
            update_data = {"auth_mode": selected_mode}
            
            if selected_mode == "location":
                # Validate location data
                lat, lng = saved_lat, saved_lng
                if hasattr(gps_display, "data") and gps_display.data:
                    lat, lng = gps_display.data
                
                if not lat or not lng:
                    page.open(ft.SnackBar(ft.Text("❌ 위치를 먼저 설정해주세요"), bgcolor="orange"))
                    e.control.disabled = False
                    page.update()
                    return
                
                update_data["location_lat"] = lat
                update_data["location_lng"] = lng
                update_data["location_address"] = tf_address.value.strip()
                update_data["wifi_ssid"] = None  # Clear WiFi if using location
                
            elif selected_mode == "wifi":
                # Validate WiFi data
                wifi_ssid = tf_wifi.value.strip()
                if not wifi_ssid:
                    page.open(ft.SnackBar(ft.Text("❌ Wi-Fi SSID를 입력해주세요"), bgcolor="orange"))
                    e.control.disabled = False
                    page.update()
                    return
                
                update_data["wifi_ssid"] = wifi_ssid
                update_data["location_lat"] = None  # Clear location if using WiFi
                update_data["location_lng"] = None
                update_data["location_address"] = None
            
            # Update database
            service_supabase.table("channels").update(update_data).eq("id", channel_id).execute()
            
            mode_text = "위치 인증" if selected_mode == "location" else "Wi-Fi 인증"
            page.open(ft.SnackBar(ft.Text(f"✅ 출퇴근 인증 정보가 저장되었습니다. ({mode_text})"), bgcolor="green"))
            log_debug(f"Attendance settings saved: mode={selected_mode}, data={update_data}")
            
        except Exception as ex:
            log_error(f"Save attendance settings error: {ex}")
            import traceback
            log_error(traceback.format_exc())
            page.open(ft.SnackBar(ft.Text(f"저장 실패: {ex}"), bgcolor="red"))
        finally:
            e.control.disabled = False
            page.update()
    
    attendance_settings_section = ft.Container(
        content=ft.Column([
            ft.Text("출퇴근 인증 설정", style=AppTextStyles.BODY_SMALL),
            ft.Container(
                content=ft.Column([
                    ft.Text("인증 방식 선택", weight="bold", size=14),
                    auth_mode,
                    ft.Divider(height=10, color="#EEEEEE"),
                    
                    # Location auth (conditional)
                    location_auth_container,
                    
                    # WiFi auth (conditional)
                    wifi_auth_container,
                    
                    ft.Container(height=10),
                    ft.ElevatedButton(
                        "인증 정보 저장",
                        on_click=save_attendance_settings,
                        bgcolor=AppColors.PRIMARY,
                        color="white",
                        expand=True,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                    )
                ], spacing=10),
                padding=15,
                bgcolor="white",
                border_radius=10,
                border=ft.border.all(1, "#EEEEEE")
            )
        ]),
        visible=(role == "owner")  # Only owner can configure attendance auth
    )
    
    # Load members if owner
    if role == "owner":
        await load_members()

    # === LAYOUT CONSTRUCTION ===

    header = AppHeader(
        title_text="설정",
        on_back_click=lambda e: page.run_task(navigate_to, "home")
    )

    current_store_settings = ft.Container(
        padding=AppLayout.CONTENT_PADDING,
        content=ft.Column([
            # Invite Code Section
            ft.Container(
                content=ft.Column([
                    ft.Text("직원 초대 코드", style=AppTextStyles.BODY_SMALL),
                    ft.Container(
                        padding=15,
                        bgcolor=AppColors.SURFACE_VARIANT,
                        border_radius=8,
                        content=ft.Column([
                            ft.Row([ft.Icon(ft.Icons.QR_CODE, color=AppColors.SECONDARY), code_display]),
                            code_expiry,
                            ft.Row([
                                generate_btn,
                                ft.IconButton(ft.Icons.COPY, icon_color=AppColors.SECONDARY, on_click=lambda e: asyncio.create_task(copy_code(e)))
                            ])
                        ])
                    ),
                ]),
                visible=(role in ["owner", "manager"])
            ),

            ft.Container(height=30),

            # Attendance Settings Section
            attendance_settings_section,

            ft.Container(height=30),

            # Personal Settings Section
            ft.Text("개인 설정", style=AppTextStyles.BODY_SMALL),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.PERSON_OUTLINE, color=AppColors.TEXT_SECONDARY),
                        ft.Text("내 프로필 관리", expand=True, size=14),
                        ft.IconButton(
                            ft.Icons.CHEVRON_RIGHT,
                            icon_color=AppColors.TEXT_SECONDARY,
                            on_click=lambda _: asyncio.create_task(navigate_to("profile"))
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

                    ft.Divider(height=10, color="transparent"),

                    ft.Row([
                        ft.Icon(ft.Icons.DARK_MODE_OUTLINED, color=AppColors.TEXT_SECONDARY),
                        ft.Text("테마 설정 (다크 모드)", expand=True, size=14),
                        ft.Switch(
                            value=(page.theme_mode == ft.ThemeMode.DARK),
                            active_color=AppColors.PRIMARY,
                            on_change=toggle_theme
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

                    ft.Divider(height=10, color="transparent"),

                    ft.Row([
                        ft.Icon(ft.Icons.NOTIFICATIONS_OUTLINED, color=AppColors.TEXT_SECONDARY),
                        ft.Text("푸시 알림 받기", expand=True, size=14),
                        ft.Switch(value=True, active_color=AppColors.PRIMARY)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

                    ft.Divider(height=10, color="transparent"),

                    ft.Row([
                        ft.Icon(ft.Icons.EXIT_TO_APP, color="red"),
                        ft.Text("매장 탈퇴하기", expand=True, size=14, color="red"),
                        ft.IconButton(
                            ft.Icons.CHEVRON_RIGHT,
                            icon_color="red",
                            on_click=lambda e: asyncio.create_task(confirm_leave_store(e))
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ]),
                padding=15,
                bgcolor="white",
                border_radius=10,
                border=ft.border.all(1, "#EEEEEE")
            ),

            ft.Container(height=30),

            # Member Management Section (Owner only)
            ft.Text(
                "매장 멤버 관리",
                style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
                visible=(role == "owner")
            ),
            member_mgmt_col if role == "owner" else ft.Container(),

            ft.Container(height=30),

            # App Info Section
            ft.Text("앱 정보", style=AppTextStyles.BODY_SMALL),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("버전 정보", expand=True, size=14),
                        ft.Text("v1.0.0", size=14, color="grey")
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=1, color="#EEEEEE"),
                    ft.Row([
                        ft.Text("이용약관", expand=True, size=14),
                        ft.Icon(ft.Icons.OPEN_IN_NEW, size=16, color="grey")
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=1, color="#EEEEEE"),
                    ft.Row([
                        ft.Text("개인정보 처리방침", expand=True, size=14),
                        ft.Icon(ft.Icons.OPEN_IN_NEW, size=16, color="grey")
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ], spacing=15),
                padding=15,
                bgcolor="white",
                border_radius=10,
                border=ft.border.all(1, "#EEEEEE")
            )
        ])
    )

    return [
        ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                bgcolor=AppColors.SURFACE,
                content=ft.ListView(
                    controls=[
                        header,
                        ft.Container(content=current_store_settings),
                        msg
                    ],
                    expand=True,
                    spacing=0
                )
            )
        )
    ]
