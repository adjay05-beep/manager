import flet as ft
from services import memo_service, audio_service
import asyncio
from datetime import datetime
from services.chat_service import get_storage_signed_url, get_public_url, upload_file_server_side
import os

def get_order_controls(page: ft.Page, navigate_to):
    # Singleton Recorder Safety
    # [FIX] Rely on Main.py global instance to prevent overlay race/freeze
    audio_recorder = getattr(page, "audio_recorder", None)
    if not audio_recorder:
        return [ft.Text("Error: Global Recorder not found", color="red")]

    state = {
        "is_recording": False, 
        "memos": [], 
        "edit_id": None
    }
    
    # UI Components
    memo_list_view = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
    status_text = ft.Text("녹음 버튼을 눌러 시작하세요", color="grey", size=14)
    
    # [RBAC] Get User from Session
    current_user_id = page.session.get("user_id")
    if not current_user_id:
        pass # Fallback

    def load_memos():
        page.run_task(load_memos_async)

    async def load_memos_async():
        if not current_user_id: return
        try:
            state["memos"] = await memo_service.get_memos(current_user_id)
            render_memos()
        except Exception as e:
            # page.snack_bar = ft.SnackBar(ft.Text(f"메모 로드 실패: {e}"), bgcolor="red")
            # page.snack_bar.open = True
            # page.update()
            # Suppress generic load errors to avoid annoying popups if just empty
            print(f"Memo Load Error: {e}")

    def render_memos():
        memo_list_view.controls.clear()
        
        if not state["memos"]:
            memo_list_view.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.NOTE_ADD, size=40, color="#EEEEEE"),
                        ft.Text("첫 번째 음성 메모를 남겨보세요!", color="grey")
                    ], horizontal_alignment="center"),
                    alignment=ft.alignment.center,
                    padding=40
                )
            )
        else:
            for memo in state["memos"]:
                # Content Layout
                c = memo.get("content", "")
                date_str = memo.get("created_at", "")[:16].replace("T", " ")
                
                card_content = ft.Column([
                    ft.Text(date_str, size=10, color="grey"),
                    ft.Text(c, size=14, color="#333333", selectable=True),
                ], spacing=5)
                
                # Delete Button
                btn_del = ft.IconButton(
                    ft.Icons.CLOSE, icon_size=16, icon_color="#BDBDBD",
                    on_click=lambda e, mid=memo['id']: delete_memo(mid)
                )
                
                item = ft.Container(
                    content=ft.Row([card_content, btn_del], alignment="spaceBetween", vertical_alignment="start"),
                    bgcolor="white",
                    border_radius=10,
                    padding=15,
                    border=ft.border.all(1, "#F5F5F5"),
                    shadow=ft.BoxShadow(blur_radius=5, color="#05000000")
                )
                memo_list_view.controls.append(item)
        
        page.update()

    def delete_memo(mid):
        async def _del():
            await memo_service.delete_memo(mid)
            await load_memos_async()
            page.snack_bar = ft.SnackBar(ft.Text("삭제되었습니다."))
            page.snack_bar.open=True
            page.update()
        page.run_task(_del)

    def delete_all_memos():
        page.run_task(lambda: _del_all_async())
    async def _del_all_async():
        if not current_user_id: return
        await memo_service.delete_all_memos(current_user_id)
        await load_memos_async()
        page.snack_bar = ft.SnackBar(ft.Text("모든 메모가 삭제되었습니다.")); page.snack_bar.open = True; page.update()

    async def start_transcription(url):
        try:
            status_text.value = "AI 분석 중..."
            page.update()
            
            # Use audio_service
            t = await asyncio.to_thread(lambda: audio_service.transcribe_audio(url))
            
            if t:
                if current_user_id:
                     await memo_service.save_transcription(t, current_user_id)
                status_text.value = "완료!"
                status_text.color = "green"
                await load_memos_async()
            else:
                status_text.value = "인식 실패"
        except Exception as ex:
            status_text.value = f"AI Error: {ex}"
        finally:
            page.update()

    # Recorder Logic
    async def stop_recording():
        try:
            res = await audio_recorder.stop_recording_async()
            if res:
                print(f"Recording stopped, file: {res}")
                # Transcribe
                await start_transcription(res)
            state["is_recording"] = False
            update_mic_ui()
        except Exception as e:
            status_text.value = f"Stop Error: {e}"
            page.update()

    async def start_recording():
        try:
            if audio_recorder.is_recording(): # If already recording
                await stop_recording()
                return

            state["is_recording"] = True
            update_mic_ui()
            
            # Simple timestamped filename
            fname = f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            # It seems Flet AudioRecorder manages path automatically if not provided or provided? 
            # Safest is to let Flet handle it or provide standard temp path.
            # Let's try default (no args) or minimal config.
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

    # File Picker Logic
    def pick_file_click(e):
        page.chat_file_picker.pick_files(allow_multiple=False, allowed_extensions=["mp3", "wav", "m4a"])
    
    async def on_picker_result(e: ft.FilePickerResultEvent):
        if e.files:
            f = e.files[0]
            status_text.value = "파일 업로드 및 분석 중..."
            page.update()
            
            try:
                # 1. Upload to Server (storage_service/chat_service helper)
                # But transcribe_audio needs a URL or Path.
                # If we are on web, we must upload. If desktop, path works.
                # We can reuse storage_service.handle_file_upload or chat_service helpers.
                # Let's use the unified `storage_service` if possible, or `upload_file_server_side`
                
                # For now, simplest path:
                # Use `chat_service.upload_file_server_side` but that requires logic.
                from services import storage_service
                 
                def progress(msg):
                    status_text.value = msg
                    page.update()

                res = await storage_service.handle_file_upload(page, f, progress, picker_ref=page.chat_file_picker)
                
                if res.get("public_url"):
                     await start_transcription(res["public_url"])
                elif res.get("path"): # Desktop local path
                     await start_transcription(res["path"])
                else:
                     status_text.value = "업로드 실패"
                     page.update()

            except Exception as ex:
                status_text.value = f"Upload Error: {ex}"
                page.update()

    # Assign picker callback safely
    page.chat_file_picker.on_result = lambda e: page.run_task(lambda: on_picker_result(e))

    # Layout
    mic_icon = ft.Icon(ft.Icons.MIC, size=40, color="white")
    mic_container = ft.Container(
        content=mic_icon, width=80, height=80, bgcolor="#00C73C", border_radius=40, 
        alignment=ft.alignment.center, on_click=toggle_rec, shadow=ft.BoxShadow(blur_radius=10, color="#00C73C"), ink=True
    )
    
    upload_btn = ft.Container(
        content=ft.Column([ft.Icon(ft.Icons.UPLOAD_FILE, color="grey"), ft.Text("업로드", size=10, color="grey")], spacing=0, alignment="center"),
        on_click=pick_file_click, padding=10
    )
    
    header = ft.Container(
        content=ft.Row([
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to("home")), 
                ft.Text("음성 메모", size=20, weight="bold")
            ]), 
            ft.Row([
                ft.IconButton(ft.Icons.DELETE_SWEEP, tooltip="전체 삭제", icon_color="red", on_click=lambda e: delete_all_memos())
            ])
        ], alignment="spaceBetween"), 
        padding=10, 
        border=ft.border.only(bottom=ft.border.BorderSide(1, "#EEEEEE"))
    )
    
    load_memos()
    return [
        ft.Container(expand=True, bgcolor="white", padding=ft.padding.only(top=50), content=ft.Column([header, ft.Container(memo_list_view, expand=True, padding=20), ft.Container(content=ft.Column([status_text, ft.Row([mic_container, upload_btn], alignment="center", vertical_alignment="center", spacing=20), ft.Container(height=10)], horizontal_alignment="center", spacing=10), padding=20, bgcolor="#F8F9FA", border_radius=ft.border_radius.only(top_left=30, top_right=30))], spacing=0))
    ]
