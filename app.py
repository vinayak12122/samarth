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
    "TRAVEL_DATE": "21/03/2026", 
    "TRAVEL_CLASS": "Sleeper (SL)", 
    # [ AC First Class (1A) , AC 2 Tier (2A) , AC 3 Tier (3A) , AC 3 Economy (3E) , AC Chair car (CC) , Sleeper (SL)]
    "TRAIN_NUMBER": "12904" ,
    "STRIKE_TIME": "10:59:57"

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
        try:
            MAX_ATTEMPTS = 5
        
            await page.wait_for_selector('.captcha-img', timeout=0)
        
            await page.evaluate("""
            () => {
                window.__captchaQueue = [];
                window.__captchaLast = null;
        
                const pushCaptcha = () => {
                    const img = document.querySelector('.captcha-img');
                    if (!img || !img.src || !img.src.startsWith('data:image')) return;
        
                    if (img.src !== window.__captchaLast) {
                        window.__captchaLast = img.src;
                        window.__captchaQueue.push(img.src);
                    }
                };
        
                pushCaptcha();
        
                const observer = new MutationObserver(pushCaptcha);
                observer.observe(document.body, { childList: true, subtree: true });
        
                setInterval(pushCaptcha, 25);
            }
            """)
        
            attempt = 0
            start_time = time.time()
        
            while attempt < MAX_ATTEMPTS:
        
                if time.time() - start_time > 15:
                    print("[!] Captcha timeout overall")
                    sys.exit(1)
        
                b64_src = await page.evaluate("() => window.__captchaQueue.shift() || null")
        
                if not b64_src:
                    await asyncio.sleep(0.005)
                    continue
        
                attempt += 1
                print(f"[*] Attempt {attempt}")

                try:
                    captcha_text = await asyncio.to_thread(Solver, b64_src)
                except Exception as e:
                    print(f"[-] Solver error: {e}")
                    continue
        
                if not captcha_text or len(captcha_text) < 3:
                    print("[-] Bad prediction, skipping")
                    continue
        
                await page.evaluate("""(text) => {
                    const field = document.getElementById('captcha');
                    const btn = document.querySelector('button.train_Search.btnDefault');
        
                    if (field && btn) {
                        field.value = text;
                        field.dispatchEvent(new Event('input', { bubbles: true }));
                        btn.click();
                    }
                }""", captcha_text)
        
                try:
                    result_handle = await page.wait_for_function("""() => {
                        if (document.querySelector("app-payment, #pay-type")) return "SUCCESS";
                        if (document.querySelector(".ui-toast-message-error")) return "FAIL";
                        return null;
                    }""", timeout=2000)
        
                    status = await result_handle.json_value()
        
                except:
                    status = "TIMEOUT"

                if status == "SUCCESS":
                    print(f"[+] SUCCESS in attempt {attempt}")
                    break
        
                elif status == "FAIL":
                    print(f"[-] Wrong captcha ({attempt}) → auto-refresh")
                    continue
        
                else:
                    print(f"[-] Timeout ({attempt})")
                    continue
        
            else:
                print("[!] CAPTCHA FAILED")
                sys.exit(1)
        
        except Exception as e:
            print(f"[!] CRITICAL ERROR: {e}")
            sys.exit(1)

        
        # PHASE 5 : Payment Selection
        try:
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
