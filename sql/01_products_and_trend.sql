-- QUESTION 1: Which products create the most complaints, and is it getting worse?
--
-- WHAT IT MEANS FOR THE CLIENT:
--   Shows where TD's complaints come from compared with peers (as a % of each
--   group's complaints, so bank size does not matter), and how the yearly volume
--   changes. If TD's volume grows while peers' stays flat, the problem is TD's own,
--   not the whole market's.
--
-- product_family comes from dim_product, so old and new product names
-- (before/after the 2017-04-24 reorganisation) count as one product.

SELECT
  co.peer_group,
  p.product_family,
  d.year,
  COUNT(*) AS complaints,
  -- this product's share of the group's complaints in that year
  -- (SUM(COUNT(*)) OVER ... = the group's total for that year)
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY co.peer_group, d.year), 1)
    AS pct_of_group_complaints
FROM dw.fact_complaint AS f
JOIN dw.dim_company AS co ON co.company_key = f.company_key
JOIN dw.dim_product AS p  ON p.product_key  = f.product_key
JOIN dw.dim_date    AS d  ON d.date_key     = f.date_received_key
WHERE co.peer_group IN ('Client', 'Peer')
GROUP BY co.peer_group, p.product_family, d.year
ORDER BY co.peer_group, d.year, complaints DESC;
