import os
import cv2
import base64
import numpy as np
import logging

os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
os.environ['FLAGS_use_onednn'] = '0'
logging.getLogger("ppocr").setLevel(logging.ERROR)

from paddlex import create_predictor

predictor = create_predictor(
    model_name='PP-OCRv4_mobile_rec', 
    model_dir='./inference_model_final', 
    device='cpu'
)

img_path = 'E:/Coding Documents/samarth/data/captcha_13.png'
dummy_img = cv2.imread(img_path)

list(predictor(dummy_img))
print("[+] Model warmed up & ready....")

def Solver(b64_string):
    try:

        if not b64_string:
            return ""
        
        header_end = b64_string.find(',')
        if header_end != -1:
            b64_string = b64_string[header_end+1:]

        img_data = base64.b64decode(b64_string)
        nparr = np.frombuffer(img_data,np.uint8)
        img = cv2.imdecode(nparr,cv2.IMREAD_COLOR)

        result_gen = predictor(img)

        for result in result_gen:
            text = result.get('rec_text', '')
            return str(text)
    except Exception as e:
        print(f'Solver Error : {e}')
        return ''



# PHASE 1 - FROM - TO
        # for field, station in [("From", CONFIG["FROM_STATION"]), ("To",     CONFIG["TO_STATION"])]:
        #     el = page.locator(f'input[aria-label="Enter {field} station.     Input is Mandatory."]')
        #     await el.click()
        #     await page.keyboard.press("Control+A")
        #     await page.keyboard.press("Backspace")
        #     await el.fill(station)
    
        #     await page.locator("ul[role='listbox'] li").first.click()
        #     await page.keyboard.press("Enter")
        #     await asyncio.sleep(0.3)
    
        # DATE
        # await page.locator('p-calendar input').click()
        # await page.keyboard.press("Control+A")
        # await page.keyboard.press("Backspace")
        # await page.locator('p-calendar input').type(CONFIG    ["TRAVEL_DATE"])
        # await page.keyboard.press("Escape")
    
        # CLASS
        # await page.locator("p-dropdown[formcontrolname='journeyClass']").    click()
        # await page.locator(f"p-dropdownitem li[aria-label='{CONFIG    ['TRAVEL_CLASS']}']").click()
    
        # QUOTA
        # await page.locator("p-dropdown[formcontrolname='journeyQuota']").    click()
        # quota_option = page.locator(f"p-dropdownitem li[aria-label='    {CONFIG['QUOTA']}']")
        # await quota_option.wait_for(state="visible")
        # await quota_option.click()
    
        # print("Search Trains...")
        # search_btn = page.locator('button.search_btn.    train_Search:has-text("Search Trains")')
        
        # await search_btn.click(force=True)