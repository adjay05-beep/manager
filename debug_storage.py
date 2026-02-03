import flet as ft
import asyncio
import json

async def main(page: ft.Page):
    await page.shared_preferences.set("debug_key", "python_value")
    
    # Polyfill if needed (already in main.py but for this test we'll add it)
    if not hasattr(page, "run_javascript"):
        async def run_javascript_polyfill(script):
            await page._invoke_method("run_javascript", {"script": script})
        page.run_javascript = run_javascript_polyfill

    await asyncio.sleep(1) # Wait for sync
    
    # Script to find the key in localStorage
    script = """
    (function(){
        let found = "None";
        for (let i = 0; i < localStorage.length; i++){
            let key = localStorage.key(i);
            if (localStorage.getItem(key) === "python_value") {
                found = key;
                break;
            }
        }
        alert("Prefix Found: " + found);
    })()
    """
    await page.run_javascript(script)
    await asyncio.sleep(5)
    page.window_close()

ft.run(main)
