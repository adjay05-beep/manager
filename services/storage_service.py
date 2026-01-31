import os
from repositories.storage_repository import StorageRepository
import flet as ft
from utils.logger import log_info, log_error

# [PROFESSIONAL] Refactored to use Repository Pattern

def handle_file_upload(is_web: bool, file_obj, status_callback=None, picker_ref: ft.FilePicker=None):
    """
    Handles file upload for both Web and Native.
    """
    try:
        import uuid
        ext = os.path.splitext(file_obj.name)[1] if file_obj.name else ""
        storage_name = f"{uuid.uuid4()}{ext or '.bin'}"
        
        if status_callback: status_callback("1/4. 업로드 준비 중...")
        
        if is_web:
            # Web Proxy Upload logic (stays in service for now as it involves Flet picker)
            upload_url = picker_ref.page.get_upload_url(storage_name, 600)
            import urllib.parse
            upload_url = urllib.parse.urlparse(upload_url).path
            
            if picker_ref:
                picker_ref.upload(files=[ft.FilePickerUploadFile(name=file_obj.name, upload_url=upload_url, method="PUT")])
                return {"type": "proxy_upload_triggered", "storage_name": storage_name, "public_url": None}
            return {"type": "error", "error": "No picker ref"}

        else:
            # Native / Desktop
            if status_callback: status_callback("2/4. 최적화 진행 중...")
            from services.compression_service import compress_file
            final_path = compress_file(file_obj.path)
            
            if status_callback: status_callback("3/4. 보안 서버로 전송 중...")
            with open(final_path, "rb") as f:
                import mimetypes
                ctype = mimetypes.guess_type(final_path)[0] or "application/octet-stream"
                StorageRepository.upload_file("uploads", storage_name, f.read(), ctype)

            final_url = StorageRepository.get_public_url("uploads", storage_name)
            return {"type": "native_url", "public_url": final_url, "storage_name": storage_name}

    except Exception as ex:
        log_error(f"Upload Handle Error: {ex}")
        if status_callback: status_callback(f"오류 발생: {ex}")
        return {"type": "error", "error": str(ex)}

def upload_proxy_file_to_supabase(storage_name: str) -> str:
    """Post-proxy upload processing."""
    local_path = os.path.join("uploads", storage_name)
    if not os.path.exists(local_path): raise Exception(f"File Not Found: {local_path}")
            
    try:
        with open(local_path, "rb") as f:
            import mimetypes
            ctype = mimetypes.guess_type(local_path)[0] or "application/octet-stream"
            StorageRepository.upload_file("uploads", storage_name, f.read(), ctype)
        
        return StorageRepository.get_public_url("uploads", storage_name)
    except Exception as e:
        log_error(f"Storage Service Error: {e}")
        raise e
    finally:
        if os.path.exists(local_path): os.remove(local_path)
