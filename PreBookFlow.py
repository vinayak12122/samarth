import random
import asyncio
from datetime import datetime,timedelta

async def humanClick(page, locator):
    await locator.wait_for(state="visible", timeout=10000)
    await locator.scroll_into_view_if_needed()
    
    await page.wait_for_timeout(random.randint(150, 300))
    
    box = await locator.bounding_box()
    if not box:
        await locator.hover()
        box = await locator.bounding_box()
        if not box:
            raise Exception("Element has no physical size or is hidden.")

    target_x = box["x"] + box["width"] * random.uniform(0.2, 0.8)
    target_y = box["y"] + box["height"] * random.uniform(0.2, 0.8)
    
    await page.mouse.move(target_x, target_y, steps=random.randint(12, 22))
    
    await page.wait_for_timeout(random.randint(50, 100))

    await page.mouse.down()
    await page.wait_for_timeout(random.randint(60, 140)) 
    await page.mouse.up()
    await page.wait_for_timeout(random.randint(100, 200))

def getNextDayDate():

    next_day = datetime.now() + timedelta(days=2)

    return next_day.strftime("%d/%m/%Y")

async def PerformPreBook(page,credentials:dict):
    try:
        print("\n Perfroming Pre Booking Flow...\n")

        await asyncio.sleep(1)
        # =====================================================
        # LOGIN
        # =====================================================

        login_button = page.locator('a.search_btn.loginText')
        await humanClick(page,login_button)

        await page.wait_for_timeout(
            random.randint(800, 1500)
        )

        username_input = page.locator(
            'input[placeholder="User Name"]'
        )

        await username_input.click()

        await username_input.fill(
            credentials["username"]
        )

        await page.wait_for_timeout(
            random.randint(300, 800)
        )

        password_input = page.locator(
            'input[placeholder="Password"]'
        )

        await password_input.click()

        await password_input.fill(
            credentials["password"]
        )

        await page.wait_for_timeout(
            random.randint(300, 800)
        )

        sign_in_button = page.locator(
            'button:has-text("SIGN IN")'
        )

        await humanClick(page,sign_in_button)

        # =====================================================
        # JOURNEY DETAILS
        # =====================================================

        from_input = page.locator('input[aria-label="Enter From station. Input is Mandatory."]')
        await from_input.click()

        await from_input.fill("NZM")

        await page.wait_for_timeout(
            random.randint(700, 1200)
        )

        # await page.keyboard.press("ArrowDown")
        await page.keyboard.press("Enter")

        # ============ TO =================

        to_input = page.locator(
            'input[aria-label="Enter To station. Input is Mandatory."]'
        )

        await to_input.click(timeout=0)

        await to_input.fill("BDTS")

        await page.wait_for_timeout(
            random.randint(700, 1200)
        )

        # await page.keyboard.press("ArrowDown")
        await page.keyboard.press("Enter")

        # ============ DATE ===========

        next_day_date = getNextDayDate()

        date_input = page.locator(
            'input[placeholder=""]'
        ).nth(0)

        await date_input.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")

        await date_input.press_sequentially(next_day_date)

        print(f"Journey Date : {next_day_date}")

        active_date = page.locator('td.ui-datepicker-current-day a.ui-state-active')

        await active_date.wait_for(state="visible",timeout=5000)

        await humanClick(page,active_date)

        await page.wait_for_timeout(random.randint(400, 800))

        # ============= QUOTA =============

        quota_dropdown = page.locator(
            '#journeyQuota'
        )

        await humanClick(page,quota_dropdown)

        await page.wait_for_timeout(
            random.randint(500, 900)
        )

        general_option = page.locator(
            'li[aria-label="GENERAL"]'
        )

        await humanClick(page,general_option)

        # =============== SUBMIT ===========

        search_button = page.locator(
            'button:has-text("Search Trains")'
        )

        await humanClick(page,search_button)


        # =====================================================
        # TRAIN SELECTION
        # =====================================================

        train_heading_xpath = f"//div[contains(@class,'train-heading')]//strong[contains(text(), '12904')]"

        await page.wait_for_selector(train_heading_xpath,timeout=15000)


        train_box = page.locator("div.bull-back").filter(has=page.locator(f"strong:has-text('12904')"))

        date_obj = datetime.strptime(next_day_date, "%d/%m/%Y")
        day_date_str = date_obj.strftime("%d %b")

        refresh_btn = train_box.locator(
                "div.pre-avl"
            ).filter(
                has_text="Sleeper (SL)"
            ).locator(
                "text=Refresh"
            ).first

        await humanClick(page,refresh_btn)



        avail_slot = train_box.locator(
                    "td.link div.pre-avl"
                ).filter(
                    has_text=day_date_str
                ).first
        
        book_btn = train_box.locator(
                    "button:has-text('Book Now')"
                ).first
        
        await avail_slot.wait_for(state="visible",timeout=10000)
        
        await humanClick(page,avail_slot)
        await humanClick(page,book_btn)

        # =====================================================
        # PASSENGER FILLING AND SUBMITION
        # =====================================================

        first_input = page.locator(
            'input[placeholder="Name"]'
        ).first
        
        await first_input.wait_for(
            state="visible",
            timeout=15000
        )

        await first_input.click()

        await page.wait_for_timeout(
            random.randint(100, 300)
        )

        master_list = page.locator(
            'li.ui-autocomplete-list-item'
        )

        passenger_count = await master_list.count()

        print(f"Passengers Found : {passenger_count}")

        if passenger_count == 0:
            raise Exception("No passengers found in master list")
        
        for passenger in range(passenger_count):
            if passenger > 0:

                add_passenger_btn = page.locator(
                    'span.prenext'
                ).filter(
                    has_text="+ Add Passenger"
                )

                await add_passenger_btn.click()

            current_input = page.locator(
                'input[placeholder="Name"]'
            ).nth(passenger)

            await current_input.wait_for(
                state="visible"
            )

            await current_input.click()

            await page.wait_for_timeout(
                random.randint(300,600)
            )

            dropdown_items = page.locator(
                'li.ui-autocomplete-list-item'
            )

            current_item = dropdown_items.first

            await current_item.wait_for(
                state="visible"
            )

            await current_item.click()

            await page.wait_for_timeout(
                random.randint(100, 300)
            )

        continueBtn = page.locator(
            'button.train_Search.btnDefault'
        ).filter(
            has_text="Continue"
        )

        await continueBtn.wait_for(
            state="visible",
            timeout=10000
        )

        await humanClick(page,continueBtn)

        # =====================================================
        # PASSENGER FILLING AND SUBMITION
        # =====================================================

        await page.wait_for_url(
            "**/reviewBooking",
            timeout=90000
        )

        home_btn = page.locator(
            'a[aria-label="Home icon"]'
        )

        await asyncio.sleep(1)

        await home_btn.wait_for(
            state="visible",
            timeout=60000
        )

        # print("Review page loaded")

        await humanClick(page, home_btn)

        print("Pre Booking FLow Has Finished....")
    except Exception as e :
        print(f"PreBook/Login Flow Failed : {e}")