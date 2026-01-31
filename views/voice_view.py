import flet as ft
from services import voice_service, audio_service
import asyncio
from datetime import datetime
import os
from views.styles import AppColors, AppTextStyles, AppLayout
from views.components.app_header import AppHeader

def get_voice_controls(page: ft.Page, navigate_to):
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    # Singleton Recorder Safety
    audio_recorder = getattr(page, "audio_recorder", None)
    if not audio_recorder:
        for ctrl in page.overlay:
             if "AudioRecorder" in str(type(ctrl)):
                 audio_recorder = ctrl
                 break

    # [RBAC] Get Context
    current_user_id = page.session.get("user_id")
    channel_id = page.session.get("channel_id")
    is_web_mode = page.web

    if not current_user_id:
        return [ft.Text("Please login first.", color="red")]

    state = {
        "is_recording": False,
        "is_listening": False,  # Web Speech API 상태
        "memos": [],
        "edit_id": None,
        "is_private_mode": True
    }

    # UI Components
    memo_list_view = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
    status_text = ft.Text("녹음 버튼을 눌러 시작하세요", color="grey", size=14)

    # ============================================
    # 메모 목록 관리
    # ============================================
    def load_memos():
        page.run_task(load_memos_async)

    async def load_memos_async():
        status_text.value = "로딩 중..."
        page.update()
        try:
            page.run_task(voice_service.voice_service.cleanup_expired_memos)
            state["memos"] = await voice_service.voice_service.get_memos(current_user_id, channel_id)
            render_memos()
            status_text.value = "대기 중"
            status_text.color = "grey"
        except Exception as e:
            print(f"Memo Load Error: {e}")
            status_text.value = "로딩 실패"
        page.update()

    def render_memos():
        memo_list_view.controls.clear()

        if not state["memos"]:
            memo_list_view.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.NOTE_ADD, size=40, color="#EEEEEE"),
                        ft.Text("첫 번째 음성 메모를 남겨보세요!", color="grey"),
                        ft.Text("오디오는 2일, 텍스트는 15일 보관됩니다.", size=10, color="orange")
                    ], horizontal_alignment="center"),
                    alignment=ft.alignment.center,
                    padding=40
                )
            )
        else:
            for memo in state["memos"]:
                is_private = memo.get("is_private", True)
                c = memo.get("content", "")
                date_str = memo.get("created_at", "")[:16].replace("T", " ")
                has_audio = bool(memo.get("audio_url"))

                icon = ft.Icon(ft.Icons.LOCK, size=14, color="grey") if is_private else ft.Icon(ft.Icons.PUBLIC, size=14, color="blue")
                style_color = "#333333" if is_private else "blue"
                bg_color = "white" if is_private else "#E3F2FD"

                card_content = ft.Column([
                    ft.Row([
                        icon,
                        ft.Text(date_str, size=10, color="grey"),
                        ft.Container(content=ft.Text("AUDIO", size=8, color="white"), bgcolor="green", padding=2, border_radius=3, visible=has_audio)
                    ], spacing=5),
                    ft.Text(c, size=14, color=style_color, selectable=True),
                ], spacing=5, expand=True)

                actions = []
                if is_private and channel_id:
                    actions.append(
                        ft.IconButton(
                            ft.Icons.IOS_SHARE, icon_size=18, tooltip="매장 공유 (공개 전환)", icon_color="blue",
                            on_click=lambda e, mid=memo['id']: share_memo(mid)
                        )
                    )

                actions.append(
                    ft.IconButton(
                        ft.Icons.CLOSE, icon_size=16, icon_color="#BDBDBD",
                        on_click=lambda e, mid=memo['id']: delete_memo(mid)
                    )
                )

                item = ft.Container(
                    content=ft.Row([card_content, ft.Row(actions, spacing=0)], alignment="spaceBetween", vertical_alignment="start"),
                    bgcolor=bg_color,
                    border_radius=10,
                    padding=15,
                    border=ft.border.all(1, "#F5F5F5"),
                    shadow=ft.BoxShadow(blur_radius=5, color="#05000000")
                )
                memo_list_view.controls.append(item)

        page.update()

    def share_memo(mid):
        async def _share():
            await voice_service.voice_service.share_memo(mid, "public")
            page.snack_bar = ft.SnackBar(ft.Text("매장에 공유되었습니다 (공개 전환)"))
            page.snack_bar.open = True
            await load_memos_async()
        page.run_task(_share)

    def delete_memo(mid):
        async def _del():
            await voice_service.voice_service.delete_memo(mid)
            await load_memos_async()
            page.snack_bar = ft.SnackBar(ft.Text("삭제되었습니다."))
            page.snack_bar.open = True
            page.update()
        page.run_task(_del)

    # ============================================
    # Web Speech API (모바일/웹용)
    # ============================================
    async def start_web_speech():
        """Web Speech API를 사용한 브라우저 내 음성인식 → 바로 메모 저장"""
        if state["is_listening"]:
            return

        state["is_listening"] = True
        update_mic_ui(True, "🎤 말씀하세요...")

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
                            ft.Text("이 브라우저는 음성인식을 지원하지 않습니다. 파일 업로드를 이용해주세요."),
                            bgcolor="red"
                        )
                        page.snack_bar.open = True
                        break

                    if data.get("status") == "done":
                        text = data.get("text", "")
                        if text:
                            # 바로 메모 저장
                            status_text.value = "저장 중..."
                            status_text.update()

                            await voice_service.voice_service.create_memo(
                                user_id=current_user_id,
                                content=text,
                                channel_id=channel_id,
                                is_private=state["is_private_mode"],
                                audio_url=None  # Web Speech는 오디오 저장 안함
                            )

                            page.snack_bar = ft.SnackBar(
                                ft.Text("✅ 음성 메모가 저장되었습니다!"),
                                bgcolor="green"
                            )
                            page.snack_bar.open = True
                            await load_memos_async()
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
            state["is_listening"] = False
            update_mic_ui(False)
            page.update()

    # ============================================
    # Desktop: AudioRecorder + Whisper
    # ============================================
    async def process_recording(url_or_path):
        """데스크톱 녹음 파일 처리"""
        try:
            status_text.value = "AI 분석 및 저장 중..."
            status_text.color = "blue"
            page.update()

            text = await asyncio.to_thread(lambda: audio_service.transcribe_audio(url_or_path))
            if not text:
                text = "(음성 인식 실패)"

            # Upload audio file to storage
            final_url = None
            if not ("blob:" in url_or_path or "http" in url_or_path):
                try:
                    fname = f"voice_{current_user_id}_{int(datetime.now().timestamp())}.wav"
                    with open(url_or_path, "rb") as f:
                        file_bytes = f.read()

                    from services.chat_service import upload_file_server_side, get_public_url
                    path_on_storage = f"voice/{fname}"
                    upload_file_server_side("chat-uploads", path_on_storage, file_bytes, "audio/wav")
                    final_url = get_public_url("chat-uploads", path_on_storage)
                except Exception as up_err:
                    print(f"Audio Upload Error: {up_err}")

            await voice_service.voice_service.create_memo(
                user_id=current_user_id,
                content=text,
                channel_id=channel_id,
                is_private=state["is_private_mode"],
                audio_url=final_url
            )

            status_text.value = "저장 완료"
            page.snack_bar = ft.SnackBar(ft.Text("✅ 음성 메모가 저장되었습니다!"), bgcolor="green")
            page.snack_bar.open = True
            await load_memos_async()

        except Exception as ex:
            status_text.value = f"Error: {ex}"
            page.update()

    async def stop_recording():
        try:
            res = await audio_recorder.stop_recording_async()
            state["is_recording"] = False
            update_mic_ui(False)
            if res:
                await process_recording(res)
        except Exception as e:
            status_text.value = f"Stop Error: {e}"
            page.update()

    async def start_desktop_recording():
        try:
            if state["is_recording"]:
                return

            state["is_recording"] = True
            update_mic_ui(True, "🎤 녹음 중... (클릭하여 중지)")

            fname = f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            await audio_recorder.start_recording_async(output_path=fname)
        except Exception as e:
            state["is_recording"] = False
            update_mic_ui(False)
            status_text.value = f"Start Error: {e}"
            page.update()

    # ============================================
    # UI 업데이트 및 클릭 핸들러
    # ============================================
    def update_mic_ui(is_active=False, msg=""):
        if is_active:
            mic_icon.name = ft.Icons.STOP
            mic_icon.color = "white"
            mic_container.bgcolor = "red"
            status_text.value = msg or "녹음 중..."
            status_text.color = "red"
        else:
            mic_icon.name = ft.Icons.MIC
            mic_icon.color = "white"
            mic_container.bgcolor = "#00C73C"
            status_text.value = "대기 중"
            status_text.color = "grey"
        try:
            mic_container.update()
            status_text.update()
        except Exception:
            pass

    def toggle_rec(e):
        # [FIX] 항상 Web Speech API를 먼저 시도 (브라우저 환경 자동 감지)
        # page.web이 클라우드 배포에서 신뢰할 수 없으므로 JS로 직접 확인
        if not state["is_listening"] and not state["is_recording"]:
            page.run_task(try_speech_recognition)
        elif state["is_recording"]:
            # 데스크톱 녹음 중지
            page.run_task(stop_recording)

    async def try_speech_recognition():
        """Web Speech API를 먼저 시도하고, 실패 시 AudioRecorder 사용"""
        try:
            # JavaScript로 브라우저 환경 및 Web Speech API 지원 확인
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
                # Web Speech API 미지원 - AudioRecorder 사용 시도
                if audio_recorder:
                    await start_desktop_recording()
                else:
                    page.snack_bar = ft.SnackBar(
                        ft.Text("음성 인식을 사용할 수 없습니다. 파일 업로드를 이용해주세요."),
                        bgcolor="orange"
                    )
                    page.snack_bar.open = True
                    page.update()
        except Exception as e:
            print(f"DEBUG: try_speech_recognition error: {e}")
            # JavaScript 실행 실패 = 데스크톱/네이티브 환경
            if audio_recorder and not state["is_recording"]:
                await start_desktop_recording()
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("음성 인식을 시작할 수 없습니다."),
                    bgcolor="red"
                )
                page.snack_bar.open = True
                page.update()

    # File Picker (Upload) - 백업용
    def pick_file_click(e):
        page.chat_file_picker.pick_files(allow_multiple=False, allowed_extensions=["mp3", "wav", "m4a"])

    async def on_picker_result(e: ft.FilePickerResultEvent):
        if e.files:
            f = e.files[0]
            status_text.value = "업로드 및 분석 중..."
            page.update()
            try:
                from services import storage_service
                def progress(msg):
                    status_text.value = msg
                    page.update()

                res = await asyncio.to_thread(
                    storage_service.handle_file_upload,
                    page.web,
                    f,
                    progress,
                    picker_ref=page.chat_file_picker
                )
                public_url = res.get("public_url")

                if public_url:
                    text = await asyncio.to_thread(lambda: audio_service.transcribe_audio(public_url))
                    if not text:
                        text = "(파일 분석 실패)"

                    await voice_service.voice_service.create_memo(
                        user_id=current_user_id,
                        content=text,
                        channel_id=channel_id,
                        is_private=state["is_private_mode"],
                        audio_url=public_url
                    )
                    status_text.value = "업로드 저장 완료"
                    page.snack_bar = ft.SnackBar(ft.Text("✅ 음성 메모가 저장되었습니다!"), bgcolor="green")
                    page.snack_bar.open = True
                    await load_memos_async()
            except Exception as ex:
                status_text.value = f"Upload Error: {ex}"
                page.update()

    page.chat_file_picker.on_result = lambda e: page.run_task(lambda: on_picker_result(e))

    # Mode Toggle UI
    def toggle_private_mode(e):
        state["is_private_mode"] = e.control.value
        mode_text.value = "나만 보기 (기본)" if state["is_private_mode"] else "매장 전체 공유"
        mode_text.color = "grey" if state["is_private_mode"] else "blue"
        page.update()

    mode_switch = ft.Switch(value=True, on_change=toggle_private_mode, active_color="grey")
    mode_text = ft.Text("나만 보기 (기본)", color="grey", size=12)

    # Layout Components
    mic_icon = ft.Icon(ft.Icons.MIC, size=40, color="white")
    mic_container = ft.Container(
        content=mic_icon,
        width=80, height=80,
        bgcolor="#00C73C",
        border_radius=40,
        alignment=ft.alignment.center,
        on_click=toggle_rec,
        shadow=ft.BoxShadow(blur_radius=10, color="#00C73C"),
        ink=True,
        tooltip="음성 녹음 시작"
    )

    # 업로드 버튼 (백업용)
    upload_btn = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.UPLOAD_FILE, color="grey", size=20),
            ft.Text("파일 업로드", size=10, color="grey")
        ], spacing=2, horizontal_alignment="center"),
        on_click=pick_file_click,
        padding=10,
        border_radius=10,
        tooltip="음성 파일 업로드 (mp3, wav, m4a)"
    )

    header = AppHeader(
        title_text="음성 메모",
        on_back_click=lambda _: navigate_to("home"),
        action_button=ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=AppColors.TEXT_SECONDARY),
                ft.Text("Audio:2일 / Text:15일", style=AppTextStyles.CAPTION)
            ], spacing=2),
            padding=ft.padding.only(right=10)
        )
    )

    controls_area = ft.Container(
        content=ft.Column([
            ft.Row([mode_switch, mode_text], alignment="center"),
            ft.Row([mic_container, upload_btn], alignment="center", vertical_alignment="center", spacing=20),
            status_text
        ], horizontal_alignment="center", spacing=10),
        padding=20, bgcolor="#F8F9FA", border_radius=ft.border_radius.only(top_left=30, top_right=30)
    )

    load_memos()
    return [
        ft.Container(
            expand=True, bgcolor="white",
            padding=ft.padding.only(top=50),
            content=ft.Column([
                header,
                ft.Container(memo_list_view, expand=True, padding=20),
                controls_area
            ], spacing=0)
        )
    ]
