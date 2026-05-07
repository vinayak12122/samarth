# STEPS :-

# 1st - taskkill /F /IM msedge.exe /T

# 2nd - "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9227 --user-data-dir="C:\edge_temp_profile" --disable-blink-features=AutomationControlled

# cd samarth

# 4rd - python app.py

import sys
import time
import base64
import asyncio
import random
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from datetime import datetime
from solver import Solver

CONFIG = {           
    "TRAVEL_DATE": "09/05/2026", 
    "TRAVEL_CLASS": "AC 3 Tier (3A)", 
    # [ AC First Class (1A) , AC 2 Tier (2A) , AC 3 Tier (3A) , AC 3 Economy (3E) , AC Chair car (CC) , Sleeper (SL)]
    "TRAIN_NUMBER": "12904" ,
    "STRIKE_TIME": "09:59:59"

}

def get_target_timestamp(target_str):
    now = datetime.now()
    target_time = datetime.strptime(target_str,"%H:%M:%S").time()
    target_datetime = datetime.combine(now.date(),target_time)

    return target_datetime.timestamp()


async def run():
    async_playwright_instance = await async_playwright().start()
    try:

        browser = await async_playwright_instance.chromium.connect_over_cdp("http://localhost:9227")
    
        browser_context = browser.contexts[0]
        page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()

        await page.route("**/*.{png,jpg,jpeg,gif,webp,svg}", lambda route: 
            route.continue_() if any(x in route.request.url.lower() for x in ["captcha", "paytm", "qr"]) else route.abort())
        
        await page.route("**/*.{woff,woff2,ttf}", lambda route: route.abort())

        await Stealth().apply_stealth_async(page)
        await page.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    delete navigator.__proto__.webdriver;
    
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };
    
    // Extra safety layers
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
    
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
    });
    
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en', 'hi'],
    });
    
    // Remove Playwright signatures
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    
    // WebGL fingerprint
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter.call(this, parameter);
    };
    
    // Make dimensions realistic
    Object.defineProperty(window, 'outerWidth', {get: () => window.innerWidth});
    Object.defineProperty(window, 'outerHeight', {get: () => window.innerHeight});
