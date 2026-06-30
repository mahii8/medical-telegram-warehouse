-- Create schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

-- Landing table for all scraped messages
CREATE TABLE IF NOT EXISTS raw.telegram_messages (
    id            SERIAL PRIMARY KEY,
    message_id    BIGINT,
    channel_name  VARCHAR(255),
    message_date  TIMESTAMPTZ,
    message_text  TEXT,
    has_media     BOOLEAN DEFAULT FALSE,
    image_path    TEXT,
    views         INTEGER DEFAULT 0,
    forwards      INTEGER DEFAULT 0,
    raw_data      JSONB,
    loaded_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (message_id, channel_name)
);

CREATE INDEX IF NOT EXISTS idx_raw_channel ON raw.telegram_messages(channel_name);
CREATE INDEX IF NOT EXISTS idx_raw_date    ON raw.telegram_messages(message_date);