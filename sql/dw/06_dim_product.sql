-- dim_product: SCD Type 2 (keeps history of changes).
--
-- On 2017-04-24 the CFPB reorganised its product categories. For example,
-- "Credit reporting" became "Credit reporting, credit repair services, or other
-- personal consumer reports", and "Credit card" + "Prepaid card" were merged into
-- "Credit card or prepaid card". Old complaints keep their OLD names.
--
-- Each row is one product + sub-product label, as it was used at the time.
--   product_family  = stable name that links old and new labels together
--   effective_from  = first day the label appears in our data
--   effective_to    = 2017-04-23 if the label was retired at the reorganisation,
--                     otherwise 9999-12-31 (still in use)
--   is_current      = TRUE if the label is still in use after the reorganisation
CREATE OR REPLACE TABLE dw.dim_product AS
WITH labels AS (
  SELECT
    product,
    COALESCE(sub_product, 'No sub-product') AS sub_product,
    MIN(date_received) AS first_seen,
    MAX(date_received) AS last_seen
  FROM staging.complaints
  GROUP BY 1, 2
)
SELECT
  ROW_NUMBER() OVER (ORDER BY product, sub_product) AS product_key,

  CASE product
    WHEN 'Credit reporting' THEN 'Credit reporting'
    WHEN 'Credit reporting, credit repair services, or other personal consumer reports' THEN 'Credit reporting'
    WHEN 'Bank account or service'     THEN 'Bank accounts'
    WHEN 'Checking or savings account' THEN 'Bank accounts'
    WHEN 'Credit card'                 THEN 'Credit and prepaid cards'
    WHEN 'Prepaid card'                THEN 'Credit and prepaid cards'
    WHEN 'Credit card or prepaid card' THEN 'Credit and prepaid cards'
    WHEN 'Consumer Loan'               THEN 'Consumer loans'
    WHEN 'Payday loan'                 THEN 'Consumer loans'
    WHEN 'Vehicle loan or lease'       THEN 'Consumer loans'
    WHEN 'Payday loan, title loan, or personal loan' THEN 'Consumer loans'
    WHEN 'Money transfers'             THEN 'Money services'
    WHEN 'Virtual currency'            THEN 'Money services'
    WHEN 'Other financial service'     THEN 'Money services'
    WHEN 'Money transfer, virtual currency, or money service' THEN 'Money services'
    ELSE product   -- Debt collection, Mortgage, Student loan kept their names
  END AS product_family,

  product,
  sub_product,
  first_seen AS effective_from,
  CASE
    WHEN last_seen < DATE '2017-04-24' THEN DATE '2017-04-23'
    ELSE DATE '9999-12-31'
  END AS effective_to,
  last_seen >= DATE '2017-04-24' AS is_current

FROM labels;
