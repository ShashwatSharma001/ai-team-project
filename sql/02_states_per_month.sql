-- QUESTION 2: Which states complain most per month?
--
-- WHAT IT MEANS FOR THE CLIENT:
--   Shows where complaint-handling staff are most needed. Big states always have
--   more complaints, so we compare TD's SHARE per state with the peers' share.
--   share_ratio above 1 means the state is a bigger part of TD's complaints than
--   of the peers' complaints (often because TD has many branches there).

WITH by_state AS (
  SELECT
    s.state_code,
    s.region,
    s.is_td_footprint,
    COUNTIF(co.peer_group = 'Client') AS td_complaints,
    COUNTIF(co.peer_group = 'Peer')   AS peer_complaints
  FROM dw.fact_complaint AS f
  JOIN dw.dim_company AS co ON co.company_key = f.company_key
  JOIN dw.dim_state   AS s  ON s.state_key    = f.state_key
  WHERE co.peer_group IN ('Client', 'Peer')
  GROUP BY s.state_code, s.region, s.is_td_footprint
),
months AS (
  -- number of months in the period (36 for 2016-2018)
  SELECT COUNT(DISTINCT d.year_month) AS n_months
  FROM dw.fact_complaint AS f
  JOIN dw.dim_date AS d ON d.date_key = f.date_received_key
)
SELECT
  b.state_code,
  b.region,
  b.is_td_footprint,
  b.td_complaints,
  ROUND(b.td_complaints / m.n_months, 1) AS td_complaints_per_month,
  ROUND(100 * b.td_complaints   / SUM(b.td_complaints)   OVER (), 2) AS td_share_pct,
  ROUND(100 * b.peer_complaints / SUM(b.peer_complaints) OVER (), 2) AS peer_share_pct,
  ROUND(
    SAFE_DIVIDE(b.td_complaints / SUM(b.td_complaints) OVER (),
                b.peer_complaints / SUM(b.peer_complaints) OVER ()), 2
  ) AS share_ratio
FROM by_state AS b
CROSS JOIN months AS m
ORDER BY b.td_complaints DESC;
