-- QUESTION 5 (uses SCD Type 2 history): How did complaint patterns shift when the
--             CFPB reorganised product categories on 2017-04-24?
--
-- WHAT IT MEANS FOR THE CLIENT:
--   Some changes in the numbers come from the NEW CATEGORIES, not from customers.
--   dim_product keeps every old and new label with effective_from / effective_to /
--   is_current, and links them with product_family. That lets us follow one
--   product across the change as ONE line.
--   Result: credit-reporting complaints started rising in early 2017 under the
--   OLD label and kept rising under the NEW label, for TD and peers alike. So the
--   rise is real (not caused by the rename) and not a TD-only problem.
--
-- label_version says whether the complaint used an old (retired) label or a
-- current one.

SELECT
  d.year_month,
  co.peer_group,
  p.product_family,
  CASE WHEN p.is_current THEN 'Current label' ELSE 'Old label (retired 2017-04-23)' END
    AS label_version,
  COUNT(*) AS complaints,
  -- share of the group's complaints in that month
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY d.year_month, co.peer_group), 2)
    AS pct_of_group_month
FROM dw.fact_complaint AS f
JOIN dw.dim_company AS co ON co.company_key = f.company_key
JOIN dw.dim_product AS p  ON p.product_key  = f.product_key
JOIN dw.dim_date    AS d  ON d.date_key     = f.date_received_key
WHERE co.peer_group IN ('Client', 'Peer')
GROUP BY d.year_month, co.peer_group, p.product_family, label_version
ORDER BY d.year_month, co.peer_group, p.product_family, label_version;
