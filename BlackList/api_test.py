from web_poster_api import WebPosterAPI
import os

def test_api():
    poster = WebPosterAPI()
    
    # 1. Login Test
    # Using a random large ID to avoid conflict, or maybe a known ID if possible.
    # If the server allows any authenticated user to post, this should work.
    user_data = {
         "id": 5999999999, # Random ID
         "first_name": "API_Tester", 
         "username": "api_test_bot", 
         "photo_url": ""
    }
    
    if not poster.login(user_data):
        print("Login failed. Check Bot Token or Server Logs.")
        return

    # 2. Post Test with Dummy Image
    # Create valid dummy image
    img_path = os.path.abspath("test_upload.jpg")
    if not os.path.exists(img_path):
        import shutil
        # Use an existing image from images folder if possible
        existing = [f for f in os.listdir("images") if f.endswith(".jpg")]
        if existing:
            shutil.copy(os.path.join("images", existing[0]), img_path)
            print(f"Copied {existing[0]} to {img_path}")
        else:
            print("No images found to test.")
            return

    data = {
        'category': 'NON_PAYMENT',
        'location_city': '서울',
        'location_district': '강남구',
        'features': 'API Automated Test',
        'damage_content': 'This is a test post from the API Poster. Please ignore or delete.',
        'incident_date': '2023-01-01',
        'images': [img_path]
    }

    print("Attempting to post...")
    poster.post_blacklist(data)
    
    poster.close()
    
    # Cleanup
    if os.path.exists(img_path):
        os.remove(img_path)

if __name__ == "__main__":
    test_api()
