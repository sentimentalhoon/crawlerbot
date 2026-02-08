import os
import asyncio
from telethon import TelegramClient, events
import config
from web_poster_api import WebPosterAPI
from ai_optimizer import AIOptimizer
from db import init_db, is_posted, save_posted, save_pending, get_pending_items, mark_item_posted
import re
import argparse

# Initialize Telegram Client
client = TelegramClient('blacklist_session', config.API_ID, config.API_HASH)

# Initialize Web Poster
poster = WebPosterAPI()

# Initialize AI Optimizer
optimizer = AIOptimizer()

# Track processed albums to avoid duplicates (In-memory cache for current session)
processed_groups = set()

# Helper to process text
def process_text(title, text):
    """
    Clean up text using AI.
    """
    print("Optimizing content with AI...")
    result = optimizer.optimize_content(title, text)
    return result # Returns dict

import hashlib

# Helper for file hashing
def calculate_file_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

async def process_message(message):
    """
    Common function to process a message (New or History).
    Handles Albums (grouped_id).
    """
    chat_id = message.chat_id
    msg_id = message.id
    
    # 1. Check Group (Album)
    grouped_id = message.grouped_id
    group_messages = []
    
    if grouped_id:
        if grouped_id in processed_groups:
            return # Already processed this album
        
        print(f"Detected Album (Group ID: {grouped_id}). Fetching related messages...")
        processed_groups.add(grouped_id)
        
        # Fetch neighbors to find the rest of the album
        batch = await client.get_messages(message.chat_id, min_id=msg_id - 10, max_id=msg_id + 11)
        group_messages = [m for m in batch if m.grouped_id == grouped_id]
        
        # Sort by ID to keep order
        group_messages.sort(key=lambda x: x.id)
        
        if message not in group_messages:
            group_messages.append(message)
            
    else:
        # Single message
        group_messages = [message]

    # 2. Check Deduplication (Any msg in group posted OR pending?)
    primary_msg = group_messages[0]
    
    if any(is_posted(m.id, chat_id) for m in group_messages):
        print(f"Skipping already processed/posted item (ID: {primary_msg.id}, Group: {grouped_id})")
        return

    # 3. Consolidate Content & Media
    full_text = ""
    image_paths = []
    seen_hashes = set()
    
    for m in group_messages:
        # Text
        if m.text:
            full_text += m.text + "\n"
        
        # Media
        if m.media:
            try:
                # Use unique filename per message
                path = await m.download_media(file=os.path.join("images", f"{chat_id}_{m.id}"))
                if path:
                    # Deduplication Check
                    file_hash = calculate_file_hash(path)
                    if file_hash in seen_hashes:
                         print(f"Duplicate image detected (Hash: {file_hash}). Removing {path}...")
                         os.remove(path)
                    else:
                         print(f"Downloaded media: {path}")
                         image_paths.append(path)
                         seen_hashes.add(file_hash)
            except Exception as e:
                print(f"Error downloading media for {m.id}: {e}")

    full_text = full_text.strip()
    
    if not full_text and not image_paths:
        return # Skip empty

    # 4. Processing Logic (AI)
    lines = full_text.split('\n')
    raw_title = lines[0] if lines else "Untitled"
    if len(raw_title) > 50: raw_title = raw_title[:50] + "..."
    
    ai_data = process_text(raw_title, full_text)
    
    # Add messages images
    ai_data['images'] = image_paths
    
    final_title = ai_data.get('title', raw_title)
    
    # 5. Extract Incident Date
    incident_date = primary_msg.date.strftime("%Y-%m-%d")
    
    print(f"Processed & Saved to Pending: {final_title} (ID: {primary_msg.id}, Date: {incident_date})")
    
    # 6. Save to Pending DB (Do NOT Post yet)
    save_pending(primary_msg.id, chat_id, ai_data, image_paths, incident_date)

