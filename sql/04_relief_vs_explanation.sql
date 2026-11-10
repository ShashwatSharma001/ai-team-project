-- QUESTION 4: How often does TD give relief (money back or a fix) versus only an
--             explanation, compared with peers, by product?
--
-- WHAT IT MEANS FOR THE CLIENT:
--   Shows whether TD actually fixes problems or mostly explains them away.
--   A higher relief rate means more complaints end with something done for the
--   customer. (The data has no customer ID, so we cannot see whether the same
--   problem came back; this is the closest measure of "fixing things".)
--
-- got_relief is an engineered flag in fact_complaint.
-- Products with fewer than 100 complaints in a group are left out.

SELECT
  p.product_family,
  co.peer_group,
  COUNT(*) AS complaints,
  ROUND(100 * COUNTIF(f.company_response_to_consumer = 'Closed with monetary relief') / COUNT(*), 1)
    AS monetary_relief_pct,
  ROUND(100 * COUNTIF(f.company_response_to_consumer = 'Closed with non-monetary relief') / COUNT(*), 1)
    AS non_monetary_relief_pct,
  ROUND(100 * COUNTIF(f.company_response_to_consumer = 'Closed with explanation') / COUNT(*), 1)
    AS explanation_only_pct,
  ROUND(100 * COUNTIF(f.got_relief) / COUNT(*), 1) AS relief_pct
FROM dw.fact_complaint AS f
JOIN dw.dim_company AS co ON co.company_key = f.company_key
JOIN dw.dim_product AS p  ON p.product_key  = f.product_key
WHERE co.peer_group IN ('Client', 'Peer')
GROUP BY p.product_family, co.peer_group
HAVING COUNT(*) >= 100
ORDER BY p.product_family, co.peer_group;
