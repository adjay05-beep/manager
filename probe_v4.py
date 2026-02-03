import flet as ft
import asyncio

async def main(page: ft.Page):
    with open("probe_output.txt", "w", encoding="utf-8") as f:
        f.write("\n--- PAGE PROBE START ---\n")
        f.write(f"Flet Version: {ft.__version__}\n")
        
        methods = [d for d in dir(page) if not d.startswith("__")]
        f.write(f"Total methods/attrs: {len(methods)}\n")
        
        # Group by common prefixes
        for prefix in ["run", "execute", "eval", "window", "_", "client", "session", "invoke"]:
            matches = [m for m in methods if m.lower().startswith(prefix)]
            if matches:
                f.write(f"Prefix '{prefix}': {matches}\n")
                
        # Check session
        if hasattr(page, "session") and page.session:
            f.write(f"Session Dir: {[d for d in dir(page.session) if 'send' in d.lower() or 'invoke' in d.lower() or 'execute' in d.lower()]}\n")

        f.write("--- PAGE PROBE END ---\n")
    page.window_close()

if __name__ == "__main__":
    ft.app(target=main)
