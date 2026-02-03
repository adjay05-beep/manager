import flet as ft
import asyncio

async def main(page: ft.Page):
    await page.shared_preferences.set("key_xyz", "value_xyz")
    # This will write to localStorage.
    # We want to know the prefix.
    # We will iterate ALL localStorage keys and write them to a Text control.
    
    t = ft.Text("Searching...")
    page.add(t)
    
    if not hasattr(page, "run_javascript"):
        async def rj(script): await page._invoke_method("run_javascript", {"script": script})
        page.run_javascript = rj

    # JS to find the key 'key_xyz' and its prefix
    await page.run_javascript("""
        (function(){
            let result = "Not Found";
            for(let i=0; i<localStorage.length; i++){
                let k = localStorage.key(i);
                if(localStorage.getItem(k) === "value_xyz"){
                    result = k;
                    break;
                }
            }
            // Use a hack to send it back: change the page title? 
            // Or use another preferences key we know works? 
            // Let's use 'prefix_found' key.
            localStorage.setItem('flet_pref:prefix_found', result); // Try with prefix first
            localStorage.setItem('prefix_found', result); // And without
        })()
    """)
    
    await asyncio.sleep(2)
    p1 = await page.shared_preferences.get("prefix_found")
    print(f"PREFIX DETECTED: {p1}")
    t.value = f"Detected: {p1}"
    page.update()
    await asyncio.sleep(5)
    page.window_close()

ft.run(main)
