import flet as ft
import asyncio
import json
from datetime import datetime, timedelta
from services.handover_service import handover_service
from services import audio_service
from utils.logger import log_info, log_error, log_debug
from views.styles import AppColors, AppTextStyles, AppLayout, AppButtons
from views.components.app_header import AppHeader
from views.components.modal_overlay import ModalOverlay


async def get_handover_controls(page: ft.Page, navigate_to):
    user_id = page.app_session.get("user_id")
    channel_id = page.app_session.get("channel_id")

    # UI State
    current_tab = "인수 인계"
    grouped_data = {}
    POLL_INTERVAL = 10  # Seconds
    render_state = {"last_hash": None}

    # Voice Recording State
    voice_state = {"is_recording": False, "is_listening": False}
    audio_recorder = getattr(page, "audio_recorder", None)
    is_web_mode = getattr(page, "web", True)  # Default to web mode for safety

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
    
    # [FAUX DIALOG] Overlay Component
    overlay = ModalOverlay(page)

    # Mic Icon & Button
    mic_icon = ft.Icon(ft.Icons.MIC, color="white", size=20)
    mic_btn = ft.Container(
        content=mic_icon,
        width=40, height=40,
        bgcolor="#00C73C",
        border_radius=20,
        alignment=ft.Alignment(0, 0),
        tooltip="음성으로 입력",
        ink=True,
    )

    async def update_mic_ui(is_active=False, status_msg=""):
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
    # iOS Safari 호환성 개선
    # ============================================
    async def start_web_speech():
        """Web Speech API를 사용한 브라우저 내 음성인식 (iOS 호환)"""
        if voice_state["is_listening"]:
            log_debug("[Voice] Already listening, skipping")
            return

        voice_state["is_listening"] = True
        await update_mic_ui(True, "🎤 말씀하세요...")
        log_info("[Voice] Starting Web Speech API")

        # iOS Safari 호환 Web Speech API JavaScript
        # - iOS에서는 webkitSpeechRecognition 사용
        # - 에러 처리 강화
        # - 타임아웃 처리 추가
        js_code = """
        (function() {
            // 이전 결과 초기화
            window.speechResult = { status: 'initializing' };

            // iOS/Safari 호환성 체크
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

            if (!SpeechRecognition) {
                window.speechResult = { status: 'error', error: 'not_supported' };
                console.log('[Voice] SpeechRecognition not supported');
                return;
            }

            try {
                const recognition = new SpeechRecognition();
                recognition.lang = 'ko-KR';
                recognition.interimResults = false;
                recognition.maxAlternatives = 1;
                recognition.continuous = false;

                // iOS에서 중요: 짧은 타임아웃 설정
                let timeoutId = setTimeout(() => {
                    console.log('[Voice] Timeout - stopping recognition');
                    try {
                        recognition.stop();
                    } catch(e) {}
                    if (window.speechResult.status === 'listening') {
                        window.speechResult = { status: 'error', error: 'timeout' };
                    }
                }, 10000);  // 10초 타임아웃

                window.speechResult = { status: 'listening' };
                console.log('[Voice] Recognition started, listening...');

                recognition.onresult = (event) => {
                    clearTimeout(timeoutId);
                    console.log('[Voice] Got result');
                    if (event.results && event.results[0] && event.results[0][0]) {
                        const transcript = event.results[0][0].transcript;
                        const confidence = event.results[0][0].confidence;
                        console.log('[Voice] Transcript:', transcript, 'Confidence:', confidence);
                        window.speechResult = { status: 'done', text: transcript, confidence: confidence };
                    } else {
                        window.speechResult = { status: 'done', text: '' };
                    }
                };

                recognition.onerror = (event) => {
                    clearTimeout(timeoutId);
                    console.log('[Voice] Error:', event.error);
                    window.speechResult = { status: 'error', error: event.error || 'unknown' };
                };

                recognition.onend = () => {
                    clearTimeout(timeoutId);
                    console.log('[Voice] Recognition ended, current status:', window.speechResult.status);
                    // 아직 listening 상태면 완료로 변경 (음성 없이 종료된 경우)
                    if (window.speechResult.status === 'listening') {
                        window.speechResult = { status: 'done', text: '' };
                    }
                };

                recognition.onnomatch = () => {
                    clearTimeout(timeoutId);
                    console.log('[Voice] No match');
                    window.speechResult = { status: 'done', text: '' };
                };

                // iOS Safari: 사용자 제스처 컨텍스트 내에서 start() 호출 필수
                recognition.start();
                console.log('[Voice] recognition.start() called');

            } catch(e) {
                console.log('[Voice] Exception:', e.message);
                window.speechResult = { status: 'error', error: e.message || 'start_failed' };
            }
        })();
        """

        try:
            # Start speech recognition
            log_debug("[Voice] Executing JavaScript...")
            await page.run_javascript(js_code)
            log_debug("[Voice] JavaScript executed, starting poll...")

            # Poll for result (max 12 seconds, 0.4초 간격)
            max_polls = 30
            for i in range(max_polls):
                await asyncio.sleep(0.4)

                try:
                    result = await page.run_javascript("JSON.stringify(window.speechResult || {})")
                    log_debug(f"[Voice] Poll {i+1}/{max_polls}: {result}")
                except Exception as js_err:
                    log_error(f"[Voice] JavaScript poll error: {js_err}")
                    continue

                if not result:
                    continue

                try:
                    data = json.loads(result)
                except json.JSONDecodeError:
                    log_error(f"[Voice] JSON parse error: {result}")
                    continue

                status = data.get("status", "")

                # 아직 초기화/리스닝 중이면 계속 대기
                if status in ["initializing", "listening"]:
                    continue

                # 에러 처리
                if status == "error":
                    error_code = data.get("error", "unknown")
                    log_error(f"[Voice] Speech recognition error: {error_code}")

                    error_messages = {
                        "not_supported": "이 브라우저는 음성인식을 지원하지 않습니다.\niOS 14.5 이상 또는 Chrome을 사용해주세요.",
                        "not-allowed": "마이크 권한을 허용해주세요.\n설정 > Safari > 마이크에서 권한을 확인하세요.",
                        "no-speech": "음성이 감지되지 않았습니다.\n다시 시도해주세요.",
                        "audio-capture": "마이크에 접근할 수 없습니다.\n다른 앱이 마이크를 사용 중인지 확인하세요.",
                        "network": "네트워크 오류입니다. 인터넷 연결을 확인하세요.",
                        "aborted": "음성 인식이 중단되었습니다.",
                        "timeout": "시간이 초과되었습니다. 다시 시도해주세요.",
                        "start_failed": "음성 인식을 시작할 수 없습니다.\nHTTPS 연결이 필요합니다.",
                    }
                    msg = error_messages.get(error_code, f"음성 인식 오류: {error_code}")

                    page.open(ft.SnackBar(ft.Text(msg), bgcolor="red"))
                    break

                # 완료 처리
                if status == "done":
                    text = data.get("text", "").strip()
                    log_info(f"[Voice] Recognition done. Text: '{text}'")

                    if text:
                        # 기존 텍스트에 추가
                        if input_tf.value:
                            input_tf.value = input_tf.value + " " + text
                        else:
                            input_tf.value = text
                        input_tf.update()
                        page.open(ft.SnackBar(
                            ft.Text("✅ 음성이 변환되었습니다."),
                            bgcolor="green"
                        ))
                    else:
                        page.open(ft.SnackBar(
                            ft.Text("음성이 인식되지 않았습니다. 다시 시도해주세요."),
                            bgcolor="orange"
                        ))
                    break
            else:
                # 폴링 완료 후에도 결과가 없으면
                log_error("[Voice] Polling timeout - no result received")
                page.open(ft.SnackBar(
                    ft.Text("음성 인식 시간이 초과되었습니다."),
                    bgcolor="orange"
                ))

        except Exception as e:
            log_error(f"[Voice] start_web_speech exception: {e}")
            page.open(ft.SnackBar(
                ft.Text(f"음성 인식 실패: {str(e)[:50]}"),
                bgcolor="red"
            ))
        finally:
            voice_state["is_listening"] = False
            await update_mic_ui(False)
            page.update()
            log_info("[Voice] Web speech session ended")

    # ============================================
    # Desktop AudioRecorder + Whisper API
    # ============================================
    async def start_desktop_recording():
        """데스크톱: AudioRecorder + OpenAI Whisper"""
        if voice_state["is_recording"]:
            log_debug("[Voice] Already recording")
            return
        if not audio_recorder:
            log_error("[Voice] AudioRecorder not available")
            page.open(ft.SnackBar(
                ft.Text("오디오 녹음기를 사용할 수 없습니다."),
                bgcolor="red"
            ))
            page.update()
            return

        try:
            voice_state["is_recording"] = True
            await update_mic_ui(True, "🎤 녹음 중... (클릭하여 중지)")
            log_info("[Voice] Starting desktop recording")

            fname = f"handover_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            await audio_recorder.start_recording_async(output_path=fname)
            log_debug(f"[Voice] Recording started: {fname}")

        except Exception as e:
            log_error(f"[Voice] Recording start failed: {e}")
            voice_state["is_recording"] = False
            await update_mic_ui(False)
            page.open(ft.SnackBar(ft.Text(f"녹음 시작 실패: {e}"), bgcolor="red"))
            page.update()

    async def stop_desktop_recording():
        """데스크톱: 녹음 중지 및 Whisper 변환"""
        if not voice_state["is_recording"]:
            log_debug("[Voice] Not recording, nothing to stop")
            return

        try:
            await update_mic_ui(True, "⏳ AI 변환 중...")
            log_info("[Voice] Stopping recording and transcribing")

            res = await audio_recorder.stop_recording_async()
            voice_state["is_recording"] = False
            log_debug(f"[Voice] Recording stopped, result: {res}")

            if res:
                # [FIX] blob URL 감지 - 웹 브라우저에서 발생
                if res.startswith("blob:"):
                    log_info("[Voice] Blob URL detected, switching to Web Speech API")
                    await update_mic_ui(False)
                    page.open(ft.SnackBar(
                        ft.Text("브라우저에서는 Web Speech API를 사용합니다."),
                        bgcolor="orange"
                    ))
                    page.update()
                    # Web Speech API로 재시도
                    await start_web_speech()
                    return

                text = await asyncio.to_thread(lambda: audio_service.transcribe_audio(res))
                log_info(f"[Voice] Transcription result: '{text[:50] if text else 'empty'}...'")

                if text:
                    if input_tf.value:
                        input_tf.value = input_tf.value + " " + text
                    else:
                        input_tf.value = text
                    input_tf.update()
                    page.open(ft.SnackBar(
                        ft.Text("✅ 음성이 변환되었습니다."),
                        bgcolor="green"
                    ))
                else:
                    page.open(ft.SnackBar(
                        ft.Text("음성 인식 결과가 없습니다."),
                        bgcolor="orange"
                    ))
            else:
                log_error("[Voice] No recording result")
                page.open(ft.SnackBar(
                    ft.Text("녹음 결과가 없습니다."),
                    bgcolor="orange"
                ))

            await update_mic_ui(False)
            page.update()

        except Exception as e:
            log_error(f"[Voice] Transcription failed: {e}")
            voice_state["is_recording"] = False
            await update_mic_ui(False)
            page.open(ft.SnackBar(ft.Text(f"음성 변환 실패: {e}"), bgcolor="red"))
            page.update()

    # ============================================
    # 마이크 버튼 클릭 핸들러
    # ============================================
    async def on_mic_click(e):
        """마이크 버튼 클릭 - iOS에서는 항상 Web Speech API 사용"""
        log_info(f"[Voice] Mic clicked. is_listening={voice_state['is_listening']}, is_recording={voice_state['is_recording']}")

        if voice_state["is_listening"]:
            log_debug("[Voice] Already listening, ignoring click")
            return

        if voice_state["is_recording"]:
            await stop_desktop_recording()
            return

        # 음성 인식 시작
        await try_speech_recognition()

    async def try_speech_recognition():
        """브라우저 환경에서는 Web Speech API 사용, 데스크톱 앱에서만 AudioRecorder 사용"""
        log_info("[Voice] try_speech_recognition called")

        # 먼저 브라우저 환경인지 확인
        is_browser = is_web_mode

        try:
            # 브라우저 환경 감지 및 Web Speech API 지원 확인
            check_js = """
            (function() {
                try {
                    if (typeof window === 'undefined') {
                        return JSON.stringify({ isBrowser: false });
                    }

                    var isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
                    var isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
                    var isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
                    var hasSpeechAPI = !!(window.SpeechRecognition || window.webkitSpeechRecognition);

                    console.log('[Voice] Browser check - iOS:', isIOS, 'Safari:', isSafari, 'Mobile:', isMobile, 'SpeechAPI:', hasSpeechAPI);

                    return JSON.stringify({
                        isBrowser: true,
                        isIOS: isIOS,
                        isSafari: isSafari,
                        isMobile: isMobile,
                        hasSpeechAPI: hasSpeechAPI,
                        userAgent: navigator.userAgent.substring(0, 100)
                    });
                } catch(e) {
                    return JSON.stringify({ isBrowser: true, error: e.message });
                }
            })()
            """

            result_str = await page.run_javascript(check_js)
            log_info(f"[Voice] Browser check result: {result_str}")

            try:
                result = json.loads(result_str) if result_str else {}
            except json.JSONDecodeError:
                log_error(f"[Voice] Failed to parse result: {result_str}")
                result = {}

            is_browser = result.get("isBrowser", True)
            is_ios = result.get("isIOS", False)
            is_mobile = result.get("isMobile", False)
            has_speech_api = result.get("hasSpeechAPI", False)

            log_info(f"[Voice] Detection - Browser:{is_browser}, iOS:{is_ios}, Mobile:{is_mobile}, SpeechAPI:{has_speech_api}")

            # 브라우저 환경 (특히 iOS/모바일)에서는 무조건 Web Speech API 사용
            if is_browser and (is_ios or is_mobile):
                log_info("[Voice] Mobile browser detected - using Web Speech API only")
                if has_speech_api:
                    await start_web_speech()
                else:
                    # iOS Safari에서 Speech API가 없다고 나오면 직접 시도
                    log_info("[Voice] SpeechAPI not detected but trying anyway (iOS quirk)")
                    await start_web_speech()
                return

            # 데스크톱 브라우저
            if is_browser and has_speech_api:
                log_info("[Voice] Desktop browser with Speech API - using Web Speech")
                await start_web_speech()
                return

            # 데스크톱 앱 (Flet 네이티브)
            if not is_browser and audio_recorder:
                log_info("[Voice] Desktop app - using AudioRecorder")
                await start_desktop_recording()
                return

            # Fallback: Web Speech 시도
            log_info("[Voice] Fallback - trying Web Speech API")
            await start_web_speech()

        except Exception as e:
            log_error(f"[Voice] try_speech_recognition error: {e}")
            # 에러 시에도 Web Speech API 시도 (iOS에서 JavaScript 실행 실패할 수 있음)
            log_info("[Voice] Error occurred, trying Web Speech API as fallback")
            try:
                await start_web_speech()
            except Exception as e2:
                log_error(f"[Voice] Web Speech fallback also failed: {e2}")
                page.open(ft.SnackBar(
                    ft.Text("음성 인식을 시작할 수 없습니다."),
                    bgcolor="red"
                ))
                page.update()

    mic_btn.on_click = lambda e: asyncio.create_task(on_mic_click(e))

    # ============================================
    # 기존 기능들
    # ============================================
    def open_edit_dialog(item):
        edit_tf = ft.TextField(value=item.get("content", ""), multiline=True, expand=True)

        async def save_edit(e):
            print(f"[VIEW DEBUG] save_edit clicked. Item ID: {item.get('id')}, User ID: {user_id}")
            try:
                if await handover_service.update_handover(item.get("id"), edit_tf.value, user_id):
                    print("[VIEW DEBUG] Update success")
                    overlay.close()
                    await fetch_and_update()
                else:
                    print("[VIEW DEBUG] Update returned False")
                    page.open(ft.SnackBar(ft.Text("수정 실패: 권한이 없거나 오류 발생"), bgcolor="red"))
                    page.update()
            except Exception as ex:
                print(f"[VIEW DEBUG] Update Exception: {ex}")
                page.open(ft.SnackBar(ft.Text(f"오류: {ex}"), bgcolor="red"))
                page.update()

        async def close_with_update(e_ign=None):
             overlay.close()

        # [FAUX DIALOG] Replace AlertDialog with Card Container
        card_content = ft.Container(
            width=400,
            padding=20,
            bgcolor=AppColors.SURFACE,
            border_radius=20,
            on_click=lambda e: e.control.page.update(), # Prevent click bubbling
            content=ft.Column([
                 ft.Text("기록 수정", size=20, weight="bold", color=AppColors.TEXT_PRIMARY),
                 ft.Container(height=10),
                 ft.Container(content=edit_tf, height=100),
                 ft.Container(height=20),
                 ft.Row([
                     ft.TextButton("취소", on_click=close_with_update, style=AppButtons.SECONDARY()),
                     ft.Container(width=10),
                     ft.ElevatedButton("저장", on_click=lambda e: asyncio.create_task(save_edit(e)), style=AppButtons.PRIMARY())
                 ], alignment=ft.MainAxisAlignment.END)
            ], tight=True)
        )
        overlay.open(card_content)

    async def delete_entry(item_id):
        await handover_service.delete_handover(item_id, user_id)
        await fetch_and_update()

    async def render_feed():
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
                    alignment=ft.Alignment(0, 0),
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
                    return lambda e, h=handler: asyncio.create_task(h(e))

                def create_delete_handler(oid):
                    async def handler(e): await delete_entry(oid)
                    return lambda e, h=handler: asyncio.create_task(h(e))

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
        # [FIX] Scroll to bottom aka "Latest"
        try:
            if hasattr(list_view, "scroll_to_async"):
                await list_view.scroll_to_async(offset=-1, duration=300)
            else:
                await list_view.scroll_to(offset=-1, duration=300)
            page.update()
        except Exception:
            pass

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
        import hashlib
        # Serialize for hashing
        try:
            # We only care about data that affects the UI: CreatedAt, Content, Category, UserID
            # Create a lightweight list of tuples for hashing
            hash_data = []
            for item in raw:
                hash_data.append(f"{item.get('id')}:{item.get('updated_at') or item.get('created_at')}")
            
            current_hash = hashlib.md5("".join(hash_data).encode()).hexdigest()
        except Exception:
            current_hash = str(datetime.now()) # Fallback

        # Check against last known hash (using a closure or simple attr logic if possible, 
        # but here we use a mutable container from outer scope or simple attribute on function if it were a class)
        # Since this is a nested function, we can use a nonlocal or a dict in the outer scope.
        # Let's assume 'render_state' dict exists in outer scope for this purpose.
        
        nonlocal render_state
        if render_state.get("last_hash") == current_hash:
            # log_debug("[Handover] Skipping render (No Change)")
            return

        render_state["last_hash"] = current_hash
        log_debug(f"[Handover] Data changed (Hash: {current_hash[:8]}). Re-rendering.")

        nonlocal grouped_data
        grouped_data = dict(temp_grouped)
        await render_feed()

    async def submit_entry(e=None):
        txt = input_tf.value
        if not txt.strip(): return
        input_tf.value = ""; input_tf.update()
        target_cat = "handover" if current_tab == "인수 인계" else "order"
        await handover_service.add_handover_entry(user_id, channel_id, target_cat, txt)
        await fetch_and_update()

    async def on_tab_change(e):
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
        await render_feed()

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
            on_click=lambda e: asyncio.create_task(on_tab_change(e)),
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
                ft.IconButton(ft.Icons.SEND_ROUNDED, on_click=lambda e: asyncio.create_task(submit_entry()))
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.END)
        ], spacing=5),
        padding=10
    )
    header = AppHeader(
        title_text="업무 일지",
        on_back_click=lambda e: asyncio.create_task(navigate_to("home"))
    )
    
    # Custom Header Container was combining title and tabs. 
    # Now AppHeader handles title. Tabs should be separate.

    async def poll_updates():
        while True:
            await asyncio.sleep(POLL_INTERVAL)
            # Only poll if this view is effectively active (simple check)
            try:
                await fetch_and_update()
            except Exception:
                break

    asyncio.create_task(fetch_and_update())
    asyncio.create_task(poll_updates())
    
    main_layout = ft.SafeArea(
        expand=True,
        content=ft.Column([header, tabs_row, ft.Container(list_view, expand=True), input_area], expand=True)
    )

    return [
        ft.Stack(
            [
                main_layout,
                overlay
            ],
            expand=True
        )
    ]
