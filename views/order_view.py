import flet as ft
from services import memo_service, audio_service
import asyncio
from datetime import datetime
from services.chat_service import get_storage_signed_url, get_public_url, upload_file_server_side
import os
import time
import tempfile

def get_order_controls(page: ft.Page, navigate_to):
    # [FIX] WeChat-style Stable Voice Memo
    # Uses Global Singleton Recorder. NO THREADS. Minimal UI updates.
    
    if hasattr(page, "audio_recorder"):
        audio_recorder = page.audio_recorder
    else:
        # Fallback (should not happen if main.py is correct)
        audio_recorder = ft.AudioRecorder()
        page.overlay.append(audio_recorder)

    state = {"is_recording": False, "memos": [], "edit_id": None}
    
    # UI Components
    memo_list_view = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
    status_text = ft.Text("녹음 버튼을 눌러 시작하세요", color="grey", size=14)
    
    # No Timer Thread to prevent freeze
    # recording_timer = ft.Text("00:00", ...) -> Removed
    
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
                        # Calendar button preserved
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
        page.snack_bar = ft.SnackBar(ft.Text("캘린더 탭으로 이동하여 등록해주세요. (내용 복사됨)"))
        page.snack_bar.open=True
        page.update()

    # --- WeChat Style Logic ---
    def toggle_rec(e):
        if not state["is_recording"]:
            # START
            state["is_recording"] = True
            mic_icon.icon = ft.Icons.STOP
            mic_container.bgcolor = "red"
            status_text.value = "녹음 중... (버튼을 눌러 종료)"
            status_text.color = "red"
            page.update()

            is_browser = page.web
            try:
                if is_browser:
                    audio_recorder.start_recording(None)
                else:
                    path = os.path.join(tempfile.gettempdir(), f"voice_{int(time.time())}.wav")
                    audio_recorder.start_recording(path)
            except Exception as ex:
                reset_ui()
                status_text.value = f"Start Error: {ex}"
                page.update()
        else:
            # STOP
            reset_ui()
            status_text.value = "저장 및 변환 중..."
            page.update()
            
            try:
                res = audio_recorder.stop_recording()
                if not res:
                    status_text.value = "녹음 데이터 없음 (권한 확인)"
                    page.update()
                    return
                
                handle_upload(res)
            except Exception as ex:
                status_text.value = f"Stop Error: {ex}"
                page.update()

    def reset_ui():
        state["is_recording"] = False
        mic_icon.icon = ft.Icons.MIC
        mic_container.bgcolor = "#00C73C"
        status_text.value = "대기 중"
        status_text.color = "grey"
        # page.update() # Called by caller

    def handle_upload(local_path):
        fname = f"voice_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
        
        # Web Check
        if page.web:
            signed_url = get_storage_signed_url(fname)
            public_url = get_public_url(fname)
            
            js = f"""
            (async function() {{
                try {{
                    const res = await fetch("{local_path}");
                    const blob = await res.blob();
                    const up = await fetch("{signed_url}", {{
                        method: "PUT",
                        headers: {{ "Content-Type": "audio/wav" }},
                        body: blob
                    }});
                }} catch (e) {{ console.log(e); }}
            }})();
            """
            page.run_javascript(js)
            page.run_task(lambda: delayed_transcribe(public_url))
        else:
            # Native
            if os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    upload_file_server_side(fname, f.read())
                public_url = get_public_url(fname)
                page.run_task(lambda: start_transcription(public_url))
            else:
                status_text.value = "파일 없음 (Safari 권장)"
                page.update()

    async def delayed_transcribe(url):
        await asyncio.sleep(2) # Wait for upload
        await start_transcription(url)

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
            status_text.value = f"AI Error: {ex}"
        finally:
            page.update()

    # Layout
    mic_icon = ft.Icon(ft.Icons.MIC, size=40, color="white")
    mic_container = ft.Container(
        content=mic_icon, 
        width=80, height=80, 
        bgcolor="#00C73C", 
        border_radius=40, 
        alignment=ft.alignment.center, 
        on_click=toggle_rec, 
        shadow=ft.BoxShadow(blur_radius=10, color="#00C73C"), 
        ink=True
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
    # Bottom Bar Layout
    return [
        ft.Container(expand=True, bgcolor="white", padding=ft.padding.only(top=50), content=ft.Column([header, ft.Container(memo_list_view, expand=True, padding=20), ft.Container(content=ft.Column([status_text, mic_container, ft.Container(height=10)], horizontal_alignment="center", spacing=10), padding=20, bgcolor="#F8F9FA", border_radius=ft.border_radius.only(top_left=30, top_right=30))], spacing=0))
    ]