""")


        current_url = page.url
        print(f"Current URL : {current_url}")
    
    
        strike_ts = get_target_timestamp(CONFIG["STRIKE_TIME"])
    
    
        trains = await page.evaluate("""() => {
                const headings = document.querySelectorAll('div.train-heading strong');
                return Array.from(headings).map(el => el.innerText.trim());
            }""")
            
        print(f"Found {len(trains)} trains:")
        for i, train in enumerate(trains, 1):
            print(f"  {i}. {train}")

        # PHASE 2 - TRAIN SEARCH LOOP
        try:
            train_heading_xpath = f"//div[contains(@class,'train-heading')]//strong[contains(text(), '{CONFIG['TRAIN_NUMBER']}')]"
            
            await page.wait_for_selector(train_heading_xpath,timeout=15000)


            train_box = page.locator("div.bull-back").filter(
                has=page.locator(f"strong:has-text('({CONFIG['TRAIN_NUMBER']})')")
            )
            
            await train_box.scroll_into_view_if_needed()
            print("Train Located...")
            
        except Exception as e:
            print("Train not found")
            try:
                train_box = page.locator("div.tou-mod").filter(has=page.locator(f"strong:has-text('{CONFIG['TRAIN_NUMBER']}')"))
                await train_box.scroll_into_view_if_needed()
            except:
                return    
    
        date_obj = datetime.strptime(CONFIG["TRAVEL_DATE"], "%d/%m/%Y")
        day_date_str = date_obj.strftime("%d %b")
        
        refresh_tab = train_box.locator("div.pre-avl, li.ui-tabmenuitem").filter(
            has_text=CONFIG['TRAVEL_CLASS']
        ).first
        
        avail_slot = train_box.locator("div.pre-avl").filter(has_text=day_date_str).first
        book_btn = train_box.locator("button:has-text('Book Now')")

        success_flag = asyncio.Event()

        async def on_response(response):
            url = response.url.lower()
            if "avlfarenquiry" in url and not success_flag.is_set():
                try:
                    data = await response.json()
                    day_list = data.get("avlDayList", [])
                    
                    if day_list:
                        status = day_list[0].get("availablityStatus", "")
                        # print(f"📡 [NETWORK] Status: {status}")

                        if any(x in status for x in ["AVAILABLE", "RAC", "CURR_AVBL", "WL"]) and "#" not in status:
                            
                            await avail_slot.dispatch_event("click")
                            await book_btn.dispatch_event("click")
                            success_flag.set()
                        else:
                            print(f"❌ No seats: {status}")
                except Exception as e:
                   
                    pass

        browser_context.on("response",on_response)
        
        print("Strike Startted...") 
        while time.time() < (strike_ts - 0.5) :
            await asyncio.sleep(0.01)

        try:
            triggered = False
            for attempt in range(20):
                if success_flag.is_set():
                    triggered = True
                    break

                
                print(f'Attempt: {attempt+1}')

                await refresh_tab.click(force=True,timeout=0)
    
                try:
                    await asyncio.wait_for(success_flag.wait(),timeout=0.6)
                    triggered = True
                    break
                except asyncio.TimeoutError:
                    continue
                                        
            if not triggered:
                await avail_slot.click(force=True)
                await asyncio.sleep(0.1)
                await book_btn.click(force=True)

        except Exception as e:
            print(f"❌ Error during strike: {e}")
        finally:
            try:
                browser_context.remove_listener("response", on_response)
            except:
                pass

    
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

            # await page.locator("tr.link:has-text('BHIM/UPI') .ui-radiobutton-box").first.click(delay=random.randint(8, 15),timeout=0)
            
            # await asyncio.sleep(random.uniform(0.06, 0.11))

            
            # await page.locator("button[type='submit'].btnDefault").first.click(delay=random.randint(6, 12),timeout=3000)
        except Exception as e:
            print(f'Speed selection failed: {e}')

        try:
            dummy = "data:image/jpg;base64,iVBORw0KGgoAAAANSUhEUgAAAMsAAAAyCAYAAADyZi/iAAAElUlEQVR42u2dTUhUURTHRSRciCAiMogEEtIiQnApEUGEiAsRQkIiJIgIGVy0kZAWbUQkWgnRKkQGREQkRBCRkIg2Ii0igoiQFiGEDCGDDEzn1hFfhzPjzH33zfv6/+Fs3rx7z7v3vp/3vnM/bGiAIAiCIAiCIAiCIAiCIAiCIKicSkIhP0uG7AHZEtke2W+yAtkJ2THZV7IVsmmyPse+G8nuki2TfWd/xajUTapeLLo9J5KbxuixeIZLnNarpTjDQm6vkK3Kl7MKfSKbJLvg0/9lss/nOQMB9YOlneynyGLX4hl2RR4mz/a4wkIuZy0gkTI9wYil/xZOX3INS6phc1B5t5U2mKwhfVZJPxrHYRi5aibbLPPiG4CGydrM8MgzTOolGyN7rfSuJcvneCKy+UZ2029vBVjcNM6yyCZP1l1Fuh4ew3u1EtcGJVfrSj1kT+GoskeY5nR+2mNHPMeNJH4PxhWWDrJDkdVWFem2RJpfZJ1xbFBy81gZSvZZ5pU5rRvL9PIPUCNgiVDhKem4MvyYqHD/Q+X+8Tg2qOlFOcJ1KvO9MuAg3znLdIFFvACLo8IrwxDTU2TKvFx5ce96XBuUXDwXLl8kpU0BS3CwZBiQihAow68jDap6lYlueVomWJStIm2TAN/8Ve8Kux1dRsJsw3mA5fz8JpR6u+P5/V4tw7Wgy0Q/LyjPYyYMx6r0NSzSbkShHQFLTLpspec45DkZrefZDKNM3COsKG2cryV6RPfOi/RTgAWw1PrBK79JcmVCq131LhOHaLeV9jURrP4afa2JPIaS2Kb4Zgmw8Lwe6jw9qneZOMy9V2bi8KKFLzlT3glYAItN3tsVQNmpd5kMDDybLbVvILL0dRzUnAZgSRcs2gx9ia/11LNMZoJQWcdm9JasNYz6C2rsD1hiCAvnn7UJyTr+2L3G4WmpVQerewELYIlvBSvvW0G59tKRL+thGGABLFGERWrGoS/5gd8Rdn0BFsDiCpYvJnTs0Neq69AxYAEsUepZTJSu2ZGvOdeTkoAFsIQJy45yzWzSanLga9D1chfAAljChKVF2br898X2CwzvdjwSCym7AQtgiSUsfM0A814LHzvwN+9yiT5gASyhwsLXzf73DwowOZ/+Msrk60BCYTkBLCmAxQPMvgLMok+fk34XZcYEFrlAthmwJBQW/r2Dz+eSeuXTb05Z1jNV40TlYMRh2RDZjwCWBMPiAUY7hG7Bh98mZRuC0QGHmIflpCX3dEN8fNHHGMzgy12l5kTNW1FYQApYAvTH3xraYXTzPv3PODhkr8TwXI8YLJkyi2NTt/mrmCZYPI1/oLT1M5/PYA7PW7SApsg7TYeiWt/cQ+ZTBQvPEfx3VnHaYOH7zc7OH0GsIeNh1jiD845fsqJngaeZo3ljFnbyyZRtMRktdPJZaWu8bbyQdFhaZQSnAYKgst2pV2uoFQjSYZl1OU6HoKSC0q0cS9SPmoGgM0jM/MJ95YN2F7UDQf8gKVSI8pkephe1BEGVYTHLPq6ihiDoDJY8A3PMgJh/CDqaimUKEARBEARBEARBEARBULL0B6XRGwUEbDkEAAAAAElFTkSuQmCC"
            await asyncio.to_thread(Solver, dummy)
        except: pass
        
        # PHASE 4 - CAPTCHA PAGE 
        MAX_ATTEMPTS = 3
        try:
            await page.wait_for_selector("app-captcha", timeout=0)
        
            for a in range(1, MAX_ATTEMPTS + 1):
        
                b64 = await page.evaluate("""() => {
                    const img = document.querySelector('img.captcha-img');
                    return img?.src?.startsWith('data:image') ? img.src : null;
                }""")
                
                # if not b64:
                #     print(f"[{a}] ✗ no img, retrying...")
                #     await asyncio.sleep(0.3)
                #     continue
        
                try:
                    txt = (await asyncio.to_thread(Solver, b64) or "").strip()
                except Exception as solver_error:
                    print(f"[{a}] ✗ Solver error: {solver_error}")
                    await asyncio.sleep(0.3)
                    continue
        
                if not txt:
                    print(f"[{a}] ✗ empty captcha text")
                    await asyncio.sleep(0.3)
                    continue
        
                ok = await page.evaluate("""t => new Promise(r => {
                    const i = document.getElementById('captcha'),
                          b = document.querySelector('button[type=submit].train_Search');
                    
                    if (!i || !b) return r(0);
                    
                    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(i, t);
                    i.dispatchEvent(new Event('input', {bubbles: true}));
                    
                    b.click();
                    
                    let n = 0;
                    const c = () => {
                        if (document.querySelector('app-payment, .bank-type') || 
                            location.href.includes('payment')) {
                            return r(1);
                        }
                        
                        if (document.querySelector('.ui-toast-message-error') || 
                            !i.value) {
                            return r(0);
                        }
                        
                        ++n < 50 ? setTimeout(c, 16) : r(0);
                    };
                    
                    c();
                })""", txt)
                        
                if ok:
                    break
                else:
                    print(f"[{a}] ✗ Failed , retrying...")
                    await asyncio.sleep(0.3)
                    
            else:
                print(f"✗ CAPTCHA FAILED after {MAX_ATTEMPTS} attempts")
        except Exception as e:
            print(f"Unexpected error: {type(e).__name__}: {e}")

        # PHASE 5 : Payment Selection With Fallback
        try:
            result = await page.evaluate("""() => {
                return new Promise((resolve, reject) => {

                    let gatewayClicked = false;
                    let payClicked = false;

                    const observer = new MutationObserver(() => {

                        // LEFT SIDE TABS
                        const tabs = Array.from(
                            document.querySelectorAll('.bank-type')
                        );

                        // BHIM TAB
                        const bhimTab = tabs.find(el =>
                            el.innerText.includes('BHIM')
                        );

                        // MULTIPLE PAYMENT TAB
                        const multiplePaymentTab = tabs.find(el =>
                            el.innerText.includes('Multiple Payment Service')
                        );

                        // =====================================================
                        // STEP 1 : ENSURE BHIM TAB ACTIVE
                        // =====================================================

                        if (
                            bhimTab &&
                            !bhimTab.classList.contains('bank-type-active')
                        ) {
                            bhimTab.click();
                            return;
                        }

                        // CURRENT GATEWAYS
                        let gateways = Array.from(
                            document.querySelectorAll('.bank-text')
                        );

                        // =====================================================
                        // PRIORITY : PAYTM
                        // =====================================================

                        let selectedGateway = gateways.find(el =>
                            el.innerText.includes('PAYTM')
                        );

                        let gatewayName = "PAYTM";

                        // =====================================================
                        // FALLBACK : PHONEPE
                        // =====================================================

                        if (!selectedGateway) {

                            // SWITCH TAB
                            if (
                                multiplePaymentTab &&
                                !multiplePaymentTab.classList.contains      ('bank-type-active')
                            ) {
                                multiplePaymentTab.click();
                                return;
                            }

                            // RE-QUERY AFTER TAB SWITCH
                            gateways = Array.from(
                                document.querySelectorAll('.bank-text')
                            );

                            selectedGateway = gateways.find(el =>
                                el.innerText.includes('PhonePe')
                            );

                            gatewayName = "PHONEPE";
                        }

                        // CLICK GATEWAY ONLY ONCE
                        if (selectedGateway && !gatewayClicked) {
                            selectedGateway.click();
                            gatewayClicked = true;
                        }

                        // CONTINUE BUTTON
                        const payBtn =
                            document.querySelector('button.btn-primary');

                        if (
                            payBtn &&
                            !payBtn.disabled &&
                            gatewayClicked &&
                            !payClicked
                        ) {

                            payClicked = true;

                            payBtn.click();

                            observer.disconnect();
                            resolve(gatewayName);
                        }

                    });

                    observer.observe(document.body, {
                        childList: true,
                        subtree: true
                    });

                    // INITIAL TRIGGER
                    document.body.dispatchEvent(new Event('input'));

                    // TIMEOUT
                    setTimeout(() => {
                        observer.disconnect();
                        reject("Gateway Selection Timeout");
                    }, 15000);

                });
            }""")

            print(f"✅ Gateway Selected : {result}")

        except Exception as e:
            print(f'💥 Payment Phase Error: {e}')

        # PHASE 6 : Initiating QR Generation
        # try:
        #     qr_selector = 'span[onclick*="submitUpiQrForm"]'
        #     target_span = await page.wait_for_selector(qr_selector, state="visible", timeout=0)
        #     await target_span.click()
        # except Exception as e:
        #     print(f'QR Generation Error: {e}')

    
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
