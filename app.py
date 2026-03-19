# STEPS :-

# 1st - taskkill /F /IM msedge.exe /T

# 2nd - "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="C:\Users\RAM\AppData\Local\Microsoft\Edge\User Data\Profile 1" --disable-blink-features=AutomationControlled

# cd samarth

# 4rd - python app.py

import sys
import time
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from datetime import datetime
from solver import Solver

CONFIG = {           
    "TRAVEL_DATE": "20/03/2026", 
    "TRAVEL_CLASS": "Sleeper (SL)", 
    # [ AC First Class (1A) , AC 2 Tier (2A) , AC 3 Tier (3A) , AC 3 Economy (3E) , AC Chair car (CC) , Sleeper (SL)]
    "TRAIN_NUMBER": "12904" ,
    "STRIKE_TIME": "09:59:57"

}

def get_target_timestamp(target_str):
    now = datetime.now()
    target_time = datetime.strptime(target_str,"%H:%M:%S").time()
    target_datetime = datetime.combine(now.date(),target_time)

    return target_datetime.timestamp()


async def run():
    async_playwright_instance = await async_playwright().start()
    try:

        browser = await async_playwright_instance.chromium.connect_over_cdp("http://localhost:9222")
    
        browser_context = browser.contexts[0]
        page = browser_context.pages[0] if browser_context.pages else     await browser_context.new_page()
    
        await Stealth().apply_stealth_async(page)
    
        strike_ts = get_target_timestamp(CONFIG["STRIKE_TIME"])
    
    
        # PHASE 2 - TRAIN SEARCH LOOP
        try:
            train_heading_xpath = f"//div[contains(@class,'train-heading')]//strong[contains(text(), '{CONFIG['TRAIN_NUMBER']}')]"
            
            await page.wait_for_selector(train_heading_xpath,timeout=15000)
            
            train_box = page.locator("div.bull-back").filter(has=page.locator(f"strong:has-text('{CONFIG['TRAIN_NUMBER']}')"))
            
            await train_box.scroll_into_view_if_needed()
            print("Train Located...")
            
        except Exception as e:
            try:
                train_box = page.locator("div.tou-mod").filter(has=page.locator(f"strong:has-text('{CONFIG['TRAIN_NUMBER']}')"))
                await train_box.scroll_into_view_if_needed()
            except:
                return    
    
        date_obj = datetime.strptime(CONFIG["TRAVEL_DATE"], "%d/%m/%Y")
        day_date_str = date_obj.strftime("%d %b")
    
        while time.time() < strike_ts:
            await asyncio.sleep(0.1)
    
        print("Strike Startted...")   
        while True:
            try:
                current_refresh = train_box.locator("div.pre-avl, li.ui-tabmenuitem").filter(has_text=CONFIG['TRAVEL_CLASS']).first
                if await current_refresh.count() > 0:
                    await current_refresh.click(force=True, no_wait_after=True)

                await asyncio.sleep(0.35)
                
                avail_slot = train_box.locator("div.pre-avl").filter(has_text=day_date_str).first
    
                status = await avail_slot.evaluate("el => el.innerText")
                status = status.replace('\n', ' ').strip()
    
                if ("AVAILABLE" in status or "WL" in status or "RAC" in status) and "#" not in status:
                    print(f"[!] Booking Open! Status: {status}")
                    
                    await avail_slot.click(force=True)
                    
                    book_btn = train_box.locator("button:has-text('Book Now')")
                    await book_btn.click(force=True)
                    break
                elif "#" in status:
                    continue
            except:
                continue        

    
        # PHASE 3 - PASSENGER ROOM
        try:
            await page.evaluate("""() => {
                return new Promise((resolve) => {
                    const observer = new MutationObserver((mutations, obs) => {
                        const upiRow = Array.from(document.querySelectorAll('tr.link'))
                                            .find(row => row.innerText.includes('BHIM/UPI'));
                        const continueBtn = document.querySelector('button[type="submit"].btnDefault');
        
                        if (upiRow) {
                            const radio = upiRow.querySelector('.ui-radiobutton-box');
                            if (radio && !radio.classList.contains('ui-state-active')) {
                                radio.click();
                            }
                        }
        
                        if (continueBtn) {
                            continueBtn.click();
                            obs.disconnect();
                            resolve("Done");
                        }
                    });
                    observer.observe(document.body, { childList: true, subtree: true });
                });
            }""")
        except Exception as e:
            print(f'Speed selection failed: {e}')
        
       # PHASE 4 - CAPTCHA PAGE
        print("Waiting for Captcha...")
        try:
            last_b64 = ""
            captcha_js = """(old) => {
                const img = document.querySelector('.captcha-img');
                if (img && img.src && img.src.startsWith('data:image') && img.src !== old) return img.src; 
                return false;
            }"""

            b64_future = asyncio.create_task(page.wait_for_function(captcha_js, arg=last_b64, timeout=0))
            
            for attempt in range(1, 4):
                print(f"[*] Captcha Attempt {attempt}/3...")
                try:
                    b64_handle = await b64_future
                    b64_src = await b64_handle.json_value()
                    if not b64_src: continue

                    last_b64 = b64_src
                    b64_future = asyncio.create_task(page.wait_for_function(captcha_js, arg=last_b64, timeout=0))
            
                    captcha_text = Solver(b64_src)

                    await page.evaluate("""(text) => {
                        const field = document.getElementById('captcha');
                        const btn = document.querySelector('button.train_Search.btnDefault');
                        if (field && btn) {
                            field.value = text;
                            // Trigger all possible validation events at once
                            ['input', 'change', 'blur'].forEach(ev => 
                                field.dispatchEvent(new Event(ev, { bubbles: true }))
                            );
                            btn.click();
                        }
                    }""", captcha_text)
            

                    success = False
                    start_wait = time.time()
                    while time.time() - start_wait < 3.5:
                        # Check for success/error elements directly
                        if await page.locator("app-payment, #pay-type").first.is_visible():
                            success = True
                            break
                        if await page.locator(".ui-toast-message-error").first.is_visible():
                            break
                        await asyncio.sleep(0.05) 

                    if success:
                        print(f"[+] Success on Attempt {attempt}")
                        if not b64_future.done(): b64_future.cancel()
                        break
                    else:
                        print(f"[-] Invalid or Timeout (Attempt {attempt})")
                        # Force refresh if we didn't land on payment
                        await page.click('a[aria-label="Click to refresh Captcha"]', force=True)
            
                except Exception as e:
                    print(f"[-] Fast-Retry: {e}")
                    if attempt == 3: sys.exit(1)
                        
        except Exception as e:
            print(f"[!] Critical Error: {e}")

        
        # PHASE 5 : Payment Selection
        try:
            # Immediately after submitting Captcha, start the "Payment Sniper"
            await page.evaluate("""() => {
                return new Promise((resolve) => {
                    const observer = new MutationObserver((mutations, obs) => {
                        // Target elements
                        const upiTab = Array.from(document.querySelectorAll('.bank-type'))
                                            .find(t => t.innerText.includes('BHIM/ UPI'));
                        const paytm = Array.from(document.querySelectorAll('.bank-text'))
                                           .find(o => o.innerText.includes('PAYTM'));
                        const payBtn = document.querySelector('button.btn-primary');
            
                        // Logic: Click as soon as they appear
                        if (upiTab && !upiTab.classList.contains('active')) {
                            upiTab.click();
                        }
                        if (paytm) {
                            paytm.click();
                        }
                        if (payBtn && paytm) { // Only click pay if paytm was selected
                            payBtn.click();
                            obs.disconnect();
                            resolve("Success");
                        }
                    });
                    observer.observe(document.body, { childList: true, subtree: true });
                });
            }""")
            print("Scan QR Now....")
        except Exception as e:
            print(f'Payment Phase Error : {e}')


    
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if browser:
            await browser.close() 
        await async_playwright_instance.stop()


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nStopping script...")
