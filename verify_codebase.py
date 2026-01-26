import py_compile
import os
import sys
import importlib.util

def check_syntax(directory="."):
    print(f"Checking syntax in {directory}...")
    errors = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py") and "venv" not in root:
                path = os.path.join(root, file)
                try:
                    py_compile.compile(path, doraise=True)
                except py_compile.PyCompileError as e:
                    errors.append(f"Syntax Error in {path}: {e}")
                except Exception as ex:
                     errors.append(f"Error checking {path}: {ex}")
    return errors

def check_imports():
    print("Checking critical imports...")
    critical_modules = [
        "main",
        "views.home_view",
        "views.work_view",
        "views.calendar_view",
        "views.signup_view",
        "views.profile_edit_view",
        "services.auth_service",
        "services.calendar_service"
    ]
    errors = []
    for mod in critical_modules:
        try:
            # Try to find spec first to avoid executing main logic
            if importlib.util.find_spec(mod) is None:
                 errors.append(f"Module not found: {mod}")
        except Exception as e:
            errors.append(f"Import Error {mod}: {e}")
    return errors

if __name__ == "__main__":
    syntax_errs = check_syntax()
    import_errs = check_imports()
    
    if syntax_errs or import_errs:
        print("❌ VERIFICATION FAILED")
        for e in syntax_errs: print(e)
        for e in import_errs: print(e)
        sys.exit(1)
    else:
        print("✅ VERIFICATION PASSED: No syntax or import errors found.")
        sys.exit(0)
