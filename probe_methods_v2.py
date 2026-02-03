import flet as ft
import asyncio

async def main(page: ft.Page):
    print("PROBE_START")
    methods = ["run_javascript", "execute_javascript", "eval", "evaluate", "window_execute_javascript", "runJavascript"]
    
    # Check what page has
    print(f"Page attributes containing 'invoke' or 'send': {[m for m in dir(page) if 'invoke' in m.lower() or 'send' in m.lower()]}")
    
    for m_name in methods:
        try:
            print(f"Trying _invoke_method('{m_name}')...")
            await page._invoke_method(m_name, {"script": "console.log('Probe: " + m_name + "')"})
            print(f"SUCCESS: {m_name}")
        except Exception as e:
            print(f"FAILED: {m_name} -> {e}")
            
    print("PROBE_END")
    await asyncio.sleep(1)
    page.window_close()

if __name__ == "__main__":
    ft.run(main)
