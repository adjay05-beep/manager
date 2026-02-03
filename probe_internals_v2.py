import flet as ft
import asyncio

async def main(page: ft.Page):
    print("PAGE_ANALYSIS_START")
    try:
        # Check for _invoke_method
        has_invoke = hasattr(page, "_invoke_method")
        print(f"has_invoke: {has_invoke}")
        
        # Check session
        if hasattr(page, "session"):
             print(f"page.session type: {type(page.session)}")
             for m in dir(page.session):
                 if "send" in m.lower() or "cmd" in m.lower():
                     print(f"session method: {m}")

        # Check for any 'client' or 'connection' related attributes
        for attr in dir(page):
            if any(x in attr.lower() for x in ["client", "conn", "sock", "bridge"]):
                print(f"attr: {attr} = {type(getattr(page, attr))}")

    except Exception as e:
        print(f"Analysis error: {e}")
    
    print("PAGE_ANALYSIS_END")
    await asyncio.sleep(1)
    page.window_close()

if __name__ == "__main__":
    ft.run(main)
