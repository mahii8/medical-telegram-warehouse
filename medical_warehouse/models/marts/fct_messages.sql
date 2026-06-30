-- Fact table: one row per message, FK'd to dimensions.

WITH messages AS (
    SELECT * FROM {{ ref('stg_telegram_messages') }}
),
channels AS (
    SELECT channel_key, channel_name FROM {{ ref('dim_channels') }}
),
dates AS (
    SELECT date_key, full_date FROM {{ ref('dim_dates') }}
)

SELECT
    m.message_id,
    c.channel_key,
    d.date_key,
    m.message_text,
    m.message_length,
    m.has_image,
    m.image_path,
    m.view_count,
    m.forward_count,
    m.message_date,
    m.loaded_at
FROM messages m
LEFT JOIN channels c ON m.channel_name      = c.channel_name
LEFT JOIN dates    d ON m.message_date_only = d.full_date
