"""
Server Launcher with Auto Browser Open
서버 시작 후 자동으로 새 브라우저 창을 엽니다.
"""
import subprocess
import time
import webbrowser
import sys
import os

def kill_existing_server():
    """기존 서버 프로세스 종료"""
    try:
        # Windows에서 포트 8555를 사용하는 프로세스 찾기
        result = subprocess.run(
            'netstat -ano | findstr :8555',
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            pids = set()
            for line in lines:
                parts = line.split()
                if len(parts) >= 5 and 'LISTENING' in line:
                    pid = parts[-1]
                    pids.add(pid)
            
            for pid in pids:
                print(f"🔪 Killing existing server (PID: {pid})...")
                subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                time.sleep(0.5)
                
    except Exception as e:
        print(f"⚠️ Could not kill existing process: {e}")

def main():
    print("=" * 60)
    print("🚀 The Manager - Server Launcher")
    print("=" * 60)
    
    # 1. 기존 서버 종료
    kill_existing_server()
    
    # 2. 서버 시작
    print("\n📦 Starting server...")
    
    # 백그라운드에서 서버 실행 (콘솔 창 숨김)
    if sys.platform == 'win32':
        # Windows - hide console window
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        process = subprocess.Popen(
            ['python', 'main.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo
        )
    else:
        # Unix/Linux/Mac
        process = subprocess.Popen(
            ['python', 'main.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    
    # 3. 서버가 준비될 때까지 대기
    print("⏳ Waiting for server to start...")
    time.sleep(3)
    
    # 4. 새 브라우저 창 열기
    url = "http://localhost:8555"
    
    print(f"\n🌐 Opening browser: {url}")
    webbrowser.open_new(url)  # 새 창으로 열기
    
    print("\n" + "=" * 60)
    print("✅ Server is running!")
    print("📍 URL: http://localhost:8555")
    print("🔄 Cache-busting URL opened in new browser window")
    print("⚠️  Press Ctrl+C in the server console to stop")
    print("=" * 60)
    
    # 서버 프로세스는 별도 콘솔에서 계속 실행됨

if __name__ == "__main__":
    main()
