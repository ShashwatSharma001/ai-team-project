-- QUESTION 3: How often do companies respond late, by product?
--
-- WHAT IT MEANS FOR THE CLIENT:
--   A late response is a regulatory risk. This compares TD's late-response rate
--   with the peers' rate for each product. A low rate means TD's response process
--   is working; a product with a high rate is where to look first.
--
-- is_late is an engineered flag in fact_complaint (= NOT is_timely).
-- Products with fewer than 100 complaints in a group are left out: the rate
-- would be too noisy to trust.

SELECT
  p.product_family,
  co.peer_group,
  COUNT(*) AS complaints,
  COUNTIF(f.is_late) AS late_responses,
  ROUND(100 * COUNTIF(f.is_late) / COUNT(*), 2) AS late_pct
FROM dw.fact_complaint AS f
JOIN dw.dim_company AS co ON co.company_key = f.company_key
JOIN dw.dim_product AS p  ON p.product_key  = f.product_key
WHERE co.peer_group IN ('Client', 'Peer')
GROUP BY p.product_family, co.peer_group
HAVING COUNT(*) >= 100
ORDER BY p.product_family, co.peer_group;
