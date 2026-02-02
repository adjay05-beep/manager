import asyncio
from playwright.async_api import async_playwright

async def test_auto_login():
    """Test if dev auto-login works on localhost"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to localhost
        await page.goto("http://localhost:8555")
        
        # Wait for auto-login to trigger (0.3s + some buffer)
        await asyncio.sleep(2)
        
        # Check if we're on dashboard (URL should change or dashboard content visible)
        current_url = page.url
        print(f"Current URL: {current_url}")
        
        # Take screenshot
        await page.screenshot(path="dev_autologin_test.png")
        
        # Check for dashboard indicators
        try:
            # Try to find dashboard elements
            dashboard_visible = await page.locator("text=Messenger").is_visible(timeout=2000) or \
                              await page.locator("text=Calendar").is_visible(timeout=2000) or \
                              await page.locator("text=Attendance").is_visible(timeout=2000)
            
            if dashboard_visible:
                print("✅ AUTO-LOGIN SUCCESS: Dashboard is visible!")
                return True
            else:
                print("❌ AUTO-LOGIN FAILED: Still on login page")
                return False
        except Exception as e:
            print(f"❌ AUTO-LOGIN FAILED: {e}")
            return False
        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_auto_login())
    exit(0 if result else 1)