# Removed @client.on(events.NewMessage) -> We are now doing batch processing mostly.
# If we want live monitoring + auto-pending, we can uncomment it, but user asked for "Collect -> Review".

# State file mapping: Source Chat -> Last ID/Offset
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

async def start_history_fetch():
    target = config.SOURCE_CHAT_ID
    last_id = load_last_id()
    
    print(f"Fetching history from {target} (Reverse Order: Oldest -> Newest)...")
    print(f"Resuming from Message ID: {last_id}")
    
    count = 0
    max_id_seen = last_id
    
    try:
        # Use min_id to skip old messages
        async for message in client.iter_messages(target, reverse=True, min_id=last_id):
           if message.id > max_id_seen:
               max_id_seen = message.id
               
           if message.text or message.media:
               await process_message(message)
               count += 1
               
        # Save the new max ID after successful fetch
        if max_id_seen > last_id:
            save_last_id(max_id_seen)
            print(f"Updated checkpoint to ID: {max_id_seen}")
            
    except Exception as e:
        print(f"Error fetching history: {e}")
    
    print(f"History fetch complete. Processed/Checked {count} messages.")

async def interactive_review(auto_confirm=False):
    print("\n" + "="*40)
    print("      REVIEW AND POSTING PHASE")
    print("="*40)
    
    pending_items = get_pending_items()
    count = len(pending_items)
    
    if count == 0:
        print("No pending items to post.")
        return

    print(f"Found {count} pending items ready for upload.")
    
    if auto_confirm:
        print("Auto-confirm enabled (--yes). Proceeding with registration.")
        choice = 'y'
    else:
        # Ask for user permission
        while True:
            choice = input("Would you like to register these items? (y/n): ").strip().lower()
            if choice in ['y', 'n']:
                break
            
    if choice == 'n':
        print("Operation cancelled. Data remains in Pending state.")
        return
        
    print(f"Starting upload of {count} items...")
    
    # Initialize Web Poster only when needed
    if not poster.login():
        print("Login failed. Aborting upload.")
        return

    success_count = 0
    fail_count = 0
    
    for item in pending_items:
        ai_data = item['ai_data']
        # Pass the incident date from DB to AI data so poster can use it
        ai_data['incident_date'] = item.get('incident_date')
        
        print(f"Posting: {ai_data.get('title')} (Original Date: {ai_data['incident_date']})...")
        
        # Use ThreadPoolExecutor for blocking Selenium (or loop.run_in_executor)
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, poster.post_blacklist, ai_data, False)
        
        if success:
            print(" -> Success!")
            mark_item_posted(item['id'], item['message_id'], item['chat_id'], ai_data.get('title'))
            success_count += 1
            
            # Clean up local images to save space
            if 'image_paths' in item:
                for img_path in item['image_paths']:
                    try:
                        if os.path.exists(img_path):
                            os.remove(img_path)
                            print(f"Deleted temp image: {img_path}")
                    except Exception as e:
                        print(f"Error deleting image {img_path}: {e}")
        else:
            print(" -> Failed.")
            fail_count += 1
            
    print(f"\nBatch processing complete. Success: {success_count}, Failed: {fail_count}")

async def main():
    parser = argparse.ArgumentParser(description="BlackList Crawler & Poster")
    parser.add_argument('-y', '--yes', action='store_true', help="Auto-confirm registration (non-interactive mode)")
    args = parser.parse_args()

    print("Starting Crawler (Batch Mode)...")
    
    # 0. Init DB
    init_db()

    # 1. Start Telegram Client
    print("Starting Telegram Client...")
    await client.start()
    
    # 2. Collection Phase
    print("\n[Phase 1] Collecting Data...")
    await start_history_fetch()
    
    # 3. Review & Post Phase
    print("\n[Phase 2] Review process...")
    await interactive_review(auto_confirm=args.yes)
    
    print("\nAll tasks done. Exiting.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        poster.close()
