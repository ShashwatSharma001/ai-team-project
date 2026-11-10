-- dim_company: one row per company.
-- peer_group marks our client, the 8 peer banks we compare against, and everyone else.
-- Company names must match the data EXACTLY (see docs/PROJECT_GUIDE.md).
CREATE OR REPLACE TABLE dw.dim_company AS
SELECT
  ROW_NUMBER() OVER (ORDER BY company) AS company_key,
  company AS company_name,

  CASE
    WHEN company = 'TD BANK US HOLDING COMPANY' THEN 'Client'
    WHEN company IN (
      'WELLS FARGO & COMPANY',
      'BANK OF AMERICA, NATIONAL ASSOCIATION',
      'JPMORGAN CHASE & CO.',
      'CITIBANK, N.A.',
      'CAPITAL ONE FINANCIAL CORPORATION',
      'U.S. BANCORP',
      'PNC Bank N.A.',
      'CITIZENS FINANCIAL GROUP, INC.'
    ) THEN 'Peer'
    ELSE 'Other'
  END AS peer_group,

  -- Short names for chart labels.
  CASE company
    WHEN 'TD BANK US HOLDING COMPANY'            THEN 'TD Bank'
    WHEN 'WELLS FARGO & COMPANY'                 THEN 'Wells Fargo'
    WHEN 'BANK OF AMERICA, NATIONAL ASSOCIATION' THEN 'Bank of America'
    WHEN 'JPMORGAN CHASE & CO.'                  THEN 'JPMorgan Chase'
    WHEN 'CITIBANK, N.A.'                        THEN 'Citibank'
    WHEN 'CAPITAL ONE FINANCIAL CORPORATION'     THEN 'Capital One'
    WHEN 'U.S. BANCORP'                          THEN 'U.S. Bank'
    WHEN 'PNC Bank N.A.'                         THEN 'PNC'
    WHEN 'CITIZENS FINANCIAL GROUP, INC.'        THEN 'Citizens'
    ELSE company
  END AS short_name

FROM (SELECT DISTINCT company FROM staging.complaints);
