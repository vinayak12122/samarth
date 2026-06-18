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
    "TRAVEL_DATE": "19/06/2026", 
    "TRAVEL_CLASS": "Sleeper (SL)", 
    # [ AC First Class (1A) , AC 2 Tier (2A) , AC 3 Tier (3A) , AC 3 Economy (3E) , AC Chair car (CC) , Sleeper (SL)]
    "TRAIN_NUMBER": "12533" ,
    "STRIKE_TIME": "10:59:58",
    "QUOTA":"pt",
    # [ TQ , PT ]
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

        # user = input("\nDo you want to Perform Pre Booking FLow? (Y/N): ").strip().upper()

        # if user == 'Y':
        #     credentials = {
        #         'username':CONFIG["Username"],
        #         'password':CONFIG["Password"]
        #     }
        #     await PerformPreBook(page,credentials)

        #     await page.wait_for_url("**/nget/booking/train-list",timeout=0)
        # else:
        #     print("\nSkipping Login PreFlow...\n")
    
    
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
    
        # =========================================================
        # PRE STRIKE
        # =========================================================
        try:
        
            refresh_btn = train_box.locator(
                "div.pre-avl"
            ).filter(
                has_text=CONFIG["TRAVEL_CLASS"]
            ).locator(
                "text=Refresh"
            ).first

            await refresh_btn.click(
                force=True,
                timeout=500
            )

            print("Refresh clicked once")

        except Exception as e:
        
            print(f"Refresh failed : {e}")

        # =========================================================
        # WAIT FOR STRIKE TIME
        # =========================================================

        class_tab = train_box.locator(
                    "li.ui-tabmenuitem"
                ).filter(
                    has_text=CONFIG["TRAVEL_CLASS"]
                ).first
        
        avail_slot = train_box.locator(
                    "td.link div.pre-avl"
                ).filter(
                    has_text=day_date_str
                ).first
        
        book_btn = train_box.locator(
                    "button:has-text('Book Now')"
                ).first

        while time.time() < (strike_ts - 0.5):
            await asyncio.sleep(random.uniform(0.08, 0.15))

        attempt = 0
        MAX_ATTEMPTS = 10000

        while attempt < MAX_ATTEMPTS:
            attempt += 1

            try:

                try:
                    await class_tab.click(delay=random.randint(12, 28), timeout=400)
                except:
                    print('Class Tab Fallback')
                    await class_tab.dispatch_event("click")

                await asyncio.sleep(random.uniform(0.28, 0.34))

                status = (
                    await avail_slot.inner_text()
                ).replace("\n", " ").strip()

                if "#" in status:
                    await asyncio.sleep(random.uniform(0.08, 0.15))
                    continue
                
                try:
                    await avail_slot.click(delay=random.randint(15, 30), timeout=400)
                except:
                    print('Avail Slot Fallback')
                    await avail_slot.dispatch_event("click")


                await asyncio.sleep(random.uniform(0.06, 0.12))

                try:
                    await book_btn.click(delay=random.randint(10, 25), timeout=400)
                except:
                    print('Booking Button Fallback')
                    await book_btn.dispatch_event("click")

                break
            
            except Exception as e:
                await asyncio.sleep(random.uniform(0.04, 0.09))
                continue
        
        else:
            print(f"✗ Failed after {MAX_ATTEMPTS} attempts")
        
        quota = CONFIG.get("QUOTA", "").strip().lower()
        is_tq = quota == "tq"

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
#         try:

#             if is_tq:
#                 confirm_checkbox = page.locator("#confirmberths").first
#                 print("Label count:",await page.locator("label[for='confirmberths']").count())

                
#                 await confirm_checkbox.wait_for(
#                     state="visible",
#                     timeout=10000
#                 )

#                 print("Label visible:",await page.locator("label[for='confirmberths']").is_visible())
#                 if not await confirm_checkbox.is_checked():
#                     confirm_label = page.locator(
#                         "label[for='confirmberths']"
#                     ).first

#                     await confirm_label.click(
#                         delay=random.randint(35, 65),
#                         timeout=2000,
#                         force=True
#                     )

#                 print(
#     "Checkbox checked:",
#     await confirm_checkbox.is_checked()
# )

#             upi_radio = page.locator("tr.link:has-text('BHIM/UPI') .ui-radiobutton-box").first
#             continue_btn = page.locator("button[type='submit'].btnDefault").first

#             await upi_radio.wait_for(state="visible", timeout=10000)

#             await asyncio.sleep(random.uniform(0.3, 0.5))

#             await upi_radio.click(
#                 delay=random.randint(35, 65), 
#                 position={"x": random.randint(3, 7), "y": random.randint(3, 7)},
#                 timeout=2000, 
#                 force=True
#             )
            
#             await asyncio.sleep(random.uniform(0.25, 0.3))

#             await continue_btn.click(
#                 delay=random.randint(35, 65), 
#                 position={"x": random.randint(15, 70), "y": random.randint(10, 30)},
#                 timeout=2000, 
#                 force=True
#             )

#         except Exception as e:
#             print(f'❌ Passenger room execution failed completely: {e}')


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

            print(f"Gateway Selected : {result}")

        except Exception as e:
            print(f'Payment Phase Error: {e}')

        # PHASE 5 : Payment Selection
        # try:
        
        #     pay_btn = await page.wait_for_selector(
        #         'button.btn-primary',
        #         state='visible',
        #         timeout=25000
        #     )

        #     await pay_btn.wait_for_element_state(
        #         'enabled',
        #         timeout=25000
        #     )

        #     await pay_btn.click()

        #     print("✅ Payment Button Clicked")

        # except Exception as e:
        #     print(f'💥 Payment Phase Error: {e}')


        # PHASE 6 : Initiating QR Generation
        # try:
        
        #     qr_selector = 'span[onclick*="submitUpiQrForm"]'

        #     target_span = await page.wait_for_selector(
        #         qr_selector,
        #         state="visible",
        #         timeout=25000
        #     )

        #     await target_span.click()

        #     print("✅ QR Generation Triggered")

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
