import flet as ft
import datetime
import traceback
from services import storage_service

def DebugUploadView(page: ft.Page):
    try:
        log_control = ft.Column(scroll=ft.ScrollMode.ALWAYS, height=400)
        
        def log(msg):
            try:
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                line = f"[{timestamp}] {msg}"
                print(line)
                log_control.controls.append(ft.Text(line, size=12, font_family="Consolas"))
                page.update()
            except: pass

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
                        status_callback=status_callback,
                        picker_ref=picker
                    )
                    log(f"Result: {result}")
                except Exception as ex:
                    log(f"CRITICAL ERROR: {ex}")
                    log(traceback.format_exc())
                finally:
                    log("Thread finished.")

            threading.Thread(target=_target, daemon=True).start()

        def check_disk_write(e):
            import os, uuid
            log("--- Checking Disk Write Permissions ---")
            try:
                test_name = f"test_{uuid.uuid4()}.txt"
                path = os.path.join("uploads", test_name)
                
                # 1. Create Folder if missing
                if not os.path.exists("uploads"):
                    log("Creating 'uploads' directory...")
                    os.makedirs("uploads", exist_ok=True)
                
                # 2. Write
                log(f"Writing to {path}...")
                with open(path, "w") as f:
                    f.write("test_content")
                
                # 3. Read
                log("Reading back...")
                with open(path, "r") as f:
                    content = f.read()
                    
                if content == "test_content":
                    log("SUCCESS: Disk Write/Read OK")
                else:
                    log(f"FAILURE: Content mismatch ({content})")
                    
                # 4. Delete
                log("Deleting test file...")
                os.remove(path)
                log("SUCCESS: Delete OK")
                
            except Exception as ex:
                log(f"DISK ERROR: {ex}")
                log(traceback.format_exc())

        def check_supabase_connect(e):
            log("--- Checking Supabase Network ---")
            try:
                from db import service_supabase
                log("Calling list_buckets()...")
                res = service_supabase.storage.list_buckets()
                log(f"SUCCESS: Connected. Buckets Found: {len(res) if res else 0}")
            except Exception as ex:
                log(f"NETWORK ERROR: {ex}")

        picker = ft.FilePicker(on_result=on_upload_result)
        page.overlay.append(picker)
        # [FIX] Do not call page.update() here. Let main.py do it.
        
        return [
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.BUG_REPORT, color="red"),
                        ft.Text("Upload Diagnostic", size=20, weight="bold", color="red")
                    ]),
                    ft.ElevatedButton("Select File to Test", on_click=lambda _: picker.pick_files()),
                    ft.Row([
                        ft.ElevatedButton("Server Disk Write Test", on_click=check_disk_write, bgcolor="blue", color="white"),
                        ft.ElevatedButton("Supabase Connection Test", on_click=check_supabase_connect, bgcolor="green", color="white"),
                    ], spacing=10),
                    ft.Container(
                        content=log_control,
                        border=ft.border.all(1, "grey"),
                        padding=10,
                        expand=True,
                        height=400 # Explicit height
                    )
                ]),
                expand=True,
                padding=20,
                bgcolor="white"
            )
        ]
    except Exception as e:
        return [ft.Text(f"Error loading debug view: {e}", color="red")]
