import sys
import time
import subprocess
import os

# Files to monitor
WATCH_EXTS = ['.py', '.env']
# Command to run
CMD = [sys.executable, 'main.py']

def get_mtimes():
    """Get modification times of all watched files."""
    mtimes = {}
    for root, dirs, files in os.walk('.'):
        # Skip hidden dirs like .git or .gemini
        if any(part.startswith('.') for part in root.split(os.sep)):
            continue
            
        for f in files:
            if any(f.endswith(ext) for ext in WATCH_EXTS):
                path = os.path.join(root, f)
                try:
                    mtimes[path] = os.path.getmtime(path)
                except OSError:
                    pass
    return mtimes

def main():
    print(f"👀 Starting Hot-Reload Watcher for {CMD}...")
    print("   (Edit any .py file to restart the app automatically)")
    
    proc = subprocess.Popen(CMD)
    last_mtimes = get_mtimes()

    try:
        while True:
            time.sleep(1)
            current_mtimes = get_mtimes()
            changed = False
            
            # Check for changes
            for path, mtime in current_mtimes.items():
                if path not in last_mtimes or last_mtimes[path] != mtime:
                    changed = True
                    print(f"\n⚡ File changed: {path}")
                    break
            
            # Update known files (in case new files added)
            if len(current_mtimes) != len(last_mtimes):
                changed = True
            
            if changed:
                print("♻️  Restarting app...")
                # Kill existing process
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                
                # Start new process
                proc = subprocess.Popen(CMD)
                last_mtimes = current_mtimes
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping Watcher...")
        if proc.poll() is None:
            proc.terminate()

if __name__ == "__main__":
    main()
