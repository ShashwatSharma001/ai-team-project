"""
Build the star schema (dataset "dw") in BigQuery from the staging tables.

Run it from the project folder, AFTER the ingest job:
    python scripts/build_dw.py

It runs every .sql file in sql/dw/ in name order (01_, 02_, ...), then prints
how many rows each table has. Every file uses CREATE OR REPLACE, so running
it twice gives the same result.
"""

import glob

import yaml
from google.cloud import bigquery

TABLES = ["dim_date", "dim_company", "dim_state", "dim_issue", "dim_product", "fact_complaint"]


def main():
    with open("config.yaml") as file:
        config = yaml.safe_load(file)
    bq = config["bigquery"]
    client = bigquery.Client(project=bq["project"], location=bq["location"])

    for path in sorted(glob.glob("sql/dw/*.sql")):
        print(f"running {path}")
        with open(path) as file:
            client.query(file.read()).result()  # waits; raises an error if the SQL fails

    print()
    for table in TABLES:
        rows = list(client.query(f"SELECT COUNT(*) AS n FROM dw.{table}").result())
        print(f"dw.{table:<15} {rows[0].n:>9,} rows")


if __name__ == "__main__":
    main()
