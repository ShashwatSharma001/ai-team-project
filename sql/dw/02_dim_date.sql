-- dim_date: one row per calendar day.
-- Lets queries group by year, quarter, month or weekday without doing date maths.
-- It covers the first date received up to the last date sent to a company
-- (some complaints were sent to the company years after they were received).
CREATE OR REPLACE TABLE dw.dim_date AS
SELECT
  CAST(FORMAT_DATE('%Y%m%d', d) AS INT64) AS date_key,   -- e.g. 20170301
  d                                        AS full_date,
  EXTRACT(YEAR FROM d)                     AS year,
  EXTRACT(QUARTER FROM d)                  AS quarter,
  EXTRACT(MONTH FROM d)                    AS month,
  FORMAT_DATE('%B', d)                     AS month_name,  -- e.g. March
  FORMAT_DATE('%Y-%m', d)                  AS year_month,  -- e.g. 2017-03
  FORMAT_DATE('%A', d)                     AS day_name,    -- e.g. Wednesday
  EXTRACT(DAYOFWEEK FROM d) IN (1, 7)      AS is_weekend   -- 1 = Sunday, 7 = Saturday
FROM UNNEST(
  GENERATE_DATE_ARRAY(
    (SELECT MIN(date_received) FROM staging.complaints),
    (SELECT GREATEST(MAX(date_received), MAX(date_sent_to_company)) FROM staging.complaints)
  )
) AS d;
