import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv

load_dotenv()

async def test_login():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False) # Set to True for headless
        page = await browser.new_page()
        
        print("🔗 Navigating to http://localhost:8555...")
        try:
            await page.goto("http://localhost:8555", timeout=60000)
            
            # 1. Wait for Login Page
            print("⏳ Waiting for login fields...")
            await page.wait_for_selector("input[type='text']", timeout=10000) # Email field
            
            # 2. Fill Credentials
            # Note: These should be provided by environment variables or user input
            test_email = os.getenv("TEST_USER_EMAIL", "test@example.com")
            test_pw = os.getenv("TEST_USER_PW", "password123")
            
            print(f"⌨️ Entering email: {test_email}")
            await page.fill("input[type='text']", test_email)
            await page.fill("input[type='password']", test_pw)
            
            # 3. Click Login
            print("🖱️ Clicking Login button...")
            # Flet buttons often render as specific divs or buttons with text
            await page.click("text='로그인'")
            
            # 4. Verify Success
            print("🏁 Verifying login success...")
            # We look for a unique element on the Home page (e.g., 'THE MANAGER' title or navigation bar)
            try:
                await page.wait_for_selector("text='매장 선택'", timeout=15000)
                print("✅ Login Successful! Store selection dialog visible.")
            except:
                # Check if we are already on home
                await page.wait_for_selector("i[class*='home']", timeout=5000) 
                print("✅ Login Successful! Home navigation verified.")
            
            # Take a screenshot
            await page.screenshot(path="login_result.png")
            print("📸 Screenshot saved as login_result.png")
            
        except Exception as e:
            print(f"❌ Test Failed: {e}")
            await page.screenshot(path="login_error.png")
        
        await browser.close()

if __name__ == "__main__":
    if not os.getenv("TEST_USER_EMAIL"):
        print("⚠️ Warning: TEST_USER_EMAIL not set in .env. Using default placeholders.")
    asyncio.run(test_login())
