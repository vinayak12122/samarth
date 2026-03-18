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
    "TRAVEL_DATE": "19/03/2026", 
    "TRAVEL_CLASS": "Sleeper (SL)", 
    # [ AC First Class (1A) , AC 2 Tier (2A) , AC 3 Tier (3A) , AC 3 Economy (3E) , AC Chair car (CC) , Sleeper (SL)]
    "TRAIN_NUMBER": "12904" ,
    "STRIKE_TIME": "10:59:59"

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
            train_heading_xpath = f"//div[contains(@class,     'train-heading')]//strong[contains(text(), '{CONFIG    ['TRAIN_NUMBER']}')]"
            
            await page.wait_for_selector(train_heading_xpath,     timeout=15000)
            
            train_box = page.locator("div.bull-back").filter(has=page.    locator(f"strong:has-text('{CONFIG['TRAIN_NUMBER']}')"))
            
            await train_box.scroll_into_view_if_needed()
            print("Train Located...")
            
        except Exception as e:
            try:
                train_box = page.locator("div.tou-mod").filter(has=page.    locator(f"strong:has-text('{CONFIG['TRAIN_NUMBER']}')"))
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
            print("[*] Monitoring for Review Page...")
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
            await page.wait_for_selector("#captcha", timeout=0)

            max_attempts = 3
            last_b64 = ""
            
            captcha_js = """(old) => {
                const img = document.querySelector('.captcha-img');
                if (img && img.src && img.src.startsWith('data:image') && img.src !== old) {
                    return img.src; 
                }
                return false;
            }"""

            b64_future = asyncio.create_task(page.wait_for_function(captcha_js, arg=last_b64))
            
            for attempt in range(1, max_attempts + 1):
                print(f"[*] Captcha Attempt {attempt}/{max_attempts}...")
            
                try:
                    b64_handle = await b64_future
                    b64_src = await b64_handle.json_value()
                    
                    if not b64_src: continue
                    last_b64 = b64_src
            
                    b64_future = asyncio.create_task(page.wait_for_function(captcha_js, arg=last_b64))
            
                    captcha_text = Solver(b64_src)            

                    await page.evaluate("""(text) => {
                        const field = document.getElementById('captcha');
                        const btn = document.querySelector('button.train_Search.btnDefault');
                        if (field && btn) {
                            field.value = text;
                            field.dispatchEvent(new Event('input', { bubbles: true }));
                            field.dispatchEvent(new Event('change', { bubbles: true }));
                            btn.click();
                        }
                    }""", captcha_text)
            
                    success_nav = page.locator("app-payment, #pay-type").first
                    error_toast = page.locator(".ui-toast-message-error").first

                    try:
                        done, pending = await asyncio.wait([
                            asyncio.create_task(success_nav.wait_for(state="visible")),
                            asyncio.create_task(error_toast.wait_for(state="visible"))
                        ], return_when=asyncio.FIRST_COMPLETED, timeout=4)

                        for task in pending: task.cancel()
                    except:
                        pass

                    if await success_nav.is_visible():
                        print(f"[+] Success on Attempt {attempt}")
                        if not b64_future.done(): b64_future.cancel()
                        break
                    else:
                        print(f"[-] Invalid Captcha or Timeout (Attempt {attempt})")
                        await page.click('a[aria-label="Click to refresh Captcha"]', timeout=500)
            
                except Exception as e:
                    print(f"[-] Retry error: {e}")
                    if attempt == max_attempts: sys.exit(1)
                        
        except Exception as e:
            print(f"[!] Critical Error in Captcha Phase: {e}")

        
        # PHASE 5 : Payment Selection
        try:
            await page.wait_for_selector("#pay-type",timeout=0)

            await page.evaluate("""() => {
                return new Promise((resolve) => {

                    const strikeLoop = setInterval(() => {
                        const tabs = document.querySelectorAll('#pay-type .bank-type');
                        const upiTab = Array.from(tabs).find(t => t.innerText.includes('BHIM/ UPI'));
                        
                        if (upiTab && !upiTab.classList.contains('active')) {
                            upiTab.click();
                        }

                        const options = document.querySelectorAll('.bank-text');
                        const targetOption = Array.from(options).find(o => o.innerText.includes('PAYTM'));
                        
                        if (targetOption) {
                            targetOption.click();
                            
                            const payBtn = document.querySelector('button.btn-primary');
                            if (payBtn) {
                                payBtn.click();
                                clearInterval(strikeLoop);
                                resolve("Payment Initiated");
                            }
                        }
                    }, 10); 

                    setTimeout(() => { clearInterval(strikeLoop); resolve("Timeout"); }, 10000);
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
