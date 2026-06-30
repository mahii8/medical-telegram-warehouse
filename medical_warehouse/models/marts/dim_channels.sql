-- Channel dimension: one row per channel with summary stats.

WITH channel_stats AS (
    SELECT
        channel_name,
        channel_type,
        MIN(message_date)                                        AS first_post_date,
        MAX(message_date)                                        AS last_post_date,
        COUNT(*)                                                 AS total_posts,
        ROUND(AVG(view_count), 0)                                AS avg_views,
        SUM(CASE WHEN has_image THEN 1 ELSE 0 END)               AS total_images,
        ROUND(
            100.0 * SUM(CASE WHEN has_image THEN 1 ELSE 0 END)
            / NULLIF(COUNT(*), 0), 2
        )                                                        AS pct_posts_with_image
    FROM {{ ref('stg_telegram_messages') }}
    GROUP BY channel_name, channel_type
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['channel_name']) }}     AS channel_key,
    channel_name,
    channel_type,
    first_post_date,
    last_post_date,
    total_posts,
    avg_views,
    total_images,
    pct_posts_with_image,
    NOW()                                                        AS dbt_updated_at
FROM channel_stats
