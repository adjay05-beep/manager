import flet as ft

def probe():
    print("\n--- STATIC PROBE START ---")
    print(f"Flet Version: {ft.__version__}")
    
    # Inspect Page class
    page_attrs = [d for d in dir(ft.Page) if not d.startswith("__")]
    print(f"Page Attrs: {page_attrs}")
    
    # Inspect Control class (Page is a Control)
    control_attrs = [d for d in dir(ft.Control) if not d.startswith("__")]
    print(f"Control Attrs: {control_attrs}")
    
    # Specifically look for patterns again
    patterns = ["run", "execute", "eval", "window", "_", "client", "session", "invoke"]
    for p in page_attrs:
        if any(pat in p.lower() for pat in patterns):
            print(f"Interesting: {p}")
            
    print("--- STATIC PROBE END ---\n")

if __name__ == "__main__":
    probe()
