-- QUESTION 6 (correlation): When TD gets more complaints in a month, does it give
--             relief less often?
--
-- WHAT IT MEANS FOR THE CLIENT:
--   A negative correlation means: in busier months, a smaller share of TD's
--   complaints end with relief. That could mean the team is stretched when volume
--   is high.
--   WHY IT MAY NOT BE CAUSATION: the product mix also changes over time. For
--   example, credit-reporting complaints (which get relief less often) grew after
--   2017, at the same time as total volume. The mix, not the volume, could be
--   driving the lower relief rate.
--   Result: r = -0.64 over 36 months; still -0.53 without the January 2018 spike,
--   so one unusual month does not explain it.
--
-- Engineered feature: rolling_3m_complaints = average monthly volume over the
-- current month and the 2 months before it (smooths out one-off spikes).

WITH monthly AS (
  SELECT
    d.year_month,
    COUNT(*) AS complaints,
    100 * COUNTIF(f.got_relief) / COUNT(*) AS relief_pct
  FROM dw.fact_complaint AS f
  JOIN dw.dim_company AS co ON co.company_key = f.company_key
  JOIN dw.dim_date    AS d  ON d.date_key     = f.date_received_key
  WHERE co.peer_group = 'Client'
  GROUP BY d.year_month
)
SELECT
  year_month,
  complaints,
  ROUND(AVG(complaints) OVER (ORDER BY year_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 1)
    AS rolling_3m_complaints,
  ROUND(relief_pct, 1) AS relief_pct,
  ROUND(CORR(complaints, relief_pct) OVER (), 2) AS corr_volume_vs_relief
FROM monthly
ORDER BY year_month;
