import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TARGET_URL = os.getenv("BLACKLIST_TARGET_URL")
SOURCE_CHAT_ID = os.getenv("BLACKLIST_SOURCE_CHAT_ID") # Can be username or ID
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
