import flet as ft
from services import memo_service, audio_service
import asyncio
from datetime import datetime
from services.chat_service import get_storage_signed_url, get_public_url, upload_file_server_side
import os
import time
import tempfile

def get_order_controls(page: ft.Page, navigate_to):
    # [RESTORE] Hybrid Mode:
    # 1. Start/Stop Recording (WeChat Style) - Works on Web(Safari) & Desktop
    # 2. File Upload Button - Backup for Native App
    
    # Singleton Recorder Safety
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
            page.snack_bar = ft.SnackBar(ft.Text(f"메모 로드 실패: {e}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

# ... (render_memos skipped) ...

    def delete_all_memos():
        page.run_task(lambda: _del_all_async())
    async def _del_all_async():
        if not current_user_id: return
        await memo_service.delete_all_memos(current_user_id)
        await load_memos_async()
        page.snack_bar = ft.SnackBar(ft.Text("모든 메모가 삭제되었습니다.")); page.snack_bar.open = True; page.update()

# ... (processing skipped) ...

    async def start_transcription(url):
        try:
            status_text.value = "AI 분석 중..."
            page.update()
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
