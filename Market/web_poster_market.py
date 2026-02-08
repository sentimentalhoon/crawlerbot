
import requests
import hmac
import hashlib
import json
import time
import os
import os
from dotenv import load_dotenv

load_dotenv()

class WebPosterMarket:
    def __init__(self):
        # Allow override of base URL via env or config, default to production
        self.base_url = "https://dool.co.kr/api" 
        self.session = requests.Session()
        self.token = None
        
        # Headers (Mimic Browser but keep it clean)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://dool.co.kr/",
            "Origin": "https://dool.co.kr",
            "Accept": "application/json, text/plain, */*"
        })

    def login(self, user_data=None):
        """
        Logs in via /api/auth/telegram.
        """

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            print("Error: TELEGRAM_BOT_TOKEN missing.")
            return False

        if not user_data:
             # Default to a "Crawler Admin" persona
             # Use a generic ID suitable for crawler operations
             user_data = {
                 "id": 123456789, 
                 "first_name": "Crawler", 
                 "username": "crawler_bot", 
                 "photo_url": "",
                 "auth_date": int(time.time())
             }
        else:
            user_data["auth_date"] = int(time.time())

        # 1. Create Data-Check-String
        keys = sorted([k for k in user_data.keys() if k != "hash"])
        data_check_string = "\n".join([f"{k}={user_data[k]}" for k in keys])
        
        
        # 2. Secret Key
        secret_key = hashlib.sha256(token.encode()).digest()
        
        # 3. Hash
        hash_value = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        user_data["hash"] = hash_value
        
        print(f"Logging in as {user_data.get('username')}...")
        try:
            resp = self.session.post(
                f"{self.base_url}/auth/telegram",
                data=user_data 
            )
            resp.raise_for_status()
            
            data = resp.json()
            self.token = data['token']['accessToken']
            
            # Set Authorization Header
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}"
            })
            print("Login successful! Token acquired.")
            return True
            
        except Exception as e:
            print(f"Login failed: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Server Response: {e.response.text}")
            return False

    def post_product(self, data, dry_run=False):
        """
        Posts a product to the market.
        data: dict with 'title', 'description', 'realEstate', 'images' (list of urls or paths)
        """
        if not self.token:
            if not self.login():
                return False

        if dry_run:
            print(f"[API Dry Run] Data: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return True

        # Prepare Payload
        # Extract images from data to handle separately
        image_urls = data.pop('images', [])
        
        # Ensure category is set (default PC_BUSINESS)
        data['category'] = "PC_BUSINESS"
        
        # Calculate price if missing (Deposit + Rights)
        if 'price' not in data:
            d = data.get('realEstate', {}).get('deposit', 0)
            r = data.get('realEstate', {}).get('rightsMoney', 0)
            data['price'] = d + r

        # Files handling
        files_to_upload = []
        opened_files = [] 
        temp_files = [] # For downloaded images

        try:
            multipart_data = [] 
            
            # 1. JSON Data -> 'product' field
            multipart_data.append(('product', (None, json.dumps(data), 'application/json')))
            
            # 2. Images
            # If images are URLs, we need to download them first
            import tempfile
            
            # Limit images count
            MAX_IMAGES = 20
            for i, img_src in enumerate(image_urls[:MAX_IMAGES]):
                try:
                    fp = None
                    filename = f"image_{i}.jpg"
                    
                    if img_src.startswith("http"):
                        # Download
                        import urllib3
                        urllib3.disable_warnings() 
                        r = requests.get(img_src, stream=True, verify=False)
                        if r.status_code == 200:
                            tf = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                            tf.write(r.content)
                            tf.close()
                            temp_files.append(tf.name)
                            fp = open(tf.name, 'rb')
                            filename = os.path.basename(img_src).split('?')[0] or f"image_{i}.jpg"
                    elif os.path.exists(img_src):
                        # Local file
                        fp = open(img_src, 'rb')
                        filename = os.path.basename(img_src)
                    
                    if fp:
                        opened_files.append(fp)
                        # field name 'file' for all images (List<MultipartFile>)
                        multipart_data.append(('file', (filename, fp, "image/jpeg")))
                        print(f"Attached image {i}: {filename}")
                        
                except Exception as e:
                    print(f"Error preparing image {img_src}: {e}")

            print(f"Sending POST to {self.base_url}/v1/market/products ...")
            
            resp = self.session.post(
                f"{self.base_url}/v1/market/products",
                files=multipart_data
            )
            
            if resp.status_code != 200 and resp.status_code != 201:
                print(f"Failed Status: {resp.status_code}")
                # print(resp.text)
                resp.raise_for_status()
                
            print("Post success!", resp.json())
            return True

        except Exception as e:
            print(f"Post failed: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return False
            
        finally:
            # Close files
            for f in opened_files:
                f.close()
            # Clean temp files
            for p in temp_files:
                try:
                    os.remove(p)
                except:
                    pass

    def close(self):
        self.session.close()
