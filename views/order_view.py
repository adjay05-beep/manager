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
    # [FIX] Pure JS Recorder Approach
    # We remove page.audio_recorder dependency because it fails in Remote Native App scenario.
    # We will use purely Javascript via page.run_javascript to Init/Start/Stop/Upload.
    
    # Inject JS Code for Recorder
    # This script defines functions in global window scope for Python to call.
    recorder_script = """
    window.audioChunks = [];
    window.mediaRecorder = null;
    
    window.startRecordingJS = async function() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            window.mediaRecorder = new MediaRecorder(stream);
            window.audioChunks = [];
            
            window.mediaRecorder.ondataavailable = event => {
                window.audioChunks.push(event.data);
            };
            
            window.mediaRecorder.start();
            return "STARTED";
        } catch (err) {
            return "ERROR: " + err;
        }
    };
    
    window.stopRecordingAndUploadJS = async function(uploadUrl) {
        return new Promise((resolve, reject) => {
            if (!window.mediaRecorder) { resolve("NO_RECORDER"); return; }
            
            window.mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(window.audioChunks, { type: 'audio/wav' });
                try {
                    const resp = await fetch(uploadUrl, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'audio/wav' },
                        body: audioBlob
                    });
                    if (resp.ok) resolve("UPLOAD_OK");
                    else resolve("UPLOAD_FAIL: " + resp.status);
                } catch (e) {
                    resolve("UPLOAD_ERR: " + e);
                }
                
                // Cleanup tracks
                window.mediaRecorder.stream.getTracks().forEach(track => track.stop());
                window.mediaRecorder = null;
            };
            
            window.mediaRecorder.stop();
        });
    };
    """
    # Inject script once
    page.run_javascript(recorder_script)

    state = {"is_recording": False, "memos": [], "seconds": 0, "edit_id": None}
    
    # UI Components
    memo_list_view = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
    status_text = ft.Text("버튼을 눌러 녹음을 시작하세요", color="grey", size=14)
    recording_timer = ft.Text("00:00", size=32, weight="bold", color="black", visible=False)
    
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

    # Upload & Transcribe Logic
    voice_up_url = ft.Text("", visible=False)
    def on_voice_uploaded(e):
        if voice_up_url.value:
            status_text.value = "AI 변환 중..."
            status_text.color = "blue"
            page.update()
            page.run_task(lambda: start_transcription(voice_up_url.value))
    
    voice_done_btn = ft.IconButton(ft.Icons.CHECK, on_click=on_voice_uploaded, visible=False)

    def toggle_rec(e):
        if not state["is_recording"]:
            # START RECORDING (JS)
            state["is_recording"] = True
            state["seconds"] = 0
            status_text.value = "녹음 준비 (JS Mode)..."
            recording_timer.visible = True
            page.update()

            def upd():
                while state["is_recording"]:
                    time.sleep(1); state["seconds"] += 1
                    mins, secs = divmod(state["seconds"], 60); recording_timer.value = f"{mins:02d}:{secs:02d}"; page.update()
            threading.Thread(target=upd, daemon=True).start()

            # Trigger JS Start
            page.run_javascript("window.startRecordingJS().then(res => console.log(res));")
            status_text.value = "녹음 중..."
            page.update()

        else:
            # STOP RECORDING (JS)
            state["is_recording"] = False
            status_text.value = "서버 전송 중..."
            recording_timer.visible = False
            page.update()
            
            # Generate Signed URL for Upload
            fname = f"voice_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
            signed_url = get_storage_signed_url(fname)
            public_url = get_public_url(fname)
            
            # Check Flet App compatibility: JS might not return value to Python directly via run_javascript return.
            # We use a trick: JS sets a hidden field value if we had one.
            # Or simpler: Just fire and forget, and assume it works.
            # But the User wants feedback.
            # Better: "window.stopRecordingAndUploadJS" handles upload. We just Alert result in JS.
            
            js_stop = f"""
            window.stopRecordingAndUploadJS('{signed_url}').then(res => {{
                if (res.startsWith('UPLOAD_OK')) {{
                    alert('녹음 전송 완료!');
                    // Note: We can't easily callback Python from here without a hidden button click.
                    // But we can just rely on the user seeing the alert.
                }} else {{
                    alert('전송 실패: ' + res);
                }}
            }});
            """
            page.run_javascript(js_stop)
            
            # We assume success and queue transcription
            # This is optimistic UI.
            page.run_task(lambda: delayed_transcribe(public_url))

    async def delayed_transcribe(url):
        await asyncio.sleep(2)
        await start_transcription(url)

    async def start_transcription(url):
        try:
            status_text.value = "AI 분석 중..."
            page.update()
            t = await asyncio.to_thread(lambda: audio_service.transcribe_audio(url))
            if t:
                await memo_service.save_transcription(t)
                status_text.value = "완료!"
                await load_memos_async()
            else:
                status_text.value = "인식 실패 (무음)"
        except Exception as ex:
            status_text.value = f"AI Err: {ex}"
        finally:
            page.update()

    # Layout
    mic_btn = ft.Container(content=ft.Icon(ft.Icons.MIC, size=40, color="white"), width=80, height=80, bgcolor="#00C73C", border_radius=40, alignment=ft.alignment.center, on_click=toggle_rec, shadow=ft.BoxShadow(blur_radius=10, color="#00C73C"), ink=True)
    
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
        voice_done_btn,
        ft.Container(expand=True, bgcolor="white", padding=ft.padding.only(top=50), content=ft.Column([header, ft.Container(memo_list_view, expand=True, padding=20), ft.Container(content=ft.Column([status_text, recording_timer, mic_btn, ft.Container(height=10)], horizontal_alignment="center", spacing=10), padding=20, bgcolor="#F8F9FA", border_radius=ft.border_radius.only(top_left=30, top_right=30))], spacing=0))
    ]
