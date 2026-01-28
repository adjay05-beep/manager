import os
import datetime
from services.chat_service import get_storage_signed_url, get_public_url, upload_file_server_side
from db import service_supabase
import flet as ft
from utils.logger import log_info

# [NEW] Unified Storage Service to remove duplication in Views.

def handle_file_upload(is_web: bool, file_obj, status_callback=None, picker_ref: ft.FilePicker=None):
    """
    Handles file upload for both Web (Bridge/SignedURL) and Native (Direct Read).
    Returns: Dict with keys 'type', 'public_url', 'storage_name'
    """
    try:
        log_info(f"DEBUG: Upload Start. Web={is_web}, Name={file_obj.name}")
        # 1. Generate Storage Name
        import uuid
        # [FIX] Use UUID to prevent URL encoding issues with Korean/Special characters
        ext = os.path.splitext(file_obj.name)[1] if file_obj.name else ""
        if not ext: ext = ".bin"
        storage_name = f"{uuid.uuid4()}{ext}"
        log_info(f"DEBUG: Generated Name={storage_name}")
        
        if status_callback: status_callback("1/4. 업로드 준비 중...")
        
        # 2. Check Environment
        # is_web is passed directly
        
        if is_web:
            if status_callback: status_callback("보안 서버(Proxy)로 전송 중...")
            
            # [FIX] Proxy Upload: Browser -> Flet Server -> Supabase
            # This bypasses Client-Side CORS/Signature issues.
            try:
                raw_url = picker_ref.page.get_upload_url(storage_name, 600)
                log_info(f"DEBUG: Internal Upload URL: {raw_url}")
                if status_callback: status_callback(f"생성된 URL 확인 중...")
                
                # [FIX] Convert to Relative URL to handle Render/Cloud Load Balancers
                # Flet usually generates absolute URL with internal IP (e.g., http://0.0.0.0:10000/upload/...)
                # which is unreachable from the outside.
                # We strip the domain to let the browser use the current correct origin.
                import urllib.parse
                parsed = urllib.parse.urlparse(raw_url)
                upload_url = parsed.path
                if parsed.query:
                    upload_url += f"?{parsed.query}"
                
                log_info(f"DEBUG: Relativized Upload URL: {upload_url}")
                if status_callback: status_callback(f"전송 경로 최적화 완료")
                    
            except Exception as e:
                log_info(f"Proxy URL Error: {e}")
                # Fallback to direct upload attempt if proxy fails (unlikely)
                raise e

            if picker_ref:
                picker_ref.upload(
                    files=[
                        ft.FilePickerUploadFile(
                            name=file_obj.name,
                            upload_url=upload_url,
                            method="PUT"
                        )
                    ]
                )
                log_info("DEBUG: Browser Upload Triggered (PUT)")
                return {
                    "type": "proxy_upload_triggered",
                    "storage_name": storage_name,
                    "public_url": None
                }
            
            return {"type": "error", "error": "No picker ref for proxy upload"}

        else:
            # Native / Desktop
            if status_callback: status_callback("최적화(압축) 진행 중...")
            
            if file_obj.path:
                final_path = file_obj.path
                is_temp = False
                
                try:
                    # [COMPRESSION STEP]
                    if status_callback: status_callback("2/4. 최적화(압축) 진행 중...")
                    
                    try:
                        from services.compression_service import compress_file
                        compressed_path = compress_file(file_obj.path)
                    except Exception as comp_ex:
                        print(f"Confirmation: Compression Service Failed {comp_ex}")
                        compressed_path = file_obj.path
                    
                    # [STRICT POLICY] - Temporarily Relaxed for Debugging
                    # If file is large (>2MB) and compression returned original (failed), abort.
                    file_size = os.path.getsize(file_obj.path)
                    if compressed_path == file_obj.path and file_size > 50 * 1024 * 1024: # 50MB Limit
                         pass 
                         
                    final_path = compressed_path
                    is_temp = (final_path != file_obj.path)

                    if status_callback: status_callback("3/4. 보안 서버로 전송 중...")
                    
                    with open(final_path, "rb") as f:
                        file_data = f.read()
                        print(f"Upload Start: {len(file_data)} bytes")
                        
                        # Use updated call with content_type if available (Need to update chat_service next)
                        import mimetypes
                        ctype, _ = mimetypes.guess_type(final_path)
                        if not ctype: ctype = "application/octet-stream"
                        
                        # [TODO] Update chat_service.py to accept content_type
                        upload_file_server_side(storage_name, file_data, content_type=ctype)
                        
                finally:
                    # Cleanup Temp
                    if is_temp and os.path.exists(final_path):
                        try:
                            os.remove(final_path)
                        except: pass

                # [FIX] Use Signed URL (10 years) to bypass Private Bucket restrictions
                # Public URL returns 403 if bucket is not set to Public
                try:
                    # 10 years expiration
                    signed_res = service_supabase.storage.from_("uploads").create_signed_url(storage_name, 60*60*24*365*10)
                    # Handle key variations
                    final_url = signed_res.get('signedURL') or signed_res.get('signedUrl') or signed_res.get('url')
                except Exception as sign_ex:
                    print(f"Signed URL Gen Error: {sign_ex} - Fallback to Public")
                    final_url = get_public_url(storage_name)

                return {
                    "type": "native_url",
                    "public_url": final_url,
                    "storage_name": storage_name
                }
            else:
                # Should not happen on Native unless permission denied
                raise Exception("파일 경로를 찾을 수 없습니다.")

    except Exception as ex:
        print(f"Upload Handle Error: {ex}")
        if status_callback: status_callback(f"오류 발생: {ex}")
        return {"type": "error", "error": str(ex)}

def upload_proxy_file_to_supabase(storage_name: str) -> str:
    """
    Called after Flet receives the file in 'uploads/' directory.
    Reads it and uploads to Supabase using Service Key.
    Returns the final display URL (Signed).
    """
    local_path = os.path.join("uploads", storage_name)
    if not os.path.exists(local_path):
        # Retry with just filename (sometimes Flet might not use subdir if config issue)
        if os.path.exists(storage_name):
            local_path = storage_name
        else:
            raise Exception(f"Server File Not Found: {local_path}")
            
    try:
        # 1. Read File
        with open(local_path, "rb") as f:
            file_data = f.read()
            
        # 2. Upload to Supabase (Server-Side)
        import mimetypes
        ctype, _ = mimetypes.guess_type(local_path)
        
        # [FIX] Robust MIME detection for Windows
        if not ctype:
            ext_lower = os.path.splitext(local_path)[1].lower()
            if ext_lower == ".mov": ctype = "video/quicktime"
            elif ext_lower == ".mp4": ctype = "video/mp4"
            else: ctype = "application/octet-stream"
            
        # Fallback for known issue where guess_type returns video/quicktime but Supabase prefers video/mp4 for some reason?
        # Actually video/quicktime is standard for MOV.
        
        from utils.logger import log_info
        log_info(f"DEBUG: Proxy Uploading {storage_name}, Size: {len(file_data)} bytes, Type: {ctype}")
        
        upload_file_server_side(storage_name, file_data, content_type=ctype)
        
        # 3. Generate Signed URL
        # 10 years expiration
        res = service_supabase.storage.from_("uploads").create_signed_url(storage_name, 60*60*24*365*10)
        final_url = res.get('signedURL') or res.get('signedUrl') or res.get('url')
        
        return final_url

    except Exception as e:
        print(f"Storage Service Error: {e}")
        raise e
        
    finally:
        # 4. Cleanup Local File
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except: pass
