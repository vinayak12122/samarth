# STEPS :-
 
# 1st - cd samarth

# 2nd - taskkill /F /IM msedge.exe /T

# 3rd - "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="C:\Users\Public\edge_clean_profile"

# 4th - python app.py

import re
import sys
import time
import math
import base64
import asyncio
import random
from playwright.async_api import async_playwright, expect, TimeoutError
from playwright_stealth import Stealth
from datetime import datetime
from solver import Solver

CONFIG = {      
    "TRAVEL_DATE": "14/11/2026", # DD/MM/YYYY
    "TRAVEL_CLASS": "AC 3 Tier (3A)", 
    # [ AC First Class (1A) , AC 2 Tier (2A) , AC 3 Tier (3A) , AC 3 Economy (3E) , AC Chair car (CC) , Sleeper (SL) , Second Sitting (2S) ]
    "TRAIN_NUMBER": "12961" ,
    "STRIKE_TIME": "09:59:58",
    "QUOTA":"tq",
    # [ TQ , PT ]
}

global_mouse = {
    "last_x": 300, 
    "last_y": 300
}

async def human_glide_to(page, locator, mouse_state):
    box = await locator.bounding_box()
    if not box:
        return False
        
    tgt_x = box["x"] + (box["width"] * random.uniform(0.45, 0.55))
    tgt_y = box["y"] + (box["height"] * random.uniform(0.45, 0.55))
    
    start_x, start_y = mouse_state["last_x"], mouse_state["last_y"]
    steps = random.randint(3, 6)
    
    amp_x = random.uniform(-0.5, 0.5) * (box["width"] * 0.15)
    amp_y = random.uniform(-0.5, 0.5) * (box["height"] * 0.15)
    
    for i in range(1, steps + 1):
        t = i / steps
        dampener = math.sin(t * math.pi) * (1 - t)
        
        curr_x = start_x + (tgt_x - start_x) * t + (amp_x * dampener)
        curr_y = start_y + (tgt_y - start_y) * t + (amp_y * dampener)
        
        await page.mouse.move(curr_x, curr_y)
        await asyncio.sleep(random.uniform(0.003, 0.006))
        
    await page.mouse.move(tgt_x, tgt_y)
    await asyncio.sleep(random.uniform(0.04, 0.07))
    
    mouse_state["last_x"], mouse_state["last_y"] = tgt_x, tgt_y
    return True


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
        page = None
        for p in browser_context.pages:
            if "irctc.co.in" in p.url:
                page = p
                break
                
        if not page:
            print("❌ Error: Open IRCTC session window not detected on port 9222!")
            return

        await Stealth().apply_stealth_async(page)

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

            await refresh_btn.wait_for(state="visible", timeout=2000)

            await human_glide_to(page, refresh_btn, global_mouse)

            await refresh_btn.click(timeout=1000)
            print("Refresh clicked")

            await asyncio.sleep(random.uniform(0.25, 0.45))


        except Exception as e:
            print(f"Refresh failed or element shifted: {e}")

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

        while time.time() < (strike_ts + 0.8):
            await asyncio.sleep(0.1)

        attempt = 0
        MAX_ATTEMPTS = 10000

        while attempt < MAX_ATTEMPTS:
        
            attempt += 1

            try:
            
                print(f"Attempt : {attempt}")

                await human_glide_to(page, class_tab, global_mouse)
                await class_tab.click()

                try:
                    await expect(class_tab).to_have_attribute("aria-selected", "true", timeout=2500)
                    await asyncio.sleep(random.uniform(0.030, 0.080))
                except TimeoutError:
                    pass

                await asyncio.sleep(0.3)

                status = (await avail_slot.inner_text()).replace("\n", " ").strip()

                if "#" not in status:
                    await human_glide_to(page, avail_slot, global_mouse)
                    await avail_slot.click()
                    try:
                        await expect(book_btn).not_to_have_class(re.compile(r"disable-book"), timeout=2000)
                    except TimeoutError:
                        await book_btn.wait_for(state="visible", timeout=1500)

                    await human_glide_to(page, book_btn, global_mouse)
                    await book_btn.click()

                    break
            
            except Exception as e:
                print(f"Loop Error : {e}")
                await asyncio.sleep(0.1)
                continue
        
        else:
            print(f"✗ Failed after {MAX_ATTEMPTS} attempts")
        
        quota = CONFIG.get("QUOTA", "").strip().lower()
        is_tq = quota == "tq"

        # PHASE 3 - PASSENGER ROOM
        try:
            if is_tq:
                confirm_checkbox = page.locator("#confirmberths").first
                print("Label count:", await page.locator("label[for='confirmberths']").count())

                await confirm_checkbox.wait_for(
                    state="visible",
                    timeout=10000
                )

                print("Label visible:", await page.locator("label[for='confirmberths']").is_visible())
                if not await confirm_checkbox.is_checked():
                    confirm_label = page.locator(
                        "label[for='confirmberths']"
                    ).first

                    await asyncio.sleep(random.uniform(0.65, 0.95))
                    await confirm_label.click(
                        delay=random.randint(65, 105),
                        timeout=2000,
                        force=True
                    )

                print("Checkbox checked:", await confirm_checkbox.is_checked())

            upi_radio = page.locator("tr.link:has-text('BHIM/UPI') .ui-radiobutton-box").first
            continue_btn = page.locator("button[type='submit'].btnDefault").first

            await upi_radio.wait_for(state="visible", timeout=10000)

            # await asyncio.sleep(random.uniform(1.45, 1.85))
            await asyncio.sleep(random.uniform(0.15, 0.25))

            await upi_radio.click(
                delay=random.randint(65, 105), 
                position={"x": random.randint(3, 7), "y": random.randint(3, 7)},
                timeout=2000, 
                force=True
            )
            
            # await asyncio.sleep(random.uniform(1.65, 2.15))
            await asyncio.sleep(random.uniform(0.15, 0.25))

            await continue_btn.click(
                delay=random.randint(75, 115), 
                position={"x": random.randint(15, 70), "y": random.randint(10, 30)},
                timeout=2000, 
                force=True
            )

        except Exception as e:
            print(f'❌ Passenger room execution failed completely: {e}')


        # PHASE 4 - CAPTCHA PAGE 
        try:
            print("Waiting for captcha page....")

            review_container = page.locator("app-review-booking")
            await review_container.wait_for(state="visible",timeout=0)

            await asyncio.sleep(random.uniform(0.15, 0.35))
            desktop_continue = review_container.locator("button.train_Search:has-text('Continue')")

            if await desktop_continue.is_visible():
                await human_glide_to(page,desktop_continue,global_mouse)
                await desktop_continue.click()
            else:
                print("Specific layout button not explicitly visible, running general fallback selection...")
                fallback_btn = review_container.locator("button[type='submit']:has-text('Continue')").first
                await fallback_btn.click(force=True)
        except Exception as e:
            print(f"Captcha phase error : {e}")

        # PHASE 5 : Payment Phase
        try:
            await page.wait_for_selector('app-payment', timeout=0)

            result = await page.evaluate("""() => {
                return new Promise((resolve, reject) => {

                    let bhimClicked = false;
                    let multipleTabClicked = false;
                    let gatewayClicked = false;
                    let payClicked = false;

                    const observer = new MutationObserver(() => {

                        const tabs = Array.from(document.querySelectorAll('.bank-type'));
                        const bhimTab = tabs.find(el => el.innerText.includes('BHIM'));
                        const multiplePaymentTab = tabs.find(el => el.innerText.includes('Multiple Payment'));

                        const isBhimActive = bhimTab && bhimTab.classList.contains('bank-type-active');
                        const isMultipleActive = multiplePaymentTab && multiplePaymentTab.classList.contains('bank-type-active');

                        // STEP 1: Ensure BHIM tab is active initially
                        if (!isBhimActive && !isMultipleActive && bhimTab && !bhimClicked) {
                            bhimClicked = true;
                            bhimTab.click();
                            return;
                        }

                        // Fetch rendered payment options
                        const gateways = Array.from(document.querySelectorAll('.bank-text'))
                                              .filter(el => el.innerText && el.innerText.trim().length > 0);

                        // Wait until Angular renders text inside options
                        if (gateways.length === 0) return;

                        let targetGateway = null;
                        let gatewayName = "";

                        if (isBhimActive) {
                            const paytmOption = gateways.find(el => el.innerText.toUpperCase().includes('PAYTM'));

                            if (paytmOption) {
                                targetGateway = paytmOption;
                                gatewayName = "PAYTM";
                            } else if (multiplePaymentTab && !multipleTabClicked) {
                                multipleTabClicked = true;
                                multiplePaymentTab.click();
                                return;
                            }
                        }
                        if (isMultipleActive) {
                            
                            const paytmOption = gateways.find(el => el.innerText.toUpperCase().includes('PAYTM'));

                            const phonepeOption = gateways.find(el => el.innerText.toUpperCase().includes('PHONEPE'));
                        
                            if (paytmOption) {
                                targetGateway = paytmOption;
                                gatewayName = "PAYTM";
                            } else if (phonepeOption) {
                                targetGateway = phonepeOption;
                                gatewayName = "PHONEPE";
                            }
                        }                        

                        if (targetGateway && !gatewayClicked) {
                            gatewayClicked = true;
                            const clickableCard = targetGateway.closest('.link') || targetGateway;
                            clickableCard.click();
                        }

                        const payBtn = document.querySelector('button.btn-primary');
                        if (payBtn && !payBtn.disabled && gatewayClicked && !payClicked) {
                            payClicked = true;
                            payBtn.click();

                            observer.disconnect();
                            resolve(gatewayName);
                        }
                    });

                    observer.observe(document.body, {
                        childList: true,
                        subtree: true,
                        characterData: true
                    });

                    // Initial manual check trigger in case options loaded synchronously
                    const initialGateways = Array.from(document.querySelectorAll('.bank-text'))
                                                 .filter(el => el.innerText && el.innerText.trim().length > 0);
                    if (initialGateways.length > 0) {
                        document.body.click(); 
                    }

                    // Timeout lock
                    setTimeout(() => {
                        observer.disconnect();
                        reject("Gateway Selection Timeout under Tatkal load");
                    }, 20000);

                });
            }""")

            print(f"Gateway Selected : {result}")

        except Exception as e:
            print(f'Payment Phase Error: {e}')
    
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