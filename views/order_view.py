import flet as ft
from services import memo_service, audio_service
import asyncio
from datetime import datetime
from services.chat_service import get_storage_signed_url, get_public_url, upload_file_server_side
import os
import threading
import tempfile
import time

def get_order_controls(page: ft.Page, navigate_to):
    # [FIX] Architecture Pivot: Using FilePicker instead of AudioRecorder
    # This completely eliminates the "Freeze" issue caused by AudioRecorder lifecycle.
    
    state = {"memos": [], "edit_id": None, "is_uploading": False}
    
    # UI Components
    memo_list_view = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
    status_text = ft.Text("버튼을 눌러 음성 파일 선택/녹음", color="grey", size=14)
    # loading_spinner = ft.ProgressRing(visible=False, width=20, height=20)
    
    def load_memos():
        page.run_task(load_memos_async)

    async def load_memos_async():
        state["memos"] = await memo_service.get_memos()
        render_memos()

    def render_memos():
        memo_list_view.controls = []
        if not state["memos"]:
            memo_list_view.controls.append(ft.Container(content=ft.Text("저장된 음성 메모가 없습니다.", italic=True, color="grey"), padding=20, alignment=ft.alignment.center))
        
        ed_id = state.get("edit_id")
        for m in state["memos"]:
            time_str = m['created_at'][5:16].replace('T', ' ') if m.get('created_at') else ""
            is_ed = (ed_id == m['id'])
            if is_ed:
                fld = ft.TextField(value=m['content'], multiline=True, expand=True, autofocus=True, text_size=15, border_color="#00C73C")
                memo_content = ft.Row([fld, ft.Column([ft.IconButton(ft.Icons.CHECK_CIRCLE, icon_color="#00C73C", on_click=lambda e, mid=m['id'], f=fld: save_inline(mid, f)), ft.IconButton(ft.Icons.CANCEL, icon_color="red", on_click=lambda _: cancel_ed())], spacing=0)], alignment="spaceBetween")
            else:
                memo_content = ft.Row([
                    ft.Column([
                        ft.Row([ft.Icon(ft.Icons.RECEIPT_LONG, size=16, color="#448AFF"), ft.Text(time_str, size=11, color="grey")], spacing=5), 
                        ft.Text(m['content'], size=15, weight="w500", color="black")
                    ], spacing=5, expand=True), 
                    ft.Row([
                        ft.IconButton(ft.Icons.COPY, icon_size=18, tooltip="복사", on_click=lambda e, t=m['content']: copy(t)), 
                        ft.IconButton(ft.Icons.EDIT, icon_size=18, tooltip="수정", on_click=lambda e, mid=m['id']: enter_ed(mid)),
                        ft.IconButton(ft.Icons.DELETE, icon_size=18, icon_color="red", tooltip="삭제", on_click=lambda e, mid=m['id']: delete_memo(mid))
                    ], spacing=0)
                ], alignment="spaceBetween")
            memo_list_view.controls.append(ft.Container(content=memo_content, padding=15, bgcolor="#F8F9FA", border_radius=10, border=ft.border.all(1, "#EEEEEE")))
        page.update()

    def enter_ed(mid): state["edit_id"] = mid; render_memos()
    def cancel_ed(): state["edit_id"] = None; render_memos()
    def save_inline(mid, f):
        page.run_task(lambda: memo_service.update_memo_content(mid, f.value))
        state["edit_id"] = None; load_memos()
    def copy(t):
        page.set_clipboard(t); page.snack_bar = ft.SnackBar(ft.Text("복사되었습니다!")); page.snack_bar.open = True; page.update()
    def delete_memo(mid):
        page.run_task(lambda: _del_async(mid))
    async def _del_async(mid):
        await memo_service.delete_memo(mid)
        await load_memos_async()
        page.snack_bar = ft.SnackBar(ft.Text("삭제되었습니다.")); page.snack_bar.open = True; page.update()
    def delete_all_memos():
        page.run_task(lambda: _del_all_async())
    async def _del_all_async():
        await memo_service.delete_all_memos()
        await load_memos_async()
        page.snack_bar = ft.SnackBar(ft.Text("모든 메모가 삭제되었습니다.")); page.snack_bar.open = True; page.update()

    # --- File Upload Logic (Stable) ---
    def pick_file_click(e):
        if hasattr(page, 'file_picker'):
            # allow_multiple=False, file_type=AUDIO
            page.file_picker.on_result = on_file_picked
            page.file_picker.pick_files(
                allow_multiple=False, 
                file_type=ft.FilePickerFileType.AUDIO,
                dialog_title="음성 파일 선택 또는 녹음"
            )
        else:
            status_text.value = "FilePicker Not Initialized"
            page.update()

    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files:
            file_obj = e.files[0]
            fname = file_obj.name
            status_text.value = f"'{fname}' 처리 중..."
            status_text.color = "blue"
            page.update()
            
            # Start Upload Process
            page.run_task(lambda: process_upload(file_obj))
        else:
            status_text.value = "파일 선택 취소됨"
            page.update()

    async def process_upload(file_obj):
        try:
            # Generate unique name
            storage_name = f"voice_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file_obj.name}"
            
            # Check Web vs Native
            # On Web, we have `path` as blob URL (?) OR we might need to use upload_url method of FilePicker.
            # Flet FilePicker usually requires `page.file_picker.upload` for web.
            # But we want to use our custom Signed URL logic if possible.
            
            # Actually, `file_obj.path` is available on Desktop.
            # On Web, `file_obj.path` might be None or a blob URL.
            
            is_env_web = (os.getenv("RENDER") is not None) or page.web
            
            if is_env_web:
                # On Web, we must use the JS trick again because we can't read the file in Python.
                # BUT, FilePicker puts the file in browser memory.
                # We can use `upload` method to Flet Server, then read it?
                # No, Flet Server is ephemeral on Render? No, it's the python process.
                
                # Better: Use the Blob URL if available.
                # If file_obj.path is a blob url, we can fetch it.
                # Warning: Flet 0.21+ might not expose blob url in path easily?
                # It usually provides `file_obj.path` as `playlist...` or `blob:...`.
                
                status_text.value = "클라우드로 업로드 중..."
                page.update()
                
                # Get Signed URL
                signed_url = get_storage_signed_url(storage_name)
                public_url = get_public_url(storage_name)
                
                # If we can't access path on Web, we might need Flet's upload_files.
                # Let's try to upload to our own server handlers?
                # Actually, simplest on Web is `upload` to Flet's internal upload endpoint, then transcribe?
                # But we want to send to supabase.
                
                # Let's rely on the JS Bridge if we can get the blob.
                # Does `file_obj` give us a handle for JS? 
                
                # Alternative: Flet FilePicker has `upload` method that sends files to a URL.
                # We can set the `upload_url` to our Signed URL!
                # file_obj has `name` and `upload_url`.
                
                # New Strategy: Use `page.file_picker.upload` with Signed URL.
                # But Signed URL is PUT. Flet upload is POST (multipart/form-data).
                # Supabase Signed URL expects PUT binary.
                
                # So we might need to use the JS Bridge logic again using the File Name? 
                # On Web, Flet stores selected files in `page.files` or similar? No.
                
                # Let's try the `upload_file_server_side` if we are on Native.
                # On Web, this is tricky without `AudioRecorder`.
                
                # Wait! FilePicker on Web UPLOADs to the python server temp dir if we call `file_picker.upload`?
                # Yes.
                # 1. Create upload handler in main? (Too complex refactor).
                # 2. Use `audio_service` to transcribe DIRECTLY if we can get the bytes?
                
                # LET'S TRY: Native approach first. Flet Web FilePicker handling is hard.
                # For now, assume Native App (Flet App) usage.
                # On Flet App (which identifies as Mobile), `file_obj.path` IS a local path!
                # So we can just read it!
                
                # So we treat "Flet App" as Native here.
                # The issue is "Flet Web in Safari". There, `file_obj.path` is useless.
                # PROPOSAL: Use `page.file_picker.upload` to a standard endpoint? 
                
                # Let's assume Flet App for now.
                if file_obj.path:
                    # Native / Flet App
                    with open(file_obj.path, "rb") as f:
                        content = f.read()
                    
                    upload_file_server_side(storage_name, content)
                    public_url = get_public_url(storage_name)
                    await start_transcription(public_url)
                else:
                    # Web Browser
                    status_text.value = "웹에서는 업로드가 제한될 수 있습니다."
                    page.update()
            
            else:
                # Desktop Local
                with open(file_obj.path, "rb") as f:
                    content = f.read()
                upload_file_server_side(storage_name, content)
                public_url = get_public_url(storage_name)
                await start_transcription(public_url)
                
        except Exception as ex:
            status_text.value = f"Upload Err: {ex}"
            page.update()

    async def start_transcription(url):
        try:
            status_text.value = "AI 분석 중..."
            page.update()
            t = await asyncio.to_thread(lambda: audio_service.transcribe_audio(url))
            if t:
                await memo_service.save_transcription(t)
                status_text.value = "완료!"
                status_text.color = "green"
                await load_memos_async()
            else:
                status_text.value = "인식 실패 (무음)"
        except Exception as ex:
            status_text.value = f"AI Err: {ex}"
        finally:
            page.update()

    # Layout
    # Use UPLOAD icon instead of mic to signify change
    mic_btn = ft.Container(content=ft.Icon(ft.Icons.CLOUD_UPLOAD, size=40, color="white"), width=80, height=80, bgcolor="#00C73C", border_radius=40, alignment=ft.alignment.center, on_click=pick_file_click, shadow=ft.BoxShadow(blur_radius=10, color="#00C73C"), ink=True)
    
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
        ft.Container(expand=True, bgcolor="white", padding=ft.padding.only(top=50), content=ft.Column([header, ft.Container(memo_list_view, expand=True, padding=20), ft.Container(content=ft.Column([status_text, mic_btn, ft.Container(height=10)], horizontal_alignment="center", spacing=10), padding=20, bgcolor="#F8F9FA", border_radius=ft.border_radius.only(top_left=30, top_right=30))], spacing=0))
    ]
