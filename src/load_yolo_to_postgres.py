"""
src/load_yolo_to_postgres.py
Loads the YOLO detection CSV into PostgreSQL as a raw table,
so dbt can build a mart model on top of it.
"""

import os
import csv
from pathlib import Path

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
CSV_PATH = BASE_DIR / "data" / "yolo_detections.csv"


def main():
    logger.info("🚀 Loading YOLO detections → PostgreSQL")

    rows = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append((
                row["message_id"],
                row["channel_name"],
                row["image_path"],
                row["detected_class"],
                float(row["confidence_score"]),
                row["image_category"],
            ))

    logger.info(f"Loaded {len(rows)} rows from CSV")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        CREATE SCHEMA IF NOT EXISTS raw;
        DROP TABLE IF EXISTS raw.yolo_detections;
        CREATE TABLE raw.yolo_detections (
            id                SERIAL PRIMARY KEY,
            message_id        VARCHAR(50),
            channel_name      VARCHAR(255),
            image_path        TEXT,
            detected_class    VARCHAR(100),
            confidence_score  FLOAT,
            image_category    VARCHAR(50),
            loaded_at         TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    conn.commit()

    execute_values(
        cur,
        """
        INSERT INTO raw.yolo_detections
            (message_id, channel_name, image_path, detected_class,
             confidence_score, image_category)
        VALUES %s
        """,
        rows,
        page_size=500,
    )
    conn.commit()

    logger.success(f"✅ Loaded {len(rows)} rows into raw.yolo_detections")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
