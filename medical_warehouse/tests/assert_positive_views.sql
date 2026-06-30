-- Must return 0 rows to pass.
SELECT message_id, channel_key, view_count
FROM {{ ref('fct_messages') }}
WHERE view_count < 0
