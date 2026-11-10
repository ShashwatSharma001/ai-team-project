-- dim_issue: one row per issue + sub-issue pair (what the complaint is about).
-- sub_issue is never empty: the cleaning step filled gaps with "Not provided".
CREATE OR REPLACE TABLE dw.dim_issue AS
SELECT
  ROW_NUMBER() OVER (ORDER BY issue, sub_issue) AS issue_key,
  issue,
  sub_issue
FROM (SELECT DISTINCT issue, sub_issue FROM staging.complaints);
