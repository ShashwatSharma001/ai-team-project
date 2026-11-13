# Bank Complaint Data Warehouse (Project 0)

**Client:** TD Bank US. Its customer complaints to the US regulator (CFPB) are public and rising.
TD wants to know **where its complaints come from, how it compares with other banks, and what to fix first.**

We loaded CFPB complaints for **2016–2018** into **Google BigQuery** and compared TD with **8 peer banks**,
using **percentages, not raw counts**, so bank size doesn't distort the picture.

## Questions and answers

| # | Question | Answer |
|---|----------|--------|
| 1 | Which products create the most complaints? Is it getting worse? | TD complaints **+60%** (peers −4%). Bank accounts = **40%** of TD's complaints (peers 28%). |
| 2 | Which states complain most per month? | **NY, FL, NJ** = **42%** of TD's complaints. |
| 3 | How often are responses late, by product? | TD late **1 time in 4,977**. Peers **2.2%**. |
| 4 | How often does TD give relief vs only an explanation? | TD relief **36%** vs peers **23%**. |
| 5 | What changed when the CFPB renamed products (24 Apr 2017)? | Credit-reporting complaints rose for TD **and** peers, starting before the rename. |
| + | Do busier months get less relief? | Yes, **r = −0.64**. Not proof of cause (the product mix changed too). |

Charts: [`charts/`](charts/)

## How it works

```
complaints.csv (18.9M rows)
  → ingest/run.py         Python: read in 250K-row chunks, clean, reject, dedupe, keep 2016–2018
  → BigQuery staging      complaints (691,167) · rejects · load_log
  → scripts/build_dw.py   SQL builds the star schema
  → BigQuery dw           fact_complaint + 5 dimensions (dim_product is SCD Type 2)
  → scripts/make_charts.py runs sql/01–06 → charts/*.png
```

![Star schema](docs/star_schema.png)

## How to run

**1. Setup (once)**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
gcloud auth application-default login      # log in to Google Cloud
cp config.example.yaml config.yaml         # then set your BigQuery project ID
```
Download the CFPB CSV from <https://www.consumerfinance.gov/data-research/consumer-complaints/>
and save it as `data/raw/complaints.csv`.

**2. Run the pipeline (about 5 minutes)**
```bash
source .venv/bin/activate
python -m ingest.run            # clean + load to BigQuery staging (~4 min)
python scripts/build_dw.py      # build the star schema in dw (~30 s)
python scripts/make_charts.py   # run the 6 queries, save charts (~20 s)
```
- Add `--dry-run` to the first command to clean the data without sending anything to BigQuery.
- Safe to re-run: same result every time, no duplicates. Each run adds one row to `load_log`.

**3. Run a query yourself:** open a file in [`sql/`](sql/), paste it into the BigQuery console and click **Run**.

**4. Tests:** `pytest` (no test connects to BigQuery).

## Folders

```
ingest/    clean.py (cleaning rules), run.py (load job)
sql/dw/    build the star schema
sql/       01–06: one question each
scripts/   build_dw.py, make_charts.py, make_samples.py, draw_star_schema.py
charts/    chart images
samples/   small example input, rejects, clean output, load log
tests/     unit tests
docs/      star schema image, project guide
```

## Limitations

- Correlation is **not** cause and effect.
- No customer ID, cost or churn data.
- BigQuery sandbox tables expire after 60 days. Re-run the pipeline if they're gone.
