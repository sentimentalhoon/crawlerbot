from telethon import TelegramClient, events
import config
import asyncio

# Initialize Client
client = TelegramClient('session_name', config.API_ID, config.API_HASH)

async def start_client():
    await client.start()
    print("Telegram Client Started!")
    print("Listening for messages...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    # Test run
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_client())
