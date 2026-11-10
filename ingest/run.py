"""
Ingest job: read the raw complaint files in chunks, clean them, load to BigQuery.

Run it from the project folder:
    python -m ingest.run             # clean the data and load it to BigQuery
    python -m ingest.run --dry-run   # clean only: nothing is sent to BigQuery

What it does:
1. Reads the settings in config.yaml.
2. Reads each source file in chunks (250,000 rows at a time).
3. Cleans each chunk with ingest/clean.py.
4. Loads clean rows to staging.complaints and rejected rows to staging.rejects.
5. At the end, adds one row to staging.load_log describing the run.

Running it twice does not duplicate data: the FIRST chunk of every run
REPLACES the complaints and rejects tables (WRITE_TRUNCATE); the chunks after
it are ADDED on (WRITE_APPEND). The load log is the exception: it is a
history of runs, so every run adds one new row to it.
"""

import argparse
import uuid
from datetime import datetime, timezone

import pandas as pd
import yaml
from google.cloud import bigquery

from ingest import clean

# ---------- table layouts (schemas) in BigQuery ----------

# Clean complaints: same order as the columns that clean.clean_chunk() returns.
COMPLAINTS_SCHEMA = [
    bigquery.SchemaField("date_received", "DATE"),
    bigquery.SchemaField("product", "STRING"),
    bigquery.SchemaField("sub_product", "STRING"),
    bigquery.SchemaField("issue", "STRING"),
    bigquery.SchemaField("sub_issue", "STRING"),
    bigquery.SchemaField("company_public_response", "STRING"),
    bigquery.SchemaField("company", "STRING"),
    bigquery.SchemaField("state", "STRING"),
    bigquery.SchemaField("zip_code", "STRING"),
    bigquery.SchemaField("tags", "STRING"),
    bigquery.SchemaField("submitted_via", "STRING"),
    bigquery.SchemaField("date_sent_to_company", "DATE"),
    bigquery.SchemaField("company_response_to_consumer", "STRING"),
    bigquery.SchemaField("complaint_id", "STRING"),
    bigquery.SchemaField("is_timely", "BOOL"),
    bigquery.SchemaField("days_to_company", "INT64"),
]

# Rejects keep every column as text (exactly as read), plus the reason.
REJECTS_SCHEMA = [
    bigquery.SchemaField(column, "STRING") for column in clean.EXPECTED_COLUMNS
] + [bigquery.SchemaField("reject_reason", "STRING")]

# One row per run.
LOAD_LOG_SCHEMA = [
    bigquery.SchemaField("run_id", "STRING"),
    bigquery.SchemaField("run_started_at", "TIMESTAMP"),
    bigquery.SchemaField("run_finished_at", "TIMESTAMP"),
    bigquery.SchemaField("source_files", "STRING"),
    bigquery.SchemaField("rows_read", "INT64"),
    bigquery.SchemaField("rows_out_of_range", "INT64"),
    bigquery.SchemaField("rows_rejected", "INT64"),
    bigquery.SchemaField("rows_duplicate", "INT64"),
    bigquery.SchemaField("rows_loaded", "INT64"),
    bigquery.SchemaField("status", "STRING"),
]


# ---------- small helper functions ----------

def load_config(path):
    """Read config.yaml into a Python dictionary."""
    with open(path) as file:
        return yaml.safe_load(file)


def read_chunks(path, file_format, chunk_size):
    """Give back the file one chunk at a time, with every column as text.

    file_format is "csv" or "json" (JSON must have one record per line).
    """
    if file_format == "csv":
        reader = pd.read_csv(path, dtype="string", chunksize=chunk_size)
    elif file_format == "json":
        reader = pd.read_json(path, lines=True, dtype=False, chunksize=chunk_size)
    else:
        raise ValueError(f"Unknown format '{file_format}' for {path}: use csv or json")

    for chunk in reader:
        yield chunk.astype("string")


def drop_seen_ids(df, seen_ids):
    """Remove rows whose complaint_id was already kept from an earlier chunk.

    clean.drop_duplicates() only sees one chunk. This function remembers every
    complaint_id kept so far (in the set seen_ids) so repeats in LATER chunks
    are removed too. It adds the new ids to seen_ids.
    """
    is_new = ~df["complaint_id"].isin(seen_ids)
    df = df[is_new]
    seen_ids.update(df["complaint_id"])
    return df


