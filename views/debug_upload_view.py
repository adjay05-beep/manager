import flet as ft
import datetime
import asyncio
import traceback
from services import storage_service

async def DebugUploadView(page: ft.Page):
    try:
        log_control = ft.Column(scroll=ft.ScrollMode.ALWAYS, height=400)
        
        def log(msg):
            try:
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                line = f"[{timestamp}] {msg}"
                print(line)
                log_control.controls.append(ft.Text(line, size=12, font_family="Consolas"))
                page.update()
            except Exception:
                pass  # UI update failed

        def on_upload_result(e: ft.ControlEvent):
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
            async def _target():
                log("Async Task started.")
                try:
                    log("Calling storage_service.handle_file_upload...")
                    result = await asyncio.to_thread(lambda: storage_service.handle_file_upload(
                        is_web=is_web,
                        file_obj=f,
                        status_callback=status_callback,
                        picker_ref=picker
                    ))
                    log(f"Result: {result}")
                except Exception as ex:
                    log(f"CRITICAL ERROR: {ex}")
                    log(traceback.format_exc())
                finally:
                    log("Async Task finished.")

            asyncio.create_task(_target())

        async def check_disk_write(e):
            import os, uuid
            log("--- Checking Disk Write Permissions ---")
            try:
                test_name = f"test_{uuid.uuid4()}.txt"
                path = os.path.join("uploads", test_name)
                
                # 1. Create Folder if missing
                if not await asyncio.to_thread(os.path.exists, "uploads"):
                    log("Creating 'uploads' directory...")
                    await asyncio.to_thread(os.makedirs, "uploads", exist_ok=True)
                
                # 2. Write
                log(f"Writing to {path}...")
                def write_test_file():
                    with open(path, "w") as f:
                        f.write("test_content")
                await asyncio.to_thread(write_test_file)
                
                # 3. Read
                log("Reading back...")
                def read_test_file():
                    with open(path, "r") as f:
                        return f.read()
                content = await asyncio.to_thread(read_test_file)
                    
                if content == "test_content":
                    log("SUCCESS: Disk Write/Read OK")
                else:
                    log(f"FAILURE: Content mismatch ({content})")
                    
                # 4. Delete
                log("Deleting test file...")
                await asyncio.to_thread(os.remove, path)
                log("SUCCESS: Delete OK")
                
            except Exception as ex:
                log(f"DISK ERROR: {ex}")
                log(traceback.format_exc())

        async def check_supabase_connect(e):
            log("--- Checking Supabase Network ---")
            try:
                from db import service_supabase
                log("Calling storage.from_('uploads').list()...")
                # Try listing files in 'uploads' bucket to verify connection
                res = await asyncio.to_thread(lambda: service_supabase.storage.from_("uploads").list())
                log(f"SUCCESS: Connected. Files found: {len(res)}")
            except Exception as ex:
                log(f"NETWORK ERROR: {ex}")
                log(traceback.format_exc())

        async def load_server_logs(e):
            from utils.logger import get_logs
            logs = get_logs()
            log_control.controls.clear()
            log("--- SYSTEM LOGS REFRESHED ---")
            for l in logs:
                color = "red" if "ERROR" in l else "blue" if "INFO" in l else "black"
                log_control.controls.append(ft.Text(str(l), size=12, font_family="Consolas", color=color))
            page.update()

        def list_upload_folder(e):
            import os
            log("--- LISTING 'uploads/' ---")
            if os.path.exists("uploads"):
                files = os.listdir("uploads")
                for f in files:
                    try:
                        size = os.path.getsize(os.path.join("uploads", f))
                        log(f"- {f} ({size} bytes)")
                    except OSError as os_err:
                        log(f"- {f} (Error reading size: {os_err})")
                if not files: log("(Empty)")
            else:
                log("ERROR: 'uploads/' directory does not exist!")

        # [Flet 0.80+] FilePicker disabled temporarily
        picker = None

        def try_pick_files(e):
            log("FilePicker disabled in Flet 0.80 - use alternative upload method")

        # Auto-load logs on entry
        load_server_logs(None)

        return [
            ft.Text("시스템 진단 & 로그", size=24, weight="bold"),
            ft.Text("AI 분석 실패 원인을 여기서 확인하세요.", size=12, color="grey"),
            ft.Divider(),
            ft.Row([
                ft.ElevatedButton("새로 고침 (로그)", on_click=lambda e: asyncio.create_task(load_server_logs(e)), bgcolor="blue", color="white", icon=ft.Icons.REFRESH),
                ft.ElevatedButton("파일 업로드 테스트 (비활성)", on_click=try_pick_files, disabled=True),
                ft.ElevatedButton("Disk Write Test", on_click=lambda e: asyncio.create_task(check_disk_write(e))),
                ft.ElevatedButton("Supabase Check", on_click=lambda e: asyncio.create_task(check_supabase_connect(e))),
            ], wrap=True),
            ft.Container(height=10),
            ft.Container(height=20),
            ft.Text("실시간 로그:", weight="bold"),
            ft.Container(
                content=log_control,
                bgcolor="#FAFAFA",
                border=ft.border.all(1, "#E0E0E0"),
                padding=10,
                border_radius=5,
                height=400
            )
        ]
    except Exception as e:
        return [ft.Text(f"Error loading debug view: {e}", color="red")]
