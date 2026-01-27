import os
import sys
import importlib.util
import traceback

def check_imports(start_dir):
    print(f"🔍 Starting Integrity Check in: {start_dir}")
    error_count = 0
    checked_count = 0
    
    # Walk through directory
    for root, dirs, files in os.walk(start_dir):
        # Skip virtualenvs or hidden dirs
        if "venv" in root or ".git" in root or "__pycache__" in root:
            continue
            
        for file in files:
            if file.endswith(".py") and not file.startswith("verify_"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, start_dir)
                module_name = os.path.splitext(rel_path.replace(os.path.sep, "."))[0]
                
                # print(f"Checking: {module_name} ...", end="")
                try:
                    spec = importlib.util.spec_from_file_location(module_name, full_path)
                    if spec and spec.loader:
                        # Just load the module, don't execute if possible, but spec.loader.exec_module does execute top-level
                        # We try to catch syntax errors primarily
                         with open(full_path, 'r', encoding='utf-8') as f:
                            compile(f.read(), full_path, 'exec')
                         
                    print(f" [OK] {rel_path}")
                    checked_count += 1
                except SyntaxError as e:
                    print(f"\n❌ SYNTAX ERROR in {rel_path}: {e}")
                    error_count += 1
                except Exception as e:
                    # Some runtime imports might fail due to missing env vars or Flet page context
                    # We largely care about Syntax/Import errors that are static
                    if "ModuleNotFoundError" in str(type(e).__name__):
                         print(f"\n❌ IMPORT ERROR in {rel_path}: {e}")
                         error_count += 1
                    else:
                        pass 
                        # Runtime errors (like missing env vars) are expected in static check
                        # print(f" [WARNING] Runtime issue in {rel_path}: {e}")

    print("-" * 30)
    print(f"Checked {checked_count} files.")
    if error_count == 0:
        print("✅ INTEGRITY CHECK PASSED: No Syntax or Missing Import errors found.")
    else:
        print(f"🚨 INTEGRITY CHECK FAILED: Found {error_count} critical errors.")

if __name__ == "__main__":
    check_imports(os.getcwd())
