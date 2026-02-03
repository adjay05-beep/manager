import flet as ft
import asyncio

async def main(page: ft.Page):
    print("\n--- PAGE PROBE START ---")
    print(f"Flet Version: {ft.__version__}")
    
    methods = [d for d in dir(page) if not d.startswith("__")]
    print(f"Total methods/attrs: {len(methods)}")
    
    # Group by common prefixes
    for prefix in ["run", "execute", "eval", "window", "_", "client", "session", "invoke"]:
        matches = [m for m in methods if m.lower().startswith(prefix)]
        if matches:
            print(f"Prefix '{prefix}': {matches}")
            
    # Check session
    if hasattr(page, "session") and page.session:
        print(f"Session Dir: {[d for d in dir(page.session) if 'send' in d.lower() or 'invoke' in d.lower() or 'execute' in d.lower()]}")

    print("--- PAGE PROBE END ---\n")
    page.window_close()

if __name__ == "__main__":
    ft.app(target=main)
