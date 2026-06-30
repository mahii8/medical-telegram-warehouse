-- fct_image_detections
-- One row per detected object per image, joined to messages and channels.

WITH detections AS (
    SELECT
        message_id::BIGINT AS message_id,
        channel_name,
        image_path,
        detected_class,
        confidence_score,
        image_category
    FROM {{ source('raw', 'yolo_detections') }}
),

messages AS (
    SELECT message_id, channel_key, date_key
    FROM {{ ref('fct_messages') }}
)

SELECT
    d.message_id,
    m.channel_key,
    m.date_key,
    d.image_path,
    d.detected_class,
    d.confidence_score,
    d.image_category
FROM detections d
LEFT JOIN messages m ON d.message_id = m.message_id
