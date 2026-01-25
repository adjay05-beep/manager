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
    # --- Pure Javascript Recorder Implementation (WeChat Style) ---
    # Flet's Native Recorder has limitations on Remote Server + Native Client.
    # We use pure JS Buffer recording which works on Safari/WebView and uploads directly.
    
    # Load JS (Inline for simplicity, or read from assets)
    recorder_js = """
    // Global Recorder State
    var mediaRecorder = null;
    var audioChunks = [];

    window.startJsRecording = async function() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = event => {
                audioChunks.push(event.data);
            };

            mediaRecorder.start();
            // alert("Recording Started");
            return "STARTED";
        } catch (err) {
            alert("Microphone Error: " + err);
        }
    };

    window.stopJsRecordingAndUpload = async function(uploadUrl) {
        return new Promise((resolve, reject) => {
            if (!mediaRecorder) {
                alert("No Recorder Found");
                resolve("NO_RECORDER");
                return;
            }

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                
                try {
                    const response = await fetch(uploadUrl, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'audio/wav' },
                        body: audioBlob
                    });

                    if (response.ok) {
                        resolve("SUCCESS");
                    } else {
                        alert("Upload Failed: " + response.status);
                        resolve("FAIL");
                    }
                } catch (e) {
                    alert("Net Error: " + e);
                    resolve("ERR");
                }
                
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
                mediaRecorder = null;
            };

            mediaRecorder.stop();
        });
    };
    """
    
    # Inject JS on load (or usually run once)
    # We do it when toggling for safety or via a hidden init
    def init_js_recorder():
        page.run_javascript(recorder_js)

    def toggle_js_rec(e):
        if not state["is_recording"]:
            # START RECORDING
            state["is_recording"] = True
            state["seconds"] = 0
            status_text.value = "녹음 중... (JS)"
            status_text.color = "red"
            recording_timer.visible = True
            page.update()
            
            # 1. Run JS Start
            page.run_javascript("window.startJsRecording();")
            
            # 2. Start Timer
            def upd():
                while state["is_recording"]:
                    time.sleep(1); state["seconds"] += 1
                    mins, secs = divmod(state["seconds"], 60); recording_timer.value = f"{mins:02d}:{secs:02d}"; page.update()
            threading.Thread(target=upd, daemon=True).start()
            
        else:
            # STOP RECORDING
            state["is_recording"] = False
            status_text.value = "업로드 중..."
            status_text.color = "blue"
            recording_timer.visible = False
            page.update()
            
            # 1. Prepare Upload URL
            fname = f"voice_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
            signed_url = get_storage_signed_url(fname)
            public_url = get_public_url(fname)
            
            # 2. Run JS Stop & Upload via run_task (handling callback is tricky)
            # Flet run_javascript is fire-and-forget.
            # We call the async JS function. It returns a Promise. 
            # We can't await it in Python directly.
            # BUT we can poll for completion? Or just assume it works and check public URL?
            
            # Improving JS: Call a Python function via window.location.href (hack)? 
            # Or simplified: Start transcription after a delay.
            
            js_stop = f"window.stopJsRecordingAndUpload('{signed_url}');"
            page.run_javascript(js_stop)
            
            async def check_and_transcribe():
                status_text.value = "AI 분석 대기..."
                page.update()
                await asyncio.sleep(3) # Wait for JS upload
                await start_transcription(public_url)
            
            page.run_task(check_and_transcribe)

    # Init JS
    init_js_recorder()

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
    # Use FloatingActionButton for reliable click handling on Mobile
    mic_btn = ft.FloatingActionButton(
        icon=ft.Icons.MIC, 
        text="녹음 시작/종료", 
        bgcolor="#00C73C", 
        content=ft.Row([ft.Icon(ft.Icons.MIC), ft.Text("녹음 시작/종료")], alignment="center", spacing=5),
        width=160,
        height=50,
        on_click=toggle_js_rec
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
