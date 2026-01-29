import flet as ft
from services import voice_service, audio_service
import asyncio
from datetime import datetime
import os

def get_voice_controls(page: ft.Page, navigate_to):
    import warnings
    # Suppress Flet Deprecation Warning for AudioRecorder
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    # Singleton Recorder Safety
    audio_recorder = getattr(page, "audio_recorder", None)
    if not audio_recorder:
        # Try to find it in overlay just in case
        for ctrl in page.overlay:
             if "AudioRecorder" in str(type(ctrl)):
                 audio_recorder = ctrl
                 break
    
    if not audio_recorder:
        return [ft.Text("오디오 녹음 기능을 초기화할 수 없습니다. (AudioRecorder Not Found)", color="red")]

    state = {
        "is_recording": False, 
        "memos": [], 
        "edit_id": None,
        "is_private_mode": True # Default to Private
    }
    
    # [RBAC] Get Context
    current_user_id = page.session.get("user_id")
    channel_id = page.session.get("channel_id")
    
    if not current_user_id:
        return [ft.Text("Please login first.", color="red")]

    # UI Components
    memo_list_view = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
    status_text = ft.Text("녹음 버튼을 눌러 시작하세요", color="grey", size=14)
    
    # Toggle for Private/Public View
    def on_mode_change(e):
        # This toggle filters the VIEW, but potentially we show mixed view with icons?
        # Plan says: "Private First: UI clearly distinguishes personal space."
        # Maybe we show list with icons.
        # Let's keep it simple: Show ALL available to me (Private + Public Channel)
        # And use chips to filter if needed.
        pass

    def load_memos():
        page.run_task(load_memos_async)

    async def load_memos_async():
        status_text.value = "로딩 중..."
        page.update()
        try:
            # Trigger Background Cleanup (Fire and Forget)
            page.run_task(voice_service.voice_service.cleanup_expired_memos)
            
            # Fetch all available memos (Private + Channel Public)
            state["memos"] = await voice_service.voice_service.get_memos(current_user_id, channel_id)
            render_memos()
            status_text.value = "대기 중"
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
                
                # Check expiration imminent?
                # For MVP just show icons.
                
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
                
                # Actions
                actions = []
                
                # Share Button (Only for private memos)
                if is_private and channel_id:
                    actions.append(
                        ft.IconButton(
                            ft.Icons.IOS_SHARE, icon_size=18, tooltip="매장 공유 (공개 전환)", icon_color="blue",
                            on_click=lambda e, mid=memo['id']: share_memo(mid)
                        )
                    )
                
                # Share to Calendar (Placeholder for now, or link?)
                # actions.append(ft.IconButton(ft.Icons.CALENDAR_MONTH, icon_size=18, tooltip="캘린더 등록", on_click=lambda e: print("Cal")))

                # Delete Button
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
            page.snack_bar.open=True
            await load_memos_async()
        page.run_task(_share)

    def delete_memo(mid):
        async def _del():
            await voice_service.voice_service.delete_memo(mid)
            await load_memos_async()
            page.snack_bar = ft.SnackBar(ft.Text("삭제되었습니다."))
            page.snack_bar.open=True
            page.update()
        page.run_task(_del)

    # Transcription & Saving
    async def process_recording(url_or_path):
        try:
            status_text.value = "AI 분석 및 저장 중..."
            page.update()
            
            # 1. Transcribe
            text = await asyncio.to_thread(lambda: audio_service.transcribe_audio(url_or_path))
            if not text: text = "(음성 인식 실패)"
            
            # 2. Upload if local path (Desktop) to get a persistent URL?
            # Creating memo with audio_url.
            # If `url_or_path` is local path, we need to upload it to Supabase Storage to keep it for 2 days.
            # If `url_or_path` is already a public URL (Web upload), we use it.
            
            final_url = None
            if "blob:" in url_or_path or "http" in url_or_path:
                final_url = url_or_path # Already uploaded case (Web) if signed url
                # Wait, for Web, on_picker_result uploads it.
                # But for MIC recording on Web, it's a blob. We can't easily upload blob without JS.
                # Flet AudioRecorder on Web returns blob? 
                # Currently AudioRecorder on Web is tricky. Assuming Desktop usage mostly or verified Web.
                pass
            else:
                 # Desktop Local File -> Upload
                 # We need to upload this to Supabase to share/store.
                 try:
                     from services import storage_service
                     # We need to act as a FilePicker file object? No, strict path.
                     # We need a helper to upload local path.
                     # storage_service.handle... expects FilePickerEventObject or similar.
                     # Let's use `chat_service.upload_file_server_side` directly.
                     
                     fname = f"voice_{current_user_id}_{int(datetime.now().timestamp())}.wav"
                     with open(url_or_path, "rb") as f:
                        file_bytes = f.read()
                        
                     from services.chat_service import upload_file_server_side, get_public_url
                     # We can reuse chat bucket or new 'voice-memos' bucket?
                     # Let's use 'chat-uploads' for MVP simplicity or 'avatars'?
                     # Let's use 'chat-uploads'.
                     
                     path_on_storage = f"voice/{fname}"
                     upload_file_server_side("chat-uploads", path_on_storage, file_bytes, "audio/wav")
                     final_url = get_public_url("chat-uploads", path_on_storage)
                     
                 except Exception as up_err:
                     print(f"Audio Upload Error: {up_err}")
                     # Save without audio url
            
            # 3. Create Memo (Private Default)
            await voice_service.voice_service.create_memo(
                user_id=current_user_id,
                content=text,
                channel_id=channel_id,
                is_private=state["is_private_mode"],
                audio_url=final_url
            )
            
            status_text.value = "저장 완료"
            await load_memos_async()
            
        except Exception as ex:
            status_text.value = f"Error: {ex}"
            page.update()

    # Recorder Handlers
    async def stop_recording():
        try:
            res = await audio_recorder.stop_recording_async()
            state["is_recording"] = False
            update_mic_ui()
            if res:
                await process_recording(res)
        except Exception as e:
            status_text.value = f"Stop Error: {e}"
            page.update()

    async def start_recording():
        try:
            if state["is_recording"]: return
            
            state["is_recording"] = True
            update_mic_ui()
            
            fname = f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            await audio_recorder.start_recording_async(output_path=fname) 
            status_text.value = "녹음 중... (클릭하여 중지)"
            status_text.color = "red"
            page.update()
        except Exception as e:
            state["is_recording"] = False
            update_mic_ui()
            status_text.value = f"Start Error: {e}"
            page.update()

    def toggle_rec(e):
        if state["is_recording"]:
            page.run_task(stop_recording)
        else:
            page.run_task(start_recording)

    def update_mic_ui():
        mic_icon.name = ft.Icons.STOP if state["is_recording"] else ft.Icons.MIC
        mic_icon.color = "white"
        mic_container.bgcolor = "red" if state["is_recording"] else "#00C73C"
        mic_container.update()

    # File Picker (Upload)
    def pick_file_click(e):
        page.chat_file_picker.pick_files(allow_multiple=False, allowed_extensions=["mp3", "wav", "m4a"])
    
    async def on_picker_result(e: ft.FilePickerResultEvent):
        if e.files:
            f = e.files[0]
            status_text.value = "업로드 및 분석 중..."
            page.update()
            try:
                from services import storage_service
                def progress(msg): status_text.value = msg; page.update()
                
                # Upload
                # [FIX] Ensure picker_ref is passed for Web Upload
                # [FIX] Pass page.web boolean, not page object
                # [FIX] Run sync upload in thread to avoid blocking/TypeError
                res = await asyncio.to_thread(
                    storage_service.handle_file_upload, 
                    page.web, 
                    f, 
                    progress, 
                    picker_ref=page.chat_file_picker
                )
                public_url = res.get("public_url")
                
                if public_url:
                     # Transcribe & Save
                     # For uploaded files, use the URL
                     text = await asyncio.to_thread(lambda: audio_service.transcribe_audio(public_url))
                     if not text: text = "(파일 분석 실패)"
                     
                     await voice_service.voice_service.create_memo(
                        user_id=current_user_id,
                        content=text,
                        channel_id=channel_id,
                        is_private=state["is_private_mode"],
                        audio_url=public_url
                     )
                     status_text.value = "업로드 저장 완료"
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
    mic_icon = ft.Icon(ft.Icons.MIC, size=40, color="#0A1929")
    mic_container = ft.Container(
        content=mic_icon, width=80, height=80, bgcolor="#00C73C", border_radius=40, 
        alignment=ft.alignment.center, on_click=toggle_rec, shadow=ft.BoxShadow(blur_radius=10, color="#00C73C"), ink=True
    )
    
    upload_btn = ft.Container(
        content=ft.Column([ft.Icon(ft.Icons.UPLOAD_FILE, color="grey"), ft.Text("업로드", size=10, color="grey")], spacing=0, alignment="center"),
        on_click=pick_file_click, padding=10
    )
    
    # Imports moved to top

    # ... (Previous imports kept if possible)

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
