
import asyncio
import re
import time
import sys
from db import init_db, is_posted, save_post
from telegram_link_collector import fetch_links
from scraper_pcnala import PCNalaScraper
from web_poster_market import WebPosterMarket

def extract_id_from_url(url):
    # url: https://pcnala.com/trade/UUID
    match = re.search(r'trade/([a-zA-Z0-9-]+)', url)
    if match:
        return match.group(1)
    return None

async def main():
    sys.stdout.reconfigure(encoding='utf-8')
    print("Starting Market Crawler (PCNala -> API)...", flush=True)
    
    # 1. Init DB
    init_db()
    
    # 2. Collect Links
    print("\n[Phase 1] Collecting Links from Telegram...")
    links = await fetch_links(limit=50)
    
    if not links:
        print("No links found. Exiting.")
        return

    # 3. Process Links
    print(f"\n[Phase 2] Processing {len(links)} links...")
    
    scraper = PCNalaScraper()
    poster = WebPosterMarket()
    
    # Verify Poster Login first
    if not poster.login():
        print("API Login failed. clean exit.")
        return

    new_count = 0
    
    for link in links:
        item_id = extract_id_from_url(link)
        if not item_id:
            print(f"Skipping invalid URL: {link}")
            continue
            
        if is_posted(item_id):
            print(f"Skipping already posted: {item_id}")
            continue
            
        print(f"Processing: {link} (ID: {item_id})")
        
        # Scrape
        data = scraper.parse_detail(link)
        if not data:
            print("Failed to scrape data, skipping.")
            continue
            
        print(f"Scraped Title: {data.get('title')}")
        
        # Post
        success = poster.post_product(data)
        
        if success:
            save_post(item_id, data.get('title', 'Untitled'))
            print("Saved to DB.")
            new_count += 1
        else:
            print("Failed to post to API.")
            
        # Polite delay
        time.sleep(3)

    print(f"\nJob Complete. Posted {new_count} new items.")
    poster.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped by user.")
