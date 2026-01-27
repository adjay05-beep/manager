import os
import datetime
from services.chat_service import get_storage_signed_url, get_public_url, upload_file_server_side
import flet as ft

# [NEW] Unified Storage Service to remove duplication in Views.

async def handle_file_upload(page: ft.Page, file_obj: ft.FilePickerFile, status_callback=None, picker_ref: ft.FilePicker=None):
    """
    Handles file upload for both Web (Bridge/SignedURL) and Native (Direct Read).
    Returns: Dict with keys 'type', 'public_url', 'storage_name'
    """
    try:
        # 1. Generate Storage Name
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        storage_name = f"upload_{timestamp}_{file_obj.name}"
        
        if status_callback: status_callback("업로드 준비 중...")
        
        # 2. Check Environment
        is_web = page.web
        
        if is_web:
            if status_callback: status_callback("클라우드로 전송 중 (Web)...")
            
            signed_url = get_storage_signed_url(storage_name)
            public_url = get_public_url(storage_name)
            
            if picker_ref:
                # Execute Flet's internal Web Upload logic
                picker_ref.upload(
                    files=[
                        ft.FilePickerUploadFile(
                            name=file_obj.name,
                            upload_url=signed_url,
                            method="PUT"
                        )
                    ]
                )
                return {
                    "type": "web_upload_triggered",
                    "public_url": public_url,
                    "storage_name": storage_name
                }
            
            # Fallback if no picker provided
            return {
                "type": "web_js",
                "signed_url": signed_url,
                "public_url": public_url,
                "storage_name": storage_name
            }

        else:
            # Native / Desktop
            if status_callback: status_callback("최적화(압축) 진행 중...")
            
            if file_obj.path:
                final_path = file_obj.path
                is_temp = False
                
                try:
                    # [COMPRESSION STEP]
                    from services.compression_service import compress_file
                    compressed_path = compress_file(file_obj.path)
                    
                    if compressed_path != file_obj.path:
                        final_path = compressed_path
                        is_temp = True
                        if status_callback: status_callback("서버로 전송 중...")
                    
                    with open(final_path, "rb") as f:
                        upload_file_server_side(storage_name, f.read())
                        
                finally:
                    # Cleanup Temp
                    if is_temp and os.path.exists(final_path):
                        try:
                            os.remove(final_path)
                        except: pass

                return {
                    "type": "native_url",
                    "public_url": get_public_url(storage_name),
                    "storage_name": storage_name
                }
            else:
                # Should not happen on Native unless permission denied
                raise Exception("파일 경로를 찾을 수 없습니다.")

    except Exception as e:
        print(f"Storage Service Error: {e}")
        raise e
