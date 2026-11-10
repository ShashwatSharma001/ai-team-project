-- fact_complaint: the centre of the star. Grain: ONE row per complaint.
-- It holds keys that point to each dimension, plus the facts we measure.
--
-- Engineered features:
--   days_to_company = days from received to sent to the company (made in Python)
--   is_late         = the company did NOT respond on time (opposite of is_timely)
--   got_relief      = the company gave money back or fixed something,
--                     not just an explanation
CREATE OR REPLACE TABLE dw.fact_complaint AS
SELECT
  c.complaint_id,

  -- keys to the dimensions
  CAST(FORMAT_DATE('%Y%m%d', c.date_received) AS INT64)        AS date_received_key,
  CAST(FORMAT_DATE('%Y%m%d', c.date_sent_to_company) AS INT64) AS date_sent_key,
  p.product_key,
  co.company_key,
  s.state_key,
  i.issue_key,

  -- other details of the complaint
  c.zip_code,
  c.submitted_via,
  c.company_response_to_consumer,
  c.company_public_response,
  c.tags,

  -- measures and flags
  c.is_timely,
  NOT c.is_timely AS is_late,
  c.company_response_to_consumer IN (
    'Closed with monetary relief',
    'Closed with non-monetary relief'
  ) AS got_relief,
  c.days_to_company

FROM staging.complaints AS c
JOIN dw.dim_product AS p
  ON  p.product = c.product
  AND p.sub_product = COALESCE(c.sub_product, 'No sub-product')
JOIN dw.dim_company AS co ON co.company_name = c.company
JOIN dw.dim_state   AS s  ON s.state_code    = c.state
JOIN dw.dim_issue   AS i  ON i.issue = c.issue AND i.sub_issue = c.sub_issue;
