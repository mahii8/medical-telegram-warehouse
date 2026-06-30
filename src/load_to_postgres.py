"""
src/load_to_postgres.py
Reads all JSON files from the data lake and loads them into PostgreSQL.
Run AFTER scraper.py.
"""

import os
import json
from pathlib import Path
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("POSTGRES_HOST", "localhost"),
    "port":     int(os.getenv("POSTGRES_PORT", 5432)),
    "dbname":   os.getenv("POSTGRES_DB", "medical_warehouse"),
    "user":     os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "raw" / "telegram_messages"
LOG_DIR  = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger.add(
    str(LOG_DIR / f"loader_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    rotation="10 MB"
)


def collect_all_records():
    records = []
    json_files = sorted(DATA_DIR.rglob("*.json"))
    logger.info(f"Found {len(json_files)} JSON files")

    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
            if isinstance(data, list):
                records.extend(data)
            else:
                records.append(data)
        except Exception as exc:
            logger.warning(f"Skipping {jf}: {exc}")

    logger.info(f"Total records: {len(records)}")
    return records


def load_to_postgres(records):
    if not records:
        logger.warning("No records to load.")
        return 0

    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()

    rows = [
        (
            r.get("message_id"),
            r.get("channel_name"),
            r.get("message_date"),
            r.get("message_text", ""),
            r.get("has_media", False),
            r.get("image_path"),
            r.get("views", 0),
            r.get("forwards", 0),
            json.dumps(r),
        )
        for r in records
    ]

    sql = """
        INSERT INTO raw.telegram_messages
            (message_id, channel_name, message_date, message_text,
             has_media, image_path, views, forwards, raw_data)
        VALUES %s
        ON CONFLICT (message_id, channel_name) DO UPDATE SET
            views     = EXCLUDED.views,
            forwards  = EXCLUDED.forwards,
            loaded_at = NOW();
    """

    execute_values(cur, sql, rows, page_size=500)
    conn.commit()
    count = cur.rowcount
    cur.close()
    conn.close()
    logger.success(f"✅ Loaded {count} records into raw.telegram_messages")
    return count


if __name__ == "__main__":
    logger.info("🚀 Loading data lake → PostgreSQL")
    records = collect_all_records()
    load_to_postgres(records)