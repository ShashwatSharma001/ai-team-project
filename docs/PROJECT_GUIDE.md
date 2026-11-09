# Project 0 (P0): Bank Complaint Data Warehouse

## Who I am / how to help me
- I'm a trainee AI engineer (Revature → Cognizant). I must EXPLAIN every file at a live showcase to Cognizant engineers and managers.
- Keep code simple, readable and well-commented. No clever tricks.
- Work in small steps. After each step, explain what you did and why in plain words.
- Ask me before: running anything that writes to BigQuery, deleting files, or installing new packages.
- Work only on the `draft-1` git branch. Never commit to or push `main`.

## Deadline
- Showcase: Friday 13 November 2026, 15 minutes per pair, queries run LIVE in BigQuery.

## The client and the business case
- Client: the US retail arm of a Canadian bank (likely TD Bank US), compared against peer banks.
- Problem: complaints against the bank are rising and are published by a US regulator (CFPB).
  The bank wants to know which products, issues and regions drive complaints,
  whether it responds on time as often as peers, and what to fix first.
- Only claim what the data can prove (no churn data, no cost data).

## Data
- Source: CFPB Consumer Complaint Database (consumerfinance.gov/data-research/consumer-complaints).
- Local file: `data/raw/complaints.csv`, about 5.4 GB and ~18 million rows. NEVER load it all at once.
  Use `pd.read_csv(..., dtype="string", chunksize=250_000)`.
- Keep only Date received between 2016-01-01 and 2018-12-31 (filtered, not rejected).
- Columns (verify with nrows=5): Date received, Product, Sub-product, Issue, Sub-issue,
  Company public response, Company, State, ZIP code, Tags, Submitted via,
  Date sent to company, Company response to consumer, Timely response?, Consumer disputed?, Complaint ID.
- ZIP codes can be masked ("811XX"): keep as text.

## BigQuery
- Project: `project-0-514205` (free sandbox, tables expire after 60 days).
- `project0.complaints` = console upload, for EXPLORATION ONLY. Not part of the pipeline.
- Pipeline datasets: `staging` (complaints, rejects, load_log) and `dw` (star schema).
- Auth: `gcloud auth application-default login`. No key files in the repo.
- BigQuery column names cannot contain spaces or "?": convert to snake_case
  (e.g. "Timely response?" → timely_response).

## Requirements from the brief (must all be met)
### Ingest (Python)
- A Python job driven by `config.yaml` (raw file paths, format CSV/JSON, BigQuery project + dataset).
  Adding a source file = config change, not code change.
- Validate and clean every record with pandas: expected columns and types,
  cleansing rules listed in README, duplicates removed (dedupe on Complaint ID ONLY).
- Rows that fail go to a rejects table WITH a reason; the job carries on.
- Every run writes a load log: run time, rows read, rows loaded, rows rejected.
- Running the job twice adds nothing (idempotent: WRITE_TRUNCATE on first chunk).
### Warehouse
- Raw data goes straight into BigQuery staging tables. No MySQL/PostgreSQL step.
- Star schema from staging: one fact table (grain: one row per complaint), 3+ dimensions,
  diagram saved as an image in `docs/`.
- One SCD Type 2 dimension: `dim_product` with effective_from, effective_to, is_current.
  Real change: CFPB reorganised product/sub-product categories on 2017-04-24.
### Analyse and tell
- 5+ BigQuery `.sql` files in `sql/`, each joining the fact to its dimensions, answering one client question.
  Each file opens with a comment: the question, and what the answer means for the client.
  One query must use the SCD2 history.
- Compare client vs peers using rates/percentages, not raw counts.
- 2 engineered features (e.g. days_to_company, late_response flag / rolling monthly volume).
- 1 correlation, stated in client terms, with a line on why it may not be causation.
- 3+ Matplotlib charts drawn from BigQuery results, saved to `charts/`.
  Titles state the insight, not column names. Client in colour, peers in grey.
### Rules
- README opens with the business case (1–2 paragraphs for a non-technical manager) and 3–5 questions.
- Credentials never in the repo. README explains how to supply them.
- pytest tests for transform and cleansing functions. NO test connects to BigQuery.
- README lets someone run everything from a fresh clone: install, credentials, job, tests, queries.
- Hand-in also needs: config file with placeholders, sample load log, sample rejects, dataset link.

## Cleaning rules (agreed)
- Trim whitespace and collapse double spaces in all text columns; blanks → NA.
- Fill: Sub-issue → "Not provided", Company public response → "No public response",
  Tags → "None", State → "Unknown" (uppercase states).
- Do NOT change the case of Company or Product names (official labels).
- Timely response? → boolean `is_timely`.
- Engineered feature: days_to_company = Date sent to company − Date received.
- Reject reasons: "missing complaint_id", "invalid date_received",
  "sent before received", "missing company", "missing product".
  Apply reject rules BEFORE filling missing values.

## Target folder layout
```
config.yaml
requirements.txt
ingest/        # clean.py, run.py
tests/         # test_clean.py
sql/           # 01_... .sql to 05_... .sql + dw build scripts
scripts/       # make_charts.py
charts/        # PNGs
docs/          # star_schema.png
samples/       # sample load log + sample rejects (small CSVs)
notebooks/     # exploration only
data/raw/      # ignored by git
```

## Out of scope (do NOT add)
- dbt, Airflow, Docker, Looker dashboards, ML models, LLM features.
  (An "AI on top" idea appears only as one future-step slide.)
