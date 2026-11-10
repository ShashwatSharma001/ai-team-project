-- dim_state: one row per state code found in the data.
-- region = US Census Bureau region, so we can compare larger areas.
-- is_td_footprint = states where TD Bank US has branches ("Maine to Florida").
--   Comparing TD with peers only inside these states is fairer.
--   (Check this list against td.com before the showcase.)
CREATE OR REPLACE TABLE dw.dim_state AS
SELECT
  ROW_NUMBER() OVER (ORDER BY state) AS state_key,
  state AS state_code,

  CASE
    WHEN state IN ('CT','ME','MA','NH','RI','VT','NJ','NY','PA') THEN 'Northeast'
    WHEN state IN ('IL','IN','MI','OH','WI','IA','KS','MN','MO','NE','ND','SD') THEN 'Midwest'
    WHEN state IN ('DE','FL','GA','MD','NC','SC','VA','DC','WV',
                   'AL','KY','MS','TN','AR','LA','OK','TX') THEN 'South'
    WHEN state IN ('AZ','CO','ID','MT','NV','NM','UT','WY','AK','CA','HI','OR','WA') THEN 'West'
    WHEN state IN ('AA','AE','AP') THEN 'Military post'
    WHEN state = 'Unknown' THEN 'Unknown'
    ELSE 'US territory'   -- PR, GU, VI, AS, MP, FM, MH, PW, minor outlying islands
  END AS region,

  state IN ('ME','NH','VT','MA','RI','CT','NY','NJ','PA',
            'DE','MD','DC','VA','NC','SC','FL') AS is_td_footprint

FROM (SELECT DISTINCT state FROM staging.complaints);
