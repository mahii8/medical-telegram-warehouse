-- Cleans and standardizes raw Telegram messages.
-- Casts types, filters bad rows, adds calculated fields.

WITH raw AS (
    SELECT *
    FROM {{ source('raw', 'telegram_messages') }}
    WHERE
        message_id   IS NOT NULL
        AND channel_name IS NOT NULL
        AND (message_text IS NOT NULL OR has_media = TRUE)
        AND message_date <= NOW()
        AND message_date >= '2020-01-01'
),

cleaned AS (
    SELECT
        message_id::BIGINT                                AS message_id,
        TRIM(channel_name)                                AS channel_name,
        message_date::TIMESTAMPTZ                         AS message_date,
        message_date::DATE                                AS message_date_only,
        TRIM(COALESCE(message_text, ''))                  AS message_text,
        LENGTH(TRIM(COALESCE(message_text, '')))          AS message_length,
        COALESCE(has_media, FALSE)                        AS has_media,
        CASE WHEN image_path IS NOT NULL THEN TRUE
             ELSE FALSE END                               AS has_image,
        image_path,
        COALESCE(views, 0)::INTEGER                       AS view_count,
        COALESCE(forwards, 0)::INTEGER                    AS forward_count,

        CASE
            WHEN LOWER(channel_name) LIKE '%pharma%'  THEN 'Pharmaceutical'
            WHEN LOWER(channel_name) LIKE '%cosmet%'  THEN 'Cosmetics'
            WHEN LOWER(channel_name) LIKE '%lobelia%' THEN 'Cosmetics'
            ELSE 'Medical'
        END                                               AS channel_type,

        loaded_at
    FROM raw
)

SELECT * FROM cleaned
