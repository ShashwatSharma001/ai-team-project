"""
Make the sample files in samples/ for the hand-in.

Run it from the project folder:
    python scripts/make_samples.py

1. sample_rejects.csv / sample_clean_output.csv
   The real 2016-2018 data had NO rejected rows, so we show the reject rules
   working on a small made-up file (samples/sample_input_complaints.csv) that
   has one broken row for each reject reason, a duplicate and an out-of-range row.
   This step does not use BigQuery.

2. sample_load_log.csv
   A copy of the real load log from BigQuery (staging.load_log). Read-only.
"""

import pandas as pd
import yaml
from google.cloud import bigquery

from ingest import clean

SAMPLE_INPUT = "samples/sample_input_complaints.csv"


def make_sample_rejects(config):
    raw = pd.read_csv(SAMPLE_INPUT, dtype="string")
    start = config["date_range"]["start"]
    end = config["date_range"]["end"]
    good, rejects, counts = clean.clean_chunk(raw, start, end)

    rejects.to_csv("samples/sample_rejects.csv", index=False)
    good.to_csv("samples/sample_clean_output.csv", index=False)
    print(f"sample input: {counts}, clean rows: {len(good)}")
    print("saved samples/sample_rejects.csv and samples/sample_clean_output.csv")


def make_sample_load_log(config):
    bq = config["bigquery"]
    client = bigquery.Client(project=bq["project"], location=bq["location"])
    table = f"{bq['project']}.{bq['dataset']}.{bq['tables']['load_log']}"
    sql = f"SELECT * FROM `{table}` ORDER BY run_started_at"
    log = client.query(sql).to_dataframe(create_bqstorage_client=False)
    log.to_csv("samples/sample_load_log.csv", index=False)
    print(f"saved samples/sample_load_log.csv ({len(log)} runs)")


def main():
    with open("config.yaml") as file:
        config = yaml.safe_load(file)
    make_sample_rejects(config)
    make_sample_load_log(config)


if __name__ == "__main__":
    main()
