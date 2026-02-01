import os
import sys
import socket
import importlib.util
from dotenv import load_dotenv

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def print_status(message, status="INFO"):
    if status == "OK":
        print(f"[{GREEN}OK{RESET}] {message}")
    elif status == "FAIL":
        print(f"[{RED}FAIL{RESET}] {message}")
    elif status == "WARN":
        print(f"[{YELLOW}WARN{RESET}] {message}")
    else:
        print(f"[INFO] {message}")

def check_env_vars():
    print("\n--- Checking Environment Variables ---")
    load_dotenv()
    required_vars = ["SUPABASE_URL", "SUPABASE_KEY", "FLET_SECRET_KEY"]
    all_present = True
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            print_status(f"{var} is missing!", "FAIL")
            all_present = False
        else:
            # Mask key for security in logs
            masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "****"
            print_status(f"{var} is set ({masked})", "OK")
    return all_present

def check_port_availability(port=8555):
    print(f"\n--- Checking Port {port} ---")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    if result == 0:
        print_status(f"Port {port} is currently IN USE.", "WARN")
        print("      This might cause startup failure if another instance is running.")
        print("      However, for deployment, this check is just for local debugging.")
        return True # Port is open (in use)
    else:
        print_status(f"Port {port} is FREE.", "OK")
        return False

def check_imports():
    print("\n--- Checking Syntax & Imports ---")
    # Add project root to path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    try:
        # Attempt to import main.py
        # We use importlib to safely import without running the if __name__ == "__main__" block if it exists,
        # but since main.py usually runs app() at top level or in main, we need to be careful.
        # Ideally, main.py should have a guard.
        # For now, let's checking generic syntax by compiling.
        
        files_to_check = ["main.py", "services/router.py", "views/login_view.py", "views/signup_view.py"]
        all_passed = True
        
        for filename in files_to_check:
            filepath = os.path.join(project_root, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    source = f.read()
                compile(source, filepath, "exec")
                print_status(f"Syntax Check: {filename}", "OK")
            except Exception as e:
                 print_status(f"Syntax Check: {filename} - {e}", "FAIL")
                 all_passed = False
                 
        return all_passed
    except Exception as e:
        print_status(f"Import Check Failed: {e}", "FAIL")
        return False

def main():
    print("========================================")
    print("   The Manager - Pre-deployment Check   ")
    print("========================================")
    
    env_ok = check_env_vars()
    code_ok = check_imports()
    check_port_availability()
    
    print("\n========================================")
    if env_ok and code_ok:
        print(f"{GREEN}>> CHECKS PASSED. Ready for Deployment/Commit. <<{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}>> CHECKS FAILED. Fix issues before deploying. <<{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
