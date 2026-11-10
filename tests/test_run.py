"""
Tests for the helper functions in ingest/run.py.

No test here connects to BigQuery.
"""

import pandas as pd
import pytest

from ingest import clean, run


def test_drop_seen_ids_removes_ids_from_earlier_chunks():
    seen_ids = set()
    first = pd.DataFrame({"complaint_id": ["1", "2"]}, dtype="string")
    second = pd.DataFrame({"complaint_id": ["2", "3"]}, dtype="string")

    kept_first = run.drop_seen_ids(first, seen_ids)
    kept_second = run.drop_seen_ids(second, seen_ids)

    assert list(kept_first["complaint_id"]) == ["1", "2"]
    assert list(kept_second["complaint_id"]) == ["3"]  # "2" was already loaded
    assert seen_ids == {"1", "2", "3"}


def test_read_chunks_csv_gives_text_columns(tmp_path):
    path = tmp_path / "small.csv"
    path.write_text("ZIP code,Complaint ID\n07001,1\n811XX,2\n811XX,3\n")

    chunks = list(run.read_chunks(path, "csv", chunk_size=2))

    assert [len(chunk) for chunk in chunks] == [2, 1]
    assert chunks[0].loc[0, "ZIP code"] == "07001"  # leading zero kept


def test_read_chunks_rejects_unknown_format():
    with pytest.raises(ValueError, match="xml"):
        list(run.read_chunks("file.xml", "xml", chunk_size=10))


def test_complaints_schema_matches_clean_output():
    # The BigQuery schema must list exactly the columns clean_chunk() produces.
    raw = pd.DataFrame(columns=[
        "Date received", "Product", "Sub-product", "Issue", "Sub-issue",
        "Company public response", "Company", "State", "ZIP code", "Tags",
        "Submitted via", "Date sent to company", "Company response to consumer",
        "Timely response?", "Complaint ID",
    ], dtype="string")
    good, rejects, _ = clean.clean_chunk(raw)

    assert list(good.columns) == [field.name for field in run.COMPLAINTS_SCHEMA]
    assert list(rejects.columns) == [field.name for field in run.REJECTS_SCHEMA]
