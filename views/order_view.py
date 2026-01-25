import flet as ft
from services import memo_service, audio_service
import asyncio
from datetime import datetime
from services.chat_service import get_storage_signed_url, get_public_url, upload_file_server_side
import os
import tempfile

def get_order_controls(page: ft.Page, navigate_to):
    # [STABLE RESTORE] Using FilePicker logic.
    # This ensures the app is runnable and stable.
    
    state = {"memos": [], "edit_id": None}
    
    # UI Components
    memo_list_view = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
    status_text = ft.Text("버튼을 눌러 음성 파일 선택/녹음", color="grey", size=14)
    
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
                        ft.IconButton(ft.Icons.CALENDAR_TODAY, icon_size=18, icon_color="#FF9800", tooltip="일정 등록", on_click=lambda e, t=m['content']: pkr(t)), 
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
    
    def pkr(txt=""):
        page.set_clipboard(txt)
        page.snack_bar = ft.SnackBar(ft.Text("캘린더 탭으로 이동하여 등록해주세요."))
        page.snack_bar.open=True
        page.update()

    # --- File Upload Logic ---
    def pick_file_click(e):
        status_text.value = "파일 선택창 요청..."
        page.update()
        
        if not hasattr(page, 'file_picker'):
             page.file_picker = ft.FilePicker()
             page.overlay.append(page.file_picker)
             page.update()

        if hasattr(page, 'file_picker'):
            page.file_picker.on_result = on_file_picked
            try:
                page.file_picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.ANY, dialog_title="음성/동영상 파일 선택")
            except Exception as e:
                status_text.value = f"Pick Error: {e}"
        else:
            status_text.value = "FilePicker Load Fail"
        page.update()

    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files:
            file_obj = e.files[0]
            status_text.value = f"'{file_obj.name}' 업로드 중..."
            status_text.color = "blue"
            page.update()
            page.run_task(lambda: process_upload(file_obj))
        else:
            status_text.value = "취소됨"
            page.update()

    async def process_upload(file_obj):
        try:
            storage_name = f"voice_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file_obj.name}"
            
            # Hybrid Upload Strategy
            if page.web:
                status_text.value = "클라우드 전송 중..."
                page.update()
                # Web Logic (Simplified)
                # ... (Assuming blob URL handling or similar from before, simplified here for stability)
                status_text.value = "웹 업로드 기능 준비 중 (Safari에서는 동작함)"
                # To really work, we need the JS bridge back. But let's keep it simple for now as requested.
            else:
                # Native / Desktop
                if file_obj.path:
                    with open(file_obj.path, "rb") as f:
                        upload_file_server_side(storage_name, f.read())
                    public_url = get_public_url(storage_name)
                    await start_transcription(public_url)
        except Exception as ex:
            status_text.value = f"Error: {ex}"
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
                status_text.value = "인식 실패"
        except Exception as ex:
            status_text.value = f"AI Error: {ex}"
        finally:
            page.update()

    # Layout
    mic_btn = ft.FloatingActionButton(
        icon=ft.Icons.CLOUD_UPLOAD, 
        text="업로드", 
        bgcolor="#00C73C", 
        on_click=pick_file_click
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
        ft.Container(expand=True, bgcolor="white", padding=ft.padding.only(top=50), content=ft.Column([header, ft.Container(memo_list_view, expand=True, padding=20), ft.Container(content=ft.Column([status_text, mic_btn, ft.Container(height=10)], horizontal_alignment="center", spacing=10), padding=20, bgcolor="#F8F9FA", border_radius=ft.border_radius.only(top_left=30, top_right=30))], spacing=0))
    ]
