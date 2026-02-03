import flet as ft
import asyncio

async def main(page: ft.Page):
    with open("probe_web_v2.txt", "w", encoding="utf-8") as f:
        f.write("\n--- WEB V2 PROBE START ---\n")
        f.write(f"Flet: {ft.__version__}\n")
        
        if hasattr(page, "web"):
            f.write(f"Page.web attrs: {[d for d in dir(page.web) if not d.startswith('_')]}\n")
            
        if hasattr(page, "session") and page.session:
             f.write(f"Page.session attrs: {[d for d in dir(page.session) if not d.startswith('_')]}\n")

        # Explicitly check for names on page again
        for m in dir(page):
            if "script" in m.lower() or "js" in m.lower() or "eval" in m.lower():
                 f.write(f"Found on page: {m}\n")
                 
        f.write("--- PROBE END ---\n")
    page.window_close()

if __name__ == "__main__":
    ft.run(main, port=8999)
