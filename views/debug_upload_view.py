import flet as ft
import datetime
import traceback
from services import storage_service

def DebugUploadView(page: ft.Page):
    log_control = ft.Column(scroll=ft.ScrollMode.ALWAYS, height=400)
    
    def log(msg):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
        log_control.controls.append(ft.Text(line, size=12, font_family="Consolas"))
        page.update()

    def on_upload_result(e: ft.FilePickerResultEvent):
        if not e.files: return
        f = e.files[0]
        log(f"File selected: {f.name} ({f.path})")
        
        # Determine Web Mode (Safe Capture)
        is_web = page.web
        log(f"Environment: Web={is_web}")

        def status_callback(msg):
            log(f"STATUS: {msg}")

        # Run in Thread to emulate real scenario
        import threading
        def _target():
            log("Thread started.")
            try:
                log("Calling storage_service.handle_file_upload...")
                result = storage_service.handle_file_upload(
                    is_web=is_web,
                    file_obj=f,
                    status_callback=status_callback
                )
                log(f"Result: {result}")
            except Exception as ex:
                log(f"CRITICAL ERROR: {ex}")
                log(traceback.format_exc())
            finally:
                log("Thread finished.")

        threading.Thread(target=_target, daemon=True).start()

    picker = ft.FilePicker(on_result=on_upload_result)
    page.overlay.append(picker)
    page.update()

    return ft.View(
        "/debug_upload",
        [
            ft.AppBar(title=ft.Text("Upload Diagnostic"), bgcolor="red"),
            ft.ElevatedButton("Select File to Test", on_click=lambda _: picker.pick_files()),
            ft.Container(
                content=log_control,
                border=ft.border.all(1, "grey"),
                padding=10,
                expand=True
            )
        ]
    )
