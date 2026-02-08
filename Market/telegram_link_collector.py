
import os
import re
import sys
from telethon import TelegramClient, events
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

# Load local .env
load_dotenv()

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH")
SOURCE_CHAT = os.getenv("SOURCE_CHAT_ID", "holempub_adultpc")

if not API_ID:
    print("Error: API_ID not found in .env")
    exit(1)

# Persist session locally
client = TelegramClient('market_session', API_ID, API_HASH)

# State file mapping: Source Chat -> Last ID
LAST_ID_FILE = "last_msg_id.txt"

def load_last_id():
    if os.path.exists(LAST_ID_FILE):
        try:
            with open(LAST_ID_FILE, "r") as f:
                return int(f.read().strip())
        except:
            pass
    return 0

def save_last_id(last_id):
    with open(LAST_ID_FILE, "w") as f:
        f.write(str(last_id))

async def fetch_links(limit=500):
    print(f"Connecting to Telegram... Target: {SOURCE_CHAT}")
    # User account login (interactive for first time)
    await client.start()
    
    last_id = load_last_id()
    print(f"Fetching messages... (Resume from ID: {last_id})")
    
    links = []
    max_id_found = last_id
    
    try:
        # Use min_id to fetch only new messages
        # reverse=True means Oldest -> Newest (good for catch-up), 
        # but iter_messages default is Newest -> Oldest. 
        # If we use min_id in default mode (Newest->Oldest), it stops when it hits min_id.
        # But we want to find ALL new messages.
        # Efficient way: Newest -> Oldest until min_id is reached.
        
        async for message in client.iter_messages(SOURCE_CHAT, limit=limit, min_id=last_id):
            # Track max ID to update state later
            if message.id > max_id_found:
                max_id_found = message.id
            
            if message.text or message.buttons:
                found_in_msg = []
                
                # Check buttons (Priority: "상세보기")
                if message.buttons:
                     for row in message.buttons:
                         for btn in row:
                             # User said button name is "상세보기"
                             if "상세보기" in btn.text:
                                 if hasattr(btn, 'url') and btn.url:
                                     found_in_msg.append(btn.url)
                
                # If no button found, check text entities fallback
                if not found_in_msg and message.entities:
                    for ent in message.entities:
                        if hasattr(ent, 'url') and ent.url and 'pcnala.com/trade/' in ent.url:
                             found_in_msg.append(ent.url)

                # Regex fallback
                if not found_in_msg and message.text:
                    regex_matches = re.findall(r'(https://pcnala\.com/trade/[a-zA-Z0-9-]+)', message.text)
                    found_in_msg.extend(regex_matches)
                
                for link in found_in_msg:
                    if link not in links:
                        links.append(link)
                        print(f"Found: {link}") # Print immediately
                            
    except Exception as e:
        print(f"Error fetching messages: {e}")
    
    if max_id_found > last_id:
        save_last_id(max_id_found)
        print(f"Updated last processed ID to {max_id_found}")
        
    print(f"Total unique links found: {len(links)}")
    return links

if __name__ == "__main__":
    import asyncio
    links = asyncio.run(fetch_links())
    print("Done.")
