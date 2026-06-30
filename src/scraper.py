"""
src/scraper.py
Scrapes Ethiopian medical Telegram channels with auto-reconnect support.
"""

import os
import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto
from telethon.errors import FloodWaitError
from telethon.network import ConnectionTcpMTProxyRandomizedIntermediate

load_dotenv()

API_ID   = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
PHONE    = os.getenv("TELEGRAM_PHONE", "")

CHANNELS = [
    {"username": "lobelia4cosmetics", "display_name": "Lobelia_Cosmetics"},
    {"username": "tikvahethiopia",    "display_name": "Tikvah_Pharma"},
    {"username": "CheMed123",         "display_name": "CheMed"},
    {"username": "DoctorsET",         "display_name": "DoctorsET"},
    {"username": "yetenaweg",         "display_name": "YetenaWeg"},
]

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "raw"
LOG_DIR  = BASE_DIR / "logs"
SESSION  = str(BASE_DIR / "telegram_session")

LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

logger.add(
    str(LOG_DIR / f"scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    rotation="10 MB", level="INFO"
)


def get_date_partition(dt):
    return dt.strftime("%Y-%m-%d")


def ensure_dirs(channel_name, date_str):
    json_dir  = DATA_DIR / "telegram_messages" / date_str
    image_dir = DATA_DIR / "images" / channel_name
    json_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)
    return json_dir, image_dir


def message_to_dict(msg, channel_name, image_path):
    return {
        "message_id":   msg.id,
        "channel_name": channel_name,
        "message_date": msg.date.isoformat() if msg.date else None,
        "message_text": msg.message or "",
        "has_media":    msg.media is not None,
        "image_path":   image_path,
        "views":        msg.views    or 0,
        "forwards":     msg.forwards or 0,
        "scraped_at":   datetime.now(timezone.utc).isoformat(),
    }


def save_to_data_lake(records, channel_name):
    """Save records to partitioned JSON files. Skips duplicates."""
    if not records:
        return

    by_date = {}
    for r in records:
        date_key = r["message_date"][:10] if r["message_date"] else "unknown"
        by_date.setdefault(date_key, []).append(r)

    for date_str, day_records in by_date.items():
        json_dir, _ = ensure_dirs(channel_name, date_str)
        out_file = json_dir / f"{channel_name}.json"

        existing = []
        if out_file.exists():
            try:
                existing = json.loads(out_file.read_text())
            except json.JSONDecodeError:
                pass

        existing_ids = {r["message_id"] for r in existing}
        new_records  = [r for r in day_records if r["message_id"] not in existing_ids]
        merged       = existing + new_records
        out_file.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"  Saved {len(new_records)} new records → {out_file}")


async def safe_download_image(client, msg, image_dir):
    """Download image with retries. Returns path or None."""
    if not isinstance(msg.media, MessageMediaPhoto):
        return None
    for attempt in range(3):
        try:
            file_path = image_dir / f"{msg.id}.jpg"
            await client.download_media(msg.media, file=str(file_path))
            return str(file_path.relative_to(BASE_DIR))
        except Exception:
            if attempt < 2:
                await asyncio.sleep(3)
            return None


async def scrape_channel(client, channel, limit=300):
    """Scrape one channel with retry logic per message batch."""
    username     = channel["username"]
    display_name = channel["display_name"]
    records = []

    logger.info(f"📡 Scraping @{username}")

    # Retry resolving the entity up to 3 times
    entity = None
    for attempt in range(3):
        try:
            entity = await client.get_entity(username)
            break
        except Exception as exc:
            logger.warning(f"  Attempt {attempt+1} to resolve @{username} failed: {exc}")
            await asyncio.sleep(5)

    if entity is None:
        logger.error(f"  ❌ Could not resolve @{username} after 3 attempts — skipping")
        return records

    count = 0
    async for msg in client.iter_messages(entity, limit=limit):
        if msg.message is None and msg.media is None:
            continue

        date_str = get_date_partition(msg.date) if msg.date else "unknown"
        _, image_dir = ensure_dirs(display_name, date_str)

        # Try image download but don't let it crash the whole scrape
        image_path = None
        if msg.media:
            try:
                image_path = await safe_download_image(client, msg, image_dir)
            except FloodWaitError as fwe:
                logger.warning(f"  Rate limited — sleeping {fwe.seconds}s")
                await asyncio.sleep(fwe.seconds)
            except Exception:
                pass  # Image failed — that's ok, text is saved

        records.append(message_to_dict(msg, display_name, image_path))
        count += 1

        if count % 50 == 0:
            logger.info(f"  …{count} messages fetched from {display_name}")
            # Save progress every 50 messages so we don't lose data on disconnect
            save_to_data_lake(records, display_name)
            records = []  # clear after saving
            await asyncio.sleep(2)  # small pause to be nice to the network

    # Save any remaining records
    save_to_data_lake(records, display_name)
    logger.success(f"✅ {display_name}: {count} messages scraped")
    return []


async def main():
    logger.info("🚀 Starting scraper")
    if not API_ID or not API_HASH:
        logger.error("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env!")
        return

    # Use connection_retries and retry_delay for unstable connections
    async with TelegramClient(
        SESSION,
        API_ID,
        API_HASH,
        connection_retries=10,
        retry_delay=5,
        timeout=30,
    ) as client:
        await client.start(phone=PHONE)
        logger.info("✅ Connected to Telegram")

        for channel in CHANNELS:
            try:
                await scrape_channel(client, channel, limit=300)
            except Exception as exc:
                logger.error(f"❌ Failed on {channel['display_name']}: {exc}")
                logger.info("Waiting 10s before next channel...")
                await asyncio.sleep(10)

    logger.success("🎉 Scraping complete!")


if __name__ == "__main__":
    asyncio.run(main())