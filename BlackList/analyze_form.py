from web_poster import WebPoster
from selenium.webdriver.common.by import By
import time

def analyze():
    poster = WebPoster()
    print("Logging in...")
    if not poster.login():
        print("Login failed")
        return

    print("Navigating to Home...")
    poster.driver.get("https://dool.co.kr/")
    time.sleep(3)
    
    print("Clicking 'Blacklist' in Bottom Nav...")
    # Try different selectors for Bottom Nav "Blacklist"
    try:
        # User said "Blacklist" in bottom nav. 
        # Often bottom nav items are links or buttons.
        # Try finding by text "블랙리스트"
        menu_btn = poster.driver.find_element(By.XPATH, "//*[contains(text(), '블랙리스트')]")
        menu_btn.click()
        time.sleep(3)
    except Exception as e:
        print(f"Failed to click Blacklist menu: {e}")
        return

    print("Clicking 'Register Damage Case'...")
    try:
        # User said "피혜 사례 등록", assuming "피해 사례 등록" or just "등록"
        # We'll look for meaningful keywords
        reg_btn = poster.driver.find_element(By.XPATH, "//*[contains(text(), '사례 등록') or contains(text(), '글쓰기')]")
        reg_btn.click()
        time.sleep(3)
    except Exception as e:
        print(f"Failed to click Register button: {e}")
        # Dump source to debug if button not found
        with open("debug_blacklist_list.html", "w", encoding="utf-8") as f:
            f.write(poster.driver.page_source)
        return
    print("--- Form Field Analysis (Deep) ---")
    
    # 1. Print all labels
    labels = poster.driver.find_elements(By.TAG_NAME, "label")
    for label in labels:
        txt = label.text.strip()
        if txt:
            print(f"LABEL: {txt}")
            # Try to find associated input
            # Check 'for' attribute
            for_attr = label.get_attribute("for")
            if for_attr:
                print(f"  -> Points to ID: {for_attr}")
            else:
                # Check siblings
                siblings = label.find_elements(By.XPATH, "./following-sibling::*")
                for sib in siblings:
                    if sib.tag_name in ['input', 'select', 'textarea']:
                        print(f"  -> Sibling {sib.tag_name}: Placeholder='{sib.get_attribute('placeholder')}'")

    # 2. Print all inputs with placeholders again
    inputs = poster.driver.find_elements(By.TAG_NAME, "input")
    for i in inputs:
        try:
            print(f"INPUT | Type: {i.get_attribute('type')} | Placeholder: {i.get_attribute('placeholder')}")
        except: pass

    textareas = poster.driver.find_elements(By.TAG_NAME, "textarea")
    for t in textareas:
        try:
             print(f"TEXTAREA | Placeholder: {t.get_attribute('placeholder')}")
        except: pass

    # 3. Print all buttons
    print("--- Buttons ---")
    buttons = poster.driver.find_elements(By.TAG_NAME, "button")
    for b in buttons:
        try:
            print(f"BUTTON | Text: '{b.text}' | Class: {b.get_attribute('class')} | Type: {b.get_attribute('type')}")
        except: pass
        
    poster.close()

if __name__ == "__main__":
    analyze()
