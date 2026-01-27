import os
import shutil
import subprocess
import datetime
from pathlib import Path

# Dependency Check
try:
    from PIL import Image, ImageOps
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("WARNING: Pillow (PIL) not found. Image compression disabled.")

def is_ffmpeg_available():
    return shutil.which("ffmpeg") is not None

def compress_file(file_path: str) -> str:
    """
    Analyzes and compresses file if necessary.
    Returns: Path to compressed file (temp) or original path if no compression needed.
    """
    if not os.path.exists(file_path):
        return file_path

    ext = os.path.splitext(file_path)[1].lower()
    
    # 1. Image Compression
    if ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']:
        return compress_image(file_path)
    
    # 2. Video Compression
    elif ext in ['.mp4', '.mov', '.avi', '.mkv']:
        return compress_video(file_path)
        
    return file_path

def compress_image(file_path: str, max_width=1280, quality=80) -> str:
    if not HAS_PIL: return file_path
    
    try:
        file_size = os.path.getsize(file_path)
        # If smaller than 500KB, skip
        if file_size < 500 * 1024:
            return file_path

        img = Image.open(file_path)
        
        # Handle Orientation (EXIF)
        img = ImageOps.exif_transpose(img)
        
        # Resize
        w, h = img.size
        if w > max_width:
            ratio = max_width / w
            new_h = int(h * ratio)
            img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)
        
        # Save to Temp
        temp_dir = os.path.join(os.getcwd(), "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime('%H%M%S')
        new_filename = f"comp_{timestamp}_{os.path.basename(file_path)}"
        new_filename = os.path.splitext(new_filename)[0] + ".jpg" # Force JPEG
        
        output_path = os.path.join(temp_dir, new_filename)
        
        # Save as JPEG (optimized)
        # Convert RGBA to RGB if needed
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        img.save(output_path, "JPEG", quality=quality, optimize=True)
        
        # Check if we actually saved space
        new_size = os.path.getsize(output_path)
        if new_size >= file_size:
            # Compression didn't help (already optimized), return original
            os.remove(output_path)
            return file_path
            
        print(f"Compressed Image: {file_size/1024:.1f}KB -> {new_size/1024:.1f}KB")
        return output_path
        
    except Exception as e:
        print(f"Image Compression Error: {e}")
        return file_path

def compress_video(file_path: str) -> str:
    if not is_ffmpeg_available():
        # Fallback: Check size limit
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 100:
            print("WARNING: Large video file detected (>100MB) and ffmpeg not available.")
        return file_path
        
    try:
        temp_dir = os.path.join(os.getcwd(), "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime('%H%M%S')
        new_filename = f"comp_{timestamp}_{os.path.basename(file_path)}"
        output_path = os.path.join(temp_dir, new_filename)
        
        # FFmpeg Command (KakaoTalk-ish settings)
        # CRF 28 (Good compression), Preset faster (Speed), AAC audio
        cmd = [
            "ffmpeg", "-i", file_path,
            "-vcodec", "libx264", "-crf", "28", "-preset", "faster",
            "-acodec", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            "-y", # Overwrite
            output_path
        ]
        
        # Run process
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result.returncode == 0 and os.path.exists(output_path):
            old_size = os.path.getsize(file_path)
            new_size = os.path.getsize(output_path)
            print(f"Compressed Video: {old_size/1024/1024:.1f}MB -> {new_size/1024/1024:.1f}MB")
            
            if new_size < old_size:
                return output_path
            else:
                os.remove(output_path)
                return file_path
        else:
            print(f"FFmpeg failed: {result.stderr.decode('utf-8')}")
            return file_path
            
    except Exception as e:
        print(f"Video Compression Error: {e}")
        return file_path
