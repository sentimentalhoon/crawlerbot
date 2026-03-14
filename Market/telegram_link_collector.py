
import os
import re
import sys

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telethon import TelegramClient

sys.stdout.reconfigure(encoding='utf-8')

# Load root .env
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

api_id_value = os.getenv("API_ID", "").strip()
API_ID = int(api_id_value) if api_id_value.isdigit() else 0
API_HASH = os.getenv("API_HASH")
SOURCE_CHAT = os.getenv("MARKET_SOURCE_CHAT_ID", "@pcnara_ch").strip()

if SOURCE_CHAT and not SOURCE_CHAT.startswith("@") and not SOURCE_CHAT.lstrip("-").isdigit():
    SOURCE_CHAT = f"@{SOURCE_CHAT}"

# Persist session locally when Telegram user credentials are available.
client = TelegramClient('market_session', API_ID, API_HASH) if API_ID and API_HASH else None

# State file mapping: Source Chat -> Last ID
LAST_ID_FILE = "last_msg_id.txt"
TRADE_URL_REGEX = re.compile(r'https?://[^\s)]+/trades?/[a-zA-Z0-9-]+', re.IGNORECASE)

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

def extract_links_from_telethon_message(message):
    found_in_msg = []

    if message.buttons:
        for row in message.buttons:
            for btn in row:
                if hasattr(btn, 'url') and btn.url and TRADE_URL_REGEX.search(btn.url):
                    found_in_msg.append(btn.url)

    if not found_in_msg and message.entities:
        for ent in message.entities:
            if hasattr(ent, 'url') and ent.url and TRADE_URL_REGEX.search(ent.url):
                found_in_msg.append(ent.url)

    if not found_in_msg and message.text:
        found_in_msg.extend(TRADE_URL_REGEX.findall(message.text))

    return found_in_msg

def extract_links_from_public_post(post):
    found_in_post = []

    for anchor in post.select(".tgme_widget_message_inline_button.url_button[href], .tgme_widget_message_text a[href]"):
        href = anchor.get("href")
        if href and TRADE_URL_REGEX.search(href):
            found_in_post.append(href)

    if not found_in_post:
        found_in_post.extend(TRADE_URL_REGEX.findall(post.get_text(" ", strip=True)))

    return found_in_post

async def fetch_links_via_telethon(limit, last_id):
    if not client:
        print("Telegram API credentials are missing. Falling back to public channel HTML.")
        return None, last_id

    links = []
    max_id_found = last_id

    try:
        await client.connect()

        if not await client.is_user_authorized():
            print("No authorized Telegram user session. Falling back to public channel HTML.")
            return None, last_id

        me = await client.get_me()
        if getattr(me, "bot", False):
            print("Telegram session is a bot account. Falling back to public channel HTML.")
            return None, last_id

        entity = await client.get_entity(SOURCE_CHAT)
        print(f"Fetching messages via Telegram session... (Resume from ID: {last_id})")

        async for message in client.iter_messages(entity, limit=limit, min_id=last_id):
            if message.id > max_id_found:
                max_id_found = message.id

            if not (message.text or message.buttons):
                continue

            for link in extract_links_from_telethon_message(message):
                if link not in links:
                    links.append(link)
                    print(f"Found: {link}")

    except Exception as e:
        print(f"Error fetching messages via Telegram: {e}")
        return None, last_id
    finally:
        await client.disconnect()

    return links, max_id_found

def fetch_links_via_public_channel(limit, last_id):
    username = SOURCE_CHAT[1:] if SOURCE_CHAT.startswith("@") else ""
    if not username:
        print("Public channel fallback requires MARKET_SOURCE_CHAT_ID to be a public @username.")
        return [], last_id

    print(f"Fetching messages via public channel HTML... (Resume from ID: {last_id})")

    links = []
    max_id_found = last_id
    before_id = None
    processed_posts = 0

    while processed_posts < limit:
        page_url = f"https://t.me/s/{username}"
        if before_id is not None:
            page_url = f"{page_url}?before={before_id}"

        try:
            response = requests.get(
                page_url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=20,
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Error fetching public channel page: {e}")
            break

        soup = BeautifulSoup(response.text, "html.parser")
        posts = soup.select(".tgme_widget_message")
        if not posts:
            break

        post_ids = []

        for post in posts:
            data_post = post.get("data-post", "")
            try:
                message_id = int(data_post.rsplit("/", 1)[-1])
            except (IndexError, ValueError):
                continue

            post_ids.append(message_id)
            if message_id <= last_id:
                continue

            processed_posts += 1
            if message_id > max_id_found:
                max_id_found = message_id

            for link in extract_links_from_public_post(post):
                if link not in links:
                    links.append(link)
                    print(f"Found: {link}")

            if processed_posts >= limit:
                break

        if not post_ids:
            break

        oldest_id = min(post_ids)
        if oldest_id <= last_id or processed_posts >= limit or before_id == oldest_id:
            break

        before_id = oldest_id

    return links, max_id_found

async def fetch_links(limit=500):
    print(f"Preparing Telegram fetch... Target: {SOURCE_CHAT}")
    last_id = load_last_id()

    links, max_id_found = await fetch_links_via_telethon(limit, last_id)
    if links is None:
        links, max_id_found = fetch_links_via_public_channel(limit, last_id)

    if max_id_found > last_id:
        save_last_id(max_id_found)
        print(f"Updated last processed ID to {max_id_found}")

    print(f"Total unique links found: {len(links)}")
    return links

if __name__ == "__main__":
    import asyncio
    links = asyncio.run(fetch_links())
    print("Done.")
