import time
import os
import pickle
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import config

LOGIN_URL = "https://dool.co.kr/login"
# The user specified this URL for posting
CREATE_URL = "http://dool.co.kr/blacklist/create" 
COOKIES_FILE = "cookies.pkl"

class WebPoster:
    def __init__(self):
        self.driver = None

    def setup_driver(self):
        if not self.driver:
            options = webdriver.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            # User agent to look like a real browser
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # Persist profile to keep login
            user_data_dir = os.path.join(os.getcwd(), "chrome_profile_blacklist")
            options.add_argument(f"user-data-dir={user_data_dir}")
            
            print(f"Initializing WebDriver with profile: {user_data_dir}")
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def login(self):
        """Handles login. If not logged in, waits for user interaction."""
        self.setup_driver()
        self.driver.get(LOGIN_URL)
        
        # Logic from Market/poster_b.py
        # Not logged in = "Guest 사장님" present
        # Logged in = "XXXX 사장님" present (so "사장님" is there, but "Guest 사장님" is not)
        source = self.driver.page_source
        is_guest = "Guest 사장님" in source
        has_boss_text = "사장님" in source
        
        if has_boss_text and not is_guest:
            print("Already logged in (Verified via '사장님' text).")
            return True
            
        print("Not logged in (Found 'Guest 사장님' or missing '사장님'). Please log in via Telegram.")
        
        # Wait for user to log in
        max_wait = 300 # 5 minutes
        start_time = time.time()
        while time.time() - start_time < max_wait:
            source = self.driver.page_source
            is_guest = "Guest 사장님" in source
            has_boss_text = "사장님" in source
            
            if has_boss_text and not is_guest:
                print("Login detected! ('사장님' found)")
                # Save cookies
                pickle.dump(self.driver.get_cookies(), open(COOKIES_FILE, "wb"))
                return True
            time.sleep(2)
        
        print("Login timed out.")
        return False

    def post_blacklist(self, data, dry_run=False):
        """
        Posts a blacklist item.
        data expects: {'title': str, 'damage_content': str, 'features': str, 'location_city': str, 'location_district': str, 'images': list}
        """
        if not self.login():
            print("Cannot post: Not logged in.")
            return False
            
        # Navigate via clicks (Nuxt.js compatibility)
        print("Navigating to Home...")
        try:
            self.driver.get("https://dool.co.kr/")
            time.sleep(3)
            
            # Click Blacklist
            print("Clicking 'Blacklist'...")
            menu_btn = self.driver.find_element(By.XPATH, "//*[contains(text(), '블랙리스트')]")
            menu_btn.click()
            time.sleep(3)
            
            # Click Register
            print("Clicking 'Register'...")
            reg_btn = self.driver.find_element(By.XPATH, "//*[contains(text(), '사례 등록') or contains(text(), '글쓰기')]")
            reg_btn.click()
            time.sleep(3)
            
        except Exception as e:
            print(f"Navigation failed: {e}")
            return False
        
        # Check login redirect
        if "login" in self.driver.current_url:
            print("Redirected to login. Session might be invalid.")
            return False

        if dry_run:
            print(f"[Dry Run] Data: {data}")
            return True

        try:
            # 0. Date
            from datetime import datetime
            today_str = datetime.now().strftime("%Y-%m-%d")
            incident_date = data.get('incident_date', today_str)
            try:
                date_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='date']")
                # specific format or JS might be needed. JS is safest.
                # Must trigger input event for Vue v-model to update
                self.driver.execute_script("""
                    arguments[0].value = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, date_input, incident_date)
                print(f"Filled Date (JS+Events): {incident_date}")
            except Exception as e:
                print(f"Could not fill date: {e}")

            # 1. Category & Region (Selects)
            # Order: 0=Category, 1=City, 2=District
            city = data.get('location_city', '')
            district = data.get('location_district', '')
            category = data.get('category', 'OTHER')
            
            try:
                selects = self.driver.find_elements(By.TAG_NAME, "select")
                if len(selects) >= 2:
                    # A. Category
                    cat_select = Select(selects[0])
                    try:
                        # AI returns Enum Key (e.g. "NON_PAYMENT"), matching <option value="NON_PAYMENT">
                        cat_select.select_by_value(category)
                        print(f"Selected Category: {category}")
                    except:
                        print(f"Category '{category}' failed. Defaulting to OTHER.")
                        try:
                            cat_select.select_by_value("OTHER")
                        except:
                            pass

                    # B. City
                    if city:
                        city_select = Select(selects[1])
                        city_select.select_by_visible_text(city)
                        print(f"Selected City: {city}")
                        time.sleep(1) # Wait for District to populate
                        
                        # C. District
                        if district and len(selects) >= 3:
                            # Re-fetch selects? No, reference should hold, but DOM updates might require re-fetch if element reduced.
                            # Usually Vue updates the options inside the select, not the select element itself.
                            district_select = Select(selects[2])
                            try:
                                district_select.select_by_visible_text(district)
                                print(f"Selected District: {district}")
                            except:
                                print(f"District '{district}' not found in dropdown.")
            except Exception as e:
                print(f"Error selecting category/region: {e}")

            # 2. Features (Input by placeholder)
            features = data.get('features', '')
            try:
                # Placeholder: '예: 키 약 175cm, 안경 착용'
                feat_input = self.driver.find_element(By.XPATH, "//input[contains(@placeholder, '안경 착용')]")
                feat_input.clear()
                feat_input.send_keys(features)
                print(f"Filled Features: {features}")
            except Exception as e:
                print(f"Could not find Features input: {e}")

            # 3. Content (Textarea by placeholder or tag)
            content = data.get('damage_content', '')
            try:
                # Placeholder: '구체적인 피해 내용을 작성해주세요 (최대 2000자)'
                # Or just first textarea
                if "피해" in content: # Just a check
                     pass
                
                try:
                    textarea = self.driver.find_element(By.XPATH, "//textarea[contains(@placeholder, '피해 내용')]")
                except:
                    textarea = self.driver.find_element(By.TAG_NAME, "textarea")
                
                textarea.clear()
                textarea.send_keys(content)
                print("Filled Content.")
            except Exception as e:
                print(f"Could not find Content textarea: {e}")

            # 4. Images
            images = data.get('images', [])
            if images:
                try:
                    file_input = self.driver.find_element(By.ID, "common-file-input")
                    # Join absolute paths
                    import os
                    abs_paths = [os.path.abspath(p) for p in images]
                    paths_str = "\n".join(abs_paths)
                    file_input.send_keys(paths_str)
                    print(f"Uploaded {len(images)} images.")
                    
                    # Wait for Face API / Blur / OCR processing
                    # The submit button is disabled while 'processingImages' is true in Vue
                    print("Waiting for image optimization (Face-API & OCR) to complete...")
                    try:
                        # Wait up to 120 seconds for processing to finish
                        # EC.element_to_be_clickable checks if element is visible AND enabled.
                        wait = WebDriverWait(self.driver, 120)
                        wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "submit-btn")))
                        print("Image processing complete. Submit button is now enabled.")
                    except TimeoutException:
                        print("Warning: Image processing timed out after 120s. Attempting to proceed anyway.")
                except Exception as e:
                    print(f"Image upload failed: {e}")

            # 5. Submit
            submit_btn = None
            try:
                # Look for "등록 완료" by text or class
                # Method 1: Class
                try:
                    submit_btn = self.driver.find_element(By.CLASS_NAME, "submit-btn")
                except:
                    # Method 2: Text
                    submit_btn = self.driver.find_element(By.XPATH, "//button[contains(., '등록 완료')]")
            except:
                pass
            
            if submit_btn:
                # Use JS Click to avoid interception
                self.driver.execute_script("arguments[0].click();", submit_btn)
                print("Clicked submit button (JS).")
                
                # Handle Alert 1: Confirmation
                try:
                    WebDriverWait(self.driver, 5).until(EC.alert_is_present())
                    alert = self.driver.switch_to.alert
                    print(f"Alert 1 (Confirm): {alert.text}")
                    alert.accept()
                except TimeoutException:
                    print("Alert 1 not found (timed out).")

                # Handle Alert 2: Success (Wait for network request, so give it more time)
                try:
                    # Give it 30 seconds for image upload and server processing
                    WebDriverWait(self.driver, 30).until(EC.alert_is_present())
                    alert = self.driver.switch_to.alert
                    print(f"Alert 2 (Success): {alert.text}")
                    alert.accept()
                except TimeoutException:
                    print("Alert 2 not found (timed out/server slow?).")

                time.sleep(3)
                return True
            else:
                print("Could not find Submit button.")
                return False

        except Exception as e:
            print(f"Error during posting: {e}")
            return False

    def close(self):
        if self.driver:
            self.driver.quit()
