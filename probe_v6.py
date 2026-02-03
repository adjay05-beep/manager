import flet as ft
import asyncio

async def main(page: ft.Page):
    with open("probe_web_output.txt", "w", encoding="utf-8") as f:
        f.write("\n--- WEB/SERVICES PROBE START ---\n")
        
        if hasattr(page, "web"):
            f.write(f"Page.web dir: {[d for d in dir(page.web) if not d.startswith('__')]}\n")
            
        if hasattr(page, "services"):
            f.write(f"Page.services dir: {[d for d in dir(page.services) if not d.startswith('__')]}\n")

        # Try to find if any control has a window property
        f.write(f"Page methods again, looking for eval/exec: {[m for m in dir(page) if 'exec' in m.lower() or 'eval' in m.lower()]}\n")
        
        f.write("--- PROBE END ---\n")
    page.window_close()

if __name__ == "__main__":
    ft.app(target=main)
