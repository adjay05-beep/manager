import flet as ft
import asyncio
from datetime import datetime, timedelta
from services.handover_service import handover_service
from services import audio_service
from views.styles import AppColors, AppTextStyles, AppLayout, AppButtons
from views.components.app_header import AppHeader

def get_handover_controls(page: ft.Page, navigate_to):
    user_id = page.session.get("user_id")
    channel_id = page.session.get("channel_id")

    # UI State
    current_tab = "인수 인계"
    grouped_data = {}
    POLL_INTERVAL = 10 # Seconds

    # Voice Recording State
    voice_state = {"is_recording": False, "is_listening": False}
    audio_recorder = getattr(page, "audio_recorder", None)
    is_web_mode = page.web

    # Controls
    list_view = ft.ListView(expand=True, spacing=10, padding=20)
    input_tf = ft.TextField(
        hint_text="내용을 입력하세요...",
        expand=True,
        border_radius=20,
        bgcolor="#F5F5F5",
        border_color="transparent",
        content_padding=ft.padding.symmetric(horizontal=15, vertical=10),
        multiline=True,
        min_lines=1,
        max_lines=4,
    )

    # Voice Recording Status
    voice_status = ft.Text("", size=11, color="red", visible=False)

    # Mic Icon & Button
    mic_icon = ft.Icon(ft.Icons.MIC, color="white", size=20)
    mic_btn = ft.Container(
        content=mic_icon,
        width=40, height=40,
        bgcolor="#00C73C",
        border_radius=20,
        alignment=ft.alignment.center,
        tooltip="음성으로 입력",
        ink=True,
    )

    def update_mic_ui(is_active=False, status_msg=""):
        if is_active:
            mic_icon.name = ft.Icons.STOP
            mic_btn.bgcolor = "red"
            voice_status.value = status_msg or "듣는 중..."
            voice_status.color = "red"
            voice_status.visible = True
        else:
            mic_icon.name = ft.Icons.MIC
            mic_btn.bgcolor = "#00C73C"
            voice_status.visible = False
        try:
            mic_btn.update()
            voice_status.update()
        except Exception:
            pass

    # ============================================
    # Web Speech API (모바일/웹용) - JavaScript 기반
    # ============================================
    async def start_web_speech():
        """Web Speech API를 사용한 브라우저 내 음성인식"""
        if voice_state["is_listening"]:
            return

        voice_state["is_listening"] = True
        update_mic_ui(True, "🎤 말씀하세요...")

        # Web Speech API JavaScript
        js_code = """
        (function() {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                window.speechResult = { error: 'not_supported' };
                return;
            }

            const recognition = new SpeechRecognition();
            recognition.lang = 'ko-KR';
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;
            recognition.continuous = false;

            window.speechResult = { status: 'listening' };

            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                window.speechResult = { status: 'done', text: transcript };
            };

            recognition.onerror = (event) => {
                window.speechResult = { status: 'error', error: event.error };
            };

            recognition.onend = () => {
                if (window.speechResult.status === 'listening') {
                    window.speechResult = { status: 'done', text: '' };
                }
            };

            try {
                recognition.start();
            } catch(e) {
                window.speechResult = { error: e.message };
            }
        })();
        """

        try:
            # Start speech recognition
            await page.run_javascript_async(js_code)

            # Poll for result (max 15 seconds)
            for i in range(30):
                await asyncio.sleep(0.5)
                result = await page.run_javascript_async("JSON.stringify(window.speechResult || {})")

                if result:
                    import json
                    try:
                        data = json.loads(result)
                    except Exception:
                        continue

                    if data.get("error") == "not_supported":
                        page.snack_bar = ft.SnackBar(
                            ft.Text("이 브라우저는 음성인식을 지원하지 않습니다."),
                            bgcolor="red"
                        )
                        page.snack_bar.open = True
                        break

                    if data.get("status") == "done":
                        text = data.get("text", "")
                        if text:
                            # 기존 텍스트에 추가
                            if input_tf.value:
                                input_tf.value = input_tf.value + " " + text
                            else:
                                input_tf.value = text
                            input_tf.update()
                            page.snack_bar = ft.SnackBar(
                                ft.Text("✅ 음성이 변환되었습니다. 수정 후 전송하세요."),
                                bgcolor="green"
                            )
                        else:
                            page.snack_bar = ft.SnackBar(
                                ft.Text("음성이 인식되지 않았습니다. 다시 시도해주세요."),
                                bgcolor="orange"
                            )
                        page.snack_bar.open = True
                        break

                    if data.get("status") == "error":
                        error_msg = data.get("error", "unknown")
                        if error_msg == "not-allowed":
                            msg = "마이크 권한을 허용해주세요."
                        elif error_msg == "no-speech":
                            msg = "음성이 감지되지 않았습니다."
                        else:
                            msg = f"음성 인식 오류: {error_msg}"
                        page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="red")
                        page.snack_bar.open = True
                        break

        except Exception as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"음성 인식 실패: {e}"), bgcolor="red")
            page.snack_bar.open = True
        finally:
            voice_state["is_listening"] = False
            update_mic_ui(False)
            page.update()

    # ============================================
    # Desktop AudioRecorder + Whisper API
    # ============================================
    async def start_desktop_recording():
        """데스크톱: AudioRecorder + OpenAI Whisper"""
        if voice_state["is_recording"] or not audio_recorder:
            return
        try:
            voice_state["is_recording"] = True
            update_mic_ui(True, "🎤 녹음 중... (클릭하여 중지)")

            fname = f"handover_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            await audio_recorder.start_recording_async(output_path=fname)
        except Exception as e:
            voice_state["is_recording"] = False
            update_mic_ui(False)
            page.snack_bar = ft.SnackBar(ft.Text(f"녹음 시작 실패: {e}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    async def stop_desktop_recording():
        """데스크톱: 녹음 중지 및 Whisper 변환"""
        if not voice_state["is_recording"]:
            return
        try:
            update_mic_ui(True, "⏳ AI 변환 중...")

            res = await audio_recorder.stop_recording_async()
            voice_state["is_recording"] = False

            if res:
                # [FIX] blob URL 감지 - 웹 브라우저에서 발생
                if res.startswith("blob:"):
                    print(f"DEBUG: Blob URL detected in handover: {res}")
                    update_mic_ui(False)
                    page.snack_bar = ft.SnackBar(
                        ft.Text("브라우저에서는 Web Speech API를 사용합니다. 다시 시도해주세요."),
                        bgcolor="orange"
                    )
                    page.snack_bar.open = True
                    page.update()
                    # Web Speech API로 재시도
                    await start_web_speech()
                    return

                text = await asyncio.to_thread(lambda: audio_service.transcribe_audio(res))

                if text:
                    if input_tf.value:
                        input_tf.value = input_tf.value + " " + text
                    else:
                        input_tf.value = text
                    input_tf.update()
                    page.snack_bar = ft.SnackBar(
                        ft.Text("✅ 음성이 변환되었습니다. 수정 후 전송하세요."),
                        bgcolor="green"
                    )
                else:
                    page.snack_bar = ft.SnackBar(
                        ft.Text("음성 인식 결과가 없습니다."),
                        bgcolor="orange"
                    )
                page.snack_bar.open = True

            update_mic_ui(False)
            page.update()

        except Exception as e:
            voice_state["is_recording"] = False
            update_mic_ui(False)
            page.snack_bar = ft.SnackBar(ft.Text(f"음성 변환 실패: {e}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    # ============================================
    # 마이크 버튼 클릭 핸들러
    # ============================================
    def on_mic_click(e):
        # [FIX] 항상 Web Speech API를 먼저 시도 (브라우저 환경 자동 감지)
        if not voice_state["is_listening"] and not voice_state["is_recording"]:
            page.run_task(try_speech_recognition)
        elif voice_state["is_recording"]:
            page.run_task(stop_desktop_recording)

    async def try_speech_recognition():
        """Web Speech API를 먼저 시도하고, 실패 시 AudioRecorder 사용"""
        try:
            check_js = """
            (function() {
                if (typeof window === 'undefined') return 'no_window';
                if (window.SpeechRecognition || window.webkitSpeechRecognition) return 'supported';
                return 'not_supported';
            })()
            """
            result = await page.run_javascript_async(check_js)
            print(f"DEBUG: Speech API check result: {result}")

            if result == "supported":
                await start_web_speech()
            else:
                if audio_recorder:
                    await start_desktop_recording()
                else:
                    page.snack_bar = ft.SnackBar(
                        ft.Text("음성 인식을 사용할 수 없습니다."),
                        bgcolor="orange"
                    )
                    page.snack_bar.open = True
                    page.update()
        except Exception as e:
            print(f"DEBUG: try_speech_recognition error: {e}")
            if audio_recorder and not voice_state["is_recording"]:
                await start_desktop_recording()
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("음성 인식을 시작할 수 없습니다."),
                    bgcolor="red"
                )
                page.snack_bar.open = True
                page.update()

    mic_btn.on_click = on_mic_click

    # ============================================
    # 기존 기능들
    # ============================================
    def open_edit_dialog(item):
        edit_tf = ft.TextField(value=item.get("content", ""), multiline=True, expand=True)

        async def save_edit(e):
            if await handover_service.update_handover(item.get("id"), edit_tf.value):
                page.close(dlg)
                await fetch_and_update()

        dlg = ft.AlertDialog(
            title=ft.Text("기록 수정"),
            content=ft.Container(content=edit_tf, height=100),
            actions=[
                ft.TextButton("취소", on_click=lambda _: page.close(dlg)),
                ft.ElevatedButton("저장", on_click=save_edit, style=AppButtons.PRIMARY())
            ]
        )
        page.open(dlg)

    async def delete_entry(item_id):
        await handover_service.delete_handover(item_id)
        await fetch_and_update()

    def render_feed():
        list_view.controls.clear()
        target_cat = "handover" if current_tab == "인수 인계" else "order"

        # Sort dates ascending (oldest first, latest at bottom)
        sorted_dates = sorted(grouped_data.keys(), reverse=False)

        for d_str in sorted_dates:
            items = grouped_data[d_str].get(target_cat, [])
            if not items: continue

            # Date Header
            dt = datetime.fromisoformat(d_str)
            m, d = dt.month, dt.day
            today_str = (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d")
            header_text = f"{m}월 {d}일"
            if d_str == today_str: header_text += " (오늘)"

            list_view.controls.append(
                ft.Container(
                    content=ft.Text(header_text, size=12, color="grey", weight="bold"),
                    alignment=ft.alignment.center,
                    padding=ft.padding.only(top=10, bottom=5)
                )
            )

            for item in items:
                content = item.get("content", "")
                time_str = item.get("time_str", "")
                author = item.get("user_name", "")
                item_id = item.get("id")

                def create_edit_handler(i):
                    async def handler(e): open_edit_dialog(i)
                    return handler

                def create_delete_handler(oid):
                    async def handler(e): await delete_entry(oid)
                    return handler

                edit_btn = ft.IconButton(ft.Icons.EDIT, icon_size=16, icon_color="grey", on_click=create_edit_handler(item))
                delete_btn = ft.IconButton(ft.Icons.CLOSE, icon_size=16, icon_color="grey", on_click=create_delete_handler(item_id))

                card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(content, size=15, color="#424242", expand=True),
                            ft.Row([edit_btn, delete_btn], spacing=0)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START),
                        ft.Row([
                            ft.Text(f"{author}", size=10, color="grey"),
                            ft.Text(time_str, size=10, color="grey")
                        ], alignment=ft.MainAxisAlignment.END)
                    ], spacing=5),
                    padding=10, bgcolor="white", border_radius=12, border=ft.border.all(1, "#EEEEEE"),
                )
                list_view.controls.append(card)

        list_view.controls.append(ft.Container(height=20))
        page.update()

    async def fetch_and_update():
        raw = await handover_service.get_handovers(channel_id)
        from collections import defaultdict
        temp_grouped = defaultdict(lambda: {"handover": [], "order": []})
        raw.sort(key=lambda x: x.get("created_at") or "")
        for item in raw:
            try:
                c_at = item.get("created_at")
                if c_at:
                    if c_at.endswith('Z'): c_at = c_at.replace('Z', '+00:00')
                    dt = datetime.fromisoformat(c_at) + timedelta(hours=9)
                    d_key = dt.strftime("%Y-%m-%d")
                    t_str = dt.strftime("%H:%M")
                    cat = item.get("category", "handover")
                    profile = item.get("profiles")
                    user_name = profile.get("full_name") if profile else "멤버"
                    temp_grouped[d_key][cat].append({"id": item.get("id"), "content": item.get("content"), "time_str": t_str, "user_name": user_name})
            except (ValueError, KeyError, AttributeError):
                pass  # Invalid date or missing data
        nonlocal grouped_data
        grouped_data = dict(temp_grouped)
        render_feed()

    async def submit_entry(e=None):
        txt = input_tf.value
        if not txt.strip(): return
        input_tf.value = ""; input_tf.update()
        target_cat = "handover" if current_tab == "인수 인계" else "order"
        await handover_service.add_handover_entry(user_id, channel_id, target_cat, txt)
        await fetch_and_update()

    def on_tab_change(e):
        nonlocal current_tab
        # e.control.data holds the tab name
        current_tab = e.control.data 
        
        # Update UI of tabs
        for c in tabs_row.controls:
            # Only update containers that are tabs (have data)
            if isinstance(c, ft.Container) and c.data:
                is_selected = c.data == current_tab
                # Update text style
                if isinstance(c.content, ft.Text):
                    c.content.color = "#1565C0" if is_selected else "#9E9E9E"
                    c.content.weight = ft.FontWeight.BOLD if is_selected else ft.FontWeight.NORMAL
        
        tabs_row.update()
        render_feed()

    def create_tab(text):
        is_selected = text == current_tab
        return ft.Container(
            content=ft.Text(
                text, 
                size=16, 
                color="#1565C0" if is_selected else "#9E9E9E",
                weight=ft.FontWeight.BOLD if is_selected else ft.FontWeight.NORMAL
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            on_click=on_tab_change,
            data=text  # Store tab name in data for easy access
        )

    tabs_row = ft.Row([
        create_tab("인수 인계"),
        ft.Text("|", size=16, color="#E0E0E0"), # Separator
        create_tab("발주 일지")
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)

    # 입력 영역 - 마이크 버튼 + 텍스트 필드 + 전송 버튼
    input_area = ft.Container(
        content=ft.Column([
            voice_status,
            ft.Row([
                mic_btn,
                input_tf,
                ft.IconButton(ft.Icons.SEND_ROUNDED, on_click=lambda e: page.run_task(submit_entry))
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.END)
        ], spacing=5),
        padding=10
    )
    header = AppHeader(
        title_text="업무 일지",
        on_back_click=page.go_back
    )
    
    # Custom Header Container was combining title and tabs. 
    # Now AppHeader handles title. Tabs should be separate.

    page.run_task(fetch_and_update)
    page.run_task(fetch_and_update)
    page.run_task(fetch_and_update)
    page.run_task(fetch_and_update)
    return [
        ft.SafeArea(
            expand=True,
            content=ft.Column([header, tabs_row, ft.Container(list_view, expand=True), input_area], expand=True)
        )
    ]
