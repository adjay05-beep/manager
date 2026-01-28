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
                log("Calling storage.from_('uploads').list()...")
                # Try listing files in 'uploads' bucket to verify connection
                res = service_supabase.storage.from_("uploads").list()
                log(f"SUCCESS: Connected. Files found: {len(res)}")
            except Exception as ex:
                log(f"NETWORK ERROR: {ex}")
                log(traceback.format_exc())

        def load_server_logs(e):
            from utils.logger import get_logs
            logs = get_logs()
            log("--- SERVER LOGS START ---")
            for l in logs:
                log_control.controls.append(ft.Text(str(l), size=12, font_family="Consolas", color="green"))
            log("--- SERVER LOGS END ---")
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
                    except:
                        log(f"- {f} (Error reading size)")
                if not files: log("(Empty)")
            else:
                log("ERROR: 'uploads/' directory does not exist!")

        picker = ft.FilePicker(on_result=on_upload_result)
        page.overlay.append(picker)
        # [FIX] Do not call page.update() here. Let main.py do it.
        
        return [
            ft.Text("디버그 업로드 도구", size=24, weight="bold"),
            ft.Text("강력한 로그 추적 기능이 포함되어 있습니다.", size=12, color="grey"),
            ft.Divider(),
            ft.Row([
                ft.ElevatedButton("파일 선택 및 테스트 업로드", on_click=lambda _: picker.pick_files(), bgcolor="blue", color="white"),
                ft.ElevatedButton("서버 디스크 쓰기 테스트", on_click=check_disk_write),
                ft.ElevatedButton("Supabase 연결 테스트", on_click=check_supabase_connect),
            ], wrap=True),
            ft.Row([
                ft.ElevatedButton("📜 서버 로그 불러오기", on_click=load_server_logs, bgcolor="#424242", color="white"),
                ft.ElevatedButton("📂 업로드 폴더 목록 확인", on_click=list_upload_folder, bgcolor="#424242", color="white"),
            ], wrap=True),
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
