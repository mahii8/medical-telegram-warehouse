-- Date dimension: one row per date in the data.

WITH date_spine AS (
    SELECT DISTINCT message_date_only AS full_date
    FROM {{ ref('stg_telegram_messages') }}
    WHERE message_date_only IS NOT NULL
)

SELECT
    TO_CHAR(full_date, 'YYYYMMDD')::INTEGER          AS date_key,
    full_date,
    EXTRACT(DAY     FROM full_date)::INTEGER          AS day_of_month,
    TO_CHAR(full_date, 'Day')                         AS day_name,
    EXTRACT(DOW     FROM full_date)::INTEGER          AS day_of_week,
    EXTRACT(DOY     FROM full_date)::INTEGER          AS day_of_year,
    EXTRACT(WEEK    FROM full_date)::INTEGER          AS week_of_year,
    EXTRACT(MONTH   FROM full_date)::INTEGER          AS month_number,
    TO_CHAR(full_date, 'Month')                       AS month_name,
    EXTRACT(QUARTER FROM full_date)::INTEGER          AS quarter,
    EXTRACT(YEAR    FROM full_date)::INTEGER          AS year,
    CASE WHEN EXTRACT(DOW FROM full_date) IN (0,6)
         THEN TRUE ELSE FALSE END                     AS is_weekend
FROM date_spine
ORDER BY full_date