def write_table(client, df, table_id, schema, write_mode):
    """Load a DataFrame into a BigQuery table and wait until it is finished.

    write_mode is bigquery.WriteDisposition.WRITE_TRUNCATE (replace the table)
    or bigquery.WriteDisposition.WRITE_APPEND (add rows to the table).
    """
    columns = [field.name for field in schema]
    job_config = bigquery.LoadJobConfig(schema=schema, write_disposition=write_mode)
    job = client.load_table_from_dataframe(df[columns], table_id, job_config=job_config)
    job.result()  # waits; raises an error if the load failed


# ---------- the job ----------

def run(config, dry_run=False):
    """Run the whole ingest job. Returns the load log row (a dictionary)."""
    bq = config["bigquery"]
    dataset_id = f"{bq['project']}.{bq['dataset']}"
    complaints_table = f"{dataset_id}.{bq['tables']['complaints']}"
    rejects_table = f"{dataset_id}.{bq['tables']['rejects']}"
    load_log_table = f"{dataset_id}.{bq['tables']['load_log']}"
    start = config["date_range"]["start"]
    end = config["date_range"]["end"]

    # Connect to BigQuery and make sure the staging dataset exists.
    client = None
    if not dry_run:
        client = bigquery.Client(project=bq["project"], location=bq["location"])
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = bq["location"]
        client.create_dataset(dataset, exists_ok=True)

    log = {
        "run_id": str(uuid.uuid4()),
        "run_started_at": datetime.now(timezone.utc),
        "run_finished_at": None,
        "source_files": ", ".join(source["path"] for source in config["sources"]),
        "rows_read": 0,
        "rows_out_of_range": 0,
        "rows_rejected": 0,
        "rows_duplicate": 0,
        "rows_loaded": 0,
        "status": "failed",  # changed to "success" only if everything works
    }
    seen_ids = set()
    is_first_chunk = True
    chunk_number = 0

    try:
        for source in config["sources"]:
            for raw_chunk in read_chunks(source["path"], source["format"], config["chunk_size"]):
                chunk_number += 1
                good, rejects, counts = clean.clean_chunk(raw_chunk, start, end)

                # Remove repeats of complaints already kept from earlier chunks.
                rows_before = len(good)
                good = drop_seen_ids(good, seen_ids)
                counts["rows_duplicate"] += rows_before - len(good)

                # Add this chunk's numbers to the run totals.
                for name, value in counts.items():
                    log[name] += value
                log["rows_loaded"] += len(good)

                if not dry_run:
                    # The first chunk replaces both tables, even if it is empty,
                    # so old data from an earlier run is always cleared.
                    if is_first_chunk:
                        mode = bigquery.WriteDisposition.WRITE_TRUNCATE
                    else:
                        mode = bigquery.WriteDisposition.WRITE_APPEND
                    if is_first_chunk or len(good) > 0:
                        write_table(client, good, complaints_table, COMPLAINTS_SCHEMA, mode)
                    if is_first_chunk or len(rejects) > 0:
                        write_table(client, rejects, rejects_table, REJECTS_SCHEMA, mode)
                is_first_chunk = False

                print(
                    f"chunk {chunk_number}: read {counts['rows_read']:,}, "
                    f"loaded {len(good):,}, rejected {len(rejects):,}"
                )

        log["status"] = "success"

    finally:
        # This part runs even if the job crashed, so failed runs are logged too.
        log["run_finished_at"] = datetime.now(timezone.utc)
        print_summary(log)
        if client is not None:
            write_table(
                client,
                pd.DataFrame([log]),
                load_log_table,
                LOAD_LOG_SCHEMA,
                bigquery.WriteDisposition.WRITE_APPEND,
            )

    return log


def print_summary(log):
    """Print the run totals and check that every row is accounted for."""
    accounted = (
        log["rows_out_of_range"]
        + log["rows_rejected"]
        + log["rows_duplicate"]
        + log["rows_loaded"]
    )
    print()
    print(f"status:            {log['status']}")
    print(f"rows read:         {log['rows_read']:,}")
    print(f"  out of range:    {log['rows_out_of_range']:,}")
    print(f"  rejected:        {log['rows_rejected']:,}")
    print(f"  duplicates:      {log['rows_duplicate']:,}")
    print(f"  loaded:          {log['rows_loaded']:,}")
    print(f"every row accounted for: {accounted == log['rows_read']}")


def main():
    parser = argparse.ArgumentParser(description="Load CFPB complaints into BigQuery staging.")
    parser.add_argument("--config", default="config.yaml", help="path to the config file")
    parser.add_argument(
        "--dry-run", action="store_true", help="clean the data but send nothing to BigQuery"
    )
    args = parser.parse_args()
    run(load_config(args.config), dry_run=args.dry_run)


if __name__ == "__main__":
    main()
