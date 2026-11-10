"""
Cleaning functions for the CFPB complaints data.

Each function does ONE job and returns a NEW DataFrame (the input is never
changed). The job in run.py calls them in this order for every chunk:

    rename_columns -> check_columns -> clean_text -> filter_years
    -> split_rejects -> drop_duplicates -> fill_missing
    -> convert_types -> add_features

clean_chunk() at the bottom runs the whole order in one call.

Note: "Consumer disputed?" is listed in the original column list, but our
downloaded file does not have it (the CFPB stopped collecting it in April
2017), so it is not in EXPECTED_COLUMNS.
"""

import re

import pandas as pd

# Dates in the file look like 2024-05-30.
DATE_FORMAT = "%Y-%m-%d"

# The project only covers complaints received in these years.
# Rows outside this range are FILTERED out (dropped quietly), not rejected.
START_DATE = "2016-01-01"
END_DATE = "2018-12-31"

# The 15 columns we expect, after renaming to snake_case.
EXPECTED_COLUMNS = [
    "date_received",
    "product",
    "sub_product",
    "issue",
    "sub_issue",
    "company_public_response",
    "company",
    "state",
    "zip_code",
    "tags",
    "submitted_via",
    "date_sent_to_company",
    "company_response_to_consumer",
    "timely_response",
    "complaint_id",
]

# Values used to fill gaps in these columns (agreed cleaning rules).
FILL_VALUES = {
    "sub_issue": "Not provided",
    "company_public_response": "No public response",
    "tags": "None",
    "state": "Unknown",
}


def to_snake_case(name):
    """Turn a column name into a BigQuery-safe name.

    Example: "Timely response?" -> "timely_response"
    Steps: lowercase, replace anything that is not a letter or digit with "_",
    then remove "_" from the start and end.
    """
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


def rename_columns(df):
    """Rename every column to snake_case (BigQuery does not allow spaces or "?")."""
    return df.rename(columns=to_snake_case)


def check_columns(df):
    """Make sure every expected column is present, and keep only those columns.

    A missing column means the file is not what we expect, so we stop with a
    clear error instead of loading bad data. Extra columns are dropped.
    """
    missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}")
    return df[EXPECTED_COLUMNS].copy()


def clean_text(df):
    """Tidy every text column.

    - remove spaces at the start and end
    - turn any run of spaces inside the text into one space
    - turn empty text ("") into a proper missing value (NA)
    We do NOT change upper/lower case: company and product names are official labels.
    """
    df = df.copy()
    for col in df.columns:
        values = df[col].astype("string")
        values = values.str.strip()
        values = values.str.replace(r"\s+", " ", regex=True)
        values = values.mask(values == "")  # "" -> NA
        df[col] = values
    return df


def filter_years(df, start=START_DATE, end=END_DATE):
    """Keep only complaints received between start and end (both included).

    Rows whose date cannot be read are KEPT here on purpose, so that
    split_rejects() can record them with the reason "invalid date_received".
    Otherwise they would disappear without a trace.
    """
    received = pd.to_datetime(df["date_received"], format=DATE_FORMAT, errors="coerce")
    in_range = received.between(pd.Timestamp(start), pd.Timestamp(end))
    unreadable = received.isna()
    return df[in_range | unreadable].copy()


def split_rejects(df):
    """Split rows into (good rows, rejected rows).

    Each rejected row gets ONE reason in a new "reject_reason" column: the
    first rule it fails, checked in this order. This must run BEFORE
    fill_missing(), otherwise blanks would already be filled in.
    """
    received = pd.to_datetime(df["date_received"], format=DATE_FORMAT, errors="coerce")
    sent = pd.to_datetime(df["date_sent_to_company"], format=DATE_FORMAT, errors="coerce")

    # (reason, True where the row breaks the rule)
    rules = [
        ("missing complaint_id", df["complaint_id"].isna()),
        ("invalid date_received", received.isna()),
        ("sent before received", sent < received),  # False when a date is missing
        ("missing company", df["company"].isna()),
        ("missing product", df["product"].isna()),
    ]

    # Start with no reason for every row, then fill in the first rule each row fails.
    reason = pd.Series(pd.NA, index=df.index, dtype="string")
    for text, failed in rules:
        still_ok = reason.isna()
        reason[still_ok & failed] = text

    is_rejected = reason.notna()
    rejects = df[is_rejected].copy()
    rejects["reject_reason"] = reason[is_rejected]
    good = df[~is_rejected].copy()
    return good, rejects


def drop_duplicates(df):
    """Remove repeated complaints, comparing on complaint_id ONLY.

    The first copy is kept. This removes repeats inside one chunk; repeats
    across chunks are handled by run.py.
    """
    return df.drop_duplicates(subset=["complaint_id"], keep="first")


def fill_missing(df):
    """Fill gaps with the agreed values and write state codes in capitals."""
    df = df.copy()
    df["state"] = df["state"].str.upper()
    return df.fillna(value=FILL_VALUES)


def convert_types(df):
    """Change text columns into their real types.

    - the two date columns become real dates
    - "Yes"/"No" in timely_response becomes True/False in a new column is_timely
      (anything else becomes NA), and timely_response is removed
    zip_code and complaint_id stay as text: some ZIP codes are masked (e.g. "811XX").
    """
    df = df.copy()
    df["date_received"] = pd.to_datetime(df["date_received"], format=DATE_FORMAT, errors="coerce")
    df["date_sent_to_company"] = pd.to_datetime(
        df["date_sent_to_company"], format=DATE_FORMAT, errors="coerce"
    )
    yes_no = {"Yes": True, "No": False}
    df["is_timely"] = df["timely_response"].map(yes_no).astype("boolean")
    return df.drop(columns=["timely_response"])


def add_features(df):
    """Add engineered features.

    days_to_company = how many days the CFPB took to send the complaint to the
    company (date_sent_to_company - date_received). NA if a date is missing.
    """
    df = df.copy()
    gap = df["date_sent_to_company"] - df["date_received"]
    df["days_to_company"] = gap.dt.days.astype("Int64")
    return df


def clean_chunk(raw_df, start=START_DATE, end=END_DATE):
    """Run every cleaning step on one chunk of the raw file.

    Returns (clean rows, rejected rows, counts).
    counts says where every row went, for the load log:
    rows_read = rows_out_of_range + rows_rejected + rows_duplicate + clean rows.
    """
    df = rename_columns(raw_df)
    df = check_columns(df)
    df = clean_text(df)
    in_range = filter_years(df, start, end)
    good, rejects = split_rejects(in_range)
    deduped = drop_duplicates(good)

    counts = {
        "rows_read": len(raw_df),
        "rows_out_of_range": len(df) - len(in_range),
        "rows_rejected": len(rejects),
        "rows_duplicate": len(good) - len(deduped),
    }

    deduped = fill_missing(deduped)
    deduped = convert_types(deduped)
    deduped = add_features(deduped)
    return deduped, rejects, counts
