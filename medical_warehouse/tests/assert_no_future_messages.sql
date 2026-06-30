-- Must return 0 rows to pass.
SELECT message_id, channel_name, message_date
FROM {{ ref('stg_telegram_messages') }}
WHERE message_date > NOW()
