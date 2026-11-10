"""
Tests for ingest/clean.py.

Every test builds a tiny made-up table, so no test needs the big CSV file
and no test connects to BigQuery.
"""

import pandas as pd
import pytest

from ingest import clean

# The 15 column names exactly as they appear in the raw CSV file.
RAW_COLUMNS = [
    "Date received",
    "Product",
    "Sub-product",
    "Issue",
    "Sub-issue",
    "Company public response",
    "Company",
    "State",
    "ZIP code",
    "Tags",
    "Submitted via",
    "Date sent to company",
    "Company response to consumer",
    "Timely response?",
    "Complaint ID",
]


def make_row(**changes):
    """One valid, already-renamed complaint row. Pass keyword args to change fields."""
    row = {
        "date_received": "2017-03-01",
        "product": "Mortgage",
        "sub_product": "Conventional fixed mortgage",
        "issue": "Loan servicing",
        "sub_issue": "Escrow problem",
        "company_public_response": "Company has responded",
        "company": "TD BANK US HOLDING COMPANY",
        "state": "NJ",
        "zip_code": "07001",
        "tags": "Older American",
        "submitted_via": "Web",
        "date_sent_to_company": "2017-03-03",
        "company_response_to_consumer": "Closed with explanation",
        "timely_response": "Yes",
        "complaint_id": "1000001",
    }
    row.update(changes)
    return row


def make_df(*rows):
    """Build a DataFrame of text columns, like reading the CSV with dtype="string"."""
    return pd.DataFrame(list(rows), dtype="string")


# ---------- column names ----------

def test_to_snake_case_examples():
    assert clean.to_snake_case("Timely response?") == "timely_response"
    assert clean.to_snake_case("Sub-product") == "sub_product"
    assert clean.to_snake_case("ZIP code") == "zip_code"


def test_rename_columns_gives_expected_names():
    raw = pd.DataFrame(columns=RAW_COLUMNS)
    renamed = clean.rename_columns(raw)
    assert list(renamed.columns) == clean.EXPECTED_COLUMNS


def test_check_columns_raises_when_a_column_is_missing():
    df = make_df(make_row()).drop(columns=["company"])
    with pytest.raises(ValueError, match="company"):
        clean.check_columns(df)


def test_check_columns_drops_extra_columns():
    df = make_df(make_row(extra_column="x"))
    checked = clean.check_columns(df)
    assert list(checked.columns) == clean.EXPECTED_COLUMNS


# ---------- text cleaning ----------

def test_clean_text_trims_and_collapses_spaces():
    df = make_df(make_row(issue="  Loan   servicing  "))
    assert clean.clean_text(df).loc[0, "issue"] == "Loan servicing"


def test_clean_text_turns_blanks_into_na():
    df = make_df(make_row(sub_issue="   "))
    assert pd.isna(clean.clean_text(df).loc[0, "sub_issue"])


def test_clean_text_keeps_company_case():
    df = make_df(make_row(company="Wells Fargo & Company"))
    assert clean.clean_text(df).loc[0, "company"] == "Wells Fargo & Company"


def test_clean_text_does_not_change_the_input():
    df = make_df(make_row(issue=" x "))
    clean.clean_text(df)
    assert df.loc[0, "issue"] == " x "


# ---------- year filter ----------

def test_filter_years_keeps_only_2016_to_2018():
    df = make_df(
        make_row(date_received="2015-12-31", complaint_id="1"),
        make_row(date_received="2016-01-01", complaint_id="2"),
        make_row(date_received="2018-12-31", complaint_id="3"),
        make_row(date_received="2019-01-01", complaint_id="4"),
    )
    kept = clean.filter_years(df)
    assert list(kept["complaint_id"]) == ["2", "3"]


def test_filter_years_keeps_unreadable_dates_for_rejection():
    df = make_df(make_row(date_received="not a date"))
    assert len(clean.filter_years(df)) == 1


# ---------- rejects ----------

@pytest.mark.parametrize(
    "changes, expected_reason",
    [
        ({"complaint_id": pd.NA}, "missing complaint_id"),
        ({"date_received": "31/02/2017"}, "invalid date_received"),
        ({"date_sent_to_company": "2017-02-27"}, "sent before received"),
        ({"company": pd.NA}, "missing company"),
        ({"product": pd.NA}, "missing product"),
    ],
)
def test_split_rejects_gives_the_right_reason(changes, expected_reason):
    df = make_df(make_row(**changes))
    good, rejects = clean.split_rejects(df)
    assert len(good) == 0
    assert list(rejects["reject_reason"]) == [expected_reason]


def test_split_rejects_uses_first_reason_only():
    df = make_df(make_row(complaint_id=pd.NA, company=pd.NA))
    _, rejects = clean.split_rejects(df)
    assert list(rejects["reject_reason"]) == ["missing complaint_id"]


def test_split_rejects_keeps_good_rows():
    df = make_df(make_row(), make_row(company=pd.NA, complaint_id="2"))
    good, rejects = clean.split_rejects(df)
    assert list(good["complaint_id"]) == ["1000001"]
    assert len(rejects) == 1


def test_missing_sent_date_is_not_rejected():
    df = make_df(make_row(date_sent_to_company=pd.NA))
    good, rejects = clean.split_rejects(df)
    assert len(good) == 1
    assert len(rejects) == 0


# ---------- duplicates ----------

def test_drop_duplicates_uses_complaint_id_only():
    # Same complaint_id but a different issue: still counts as a duplicate.
    df = make_df(make_row(issue="A"), make_row(issue="B"), make_row(complaint_id="2"))
    deduped = clean.drop_duplicates(df)
    assert list(deduped["complaint_id"]) == ["1000001", "2"]
    assert deduped.iloc[0]["issue"] == "A"  # first copy is kept


# ---------- filling gaps ----------

def test_fill_missing_uses_agreed_values():
    df = make_df(
        make_row(sub_issue=pd.NA, company_public_response=pd.NA, tags=pd.NA, state=pd.NA)
    )
    filled = clean.fill_missing(df)
    assert filled.loc[0, "sub_issue"] == "Not provided"
    assert filled.loc[0, "company_public_response"] == "No public response"
    assert filled.loc[0, "tags"] == "None"
    assert filled.loc[0, "state"] == "Unknown"


def test_fill_missing_uppercases_state():
    df = make_df(make_row(state="ny"))
    assert clean.fill_missing(df).loc[0, "state"] == "NY"


def test_fill_missing_leaves_other_gaps_alone():
    df = make_df(make_row(sub_product=pd.NA))
    assert pd.isna(clean.fill_missing(df).loc[0, "sub_product"])


# ---------- types and features ----------

def test_convert_types_makes_is_timely_boolean():
    df = make_df(
        make_row(timely_response="Yes"),
        make_row(timely_response="No"),
        make_row(timely_response=pd.NA),
    )
    converted = clean.convert_types(df)
    assert "timely_response" not in converted.columns
    assert converted["is_timely"].tolist()[:2] == [True, False]
    assert pd.isna(converted.loc[2, "is_timely"])


def test_convert_types_makes_real_dates_and_keeps_zip_as_text():
    df = make_df(make_row(zip_code="811XX"))
    converted = clean.convert_types(df)
    assert converted.loc[0, "date_received"] == pd.Timestamp("2017-03-01")
    assert converted.loc[0, "zip_code"] == "811XX"


def test_add_features_days_to_company():
    df = clean.convert_types(make_df(make_row(), make_row(date_sent_to_company=pd.NA)))
    with_features = clean.add_features(df)
    assert with_features.loc[0, "days_to_company"] == 2
    assert pd.isna(with_features.loc[1, "days_to_company"])


# ---------- the sample file in samples/ ----------

def test_sample_input_file_hits_every_reject_reason():
    # samples/sample_input_complaints.csv has one broken row per reject reason.
    raw = pd.read_csv("samples/sample_input_complaints.csv", dtype="string")
    good, rejects, counts = clean.clean_chunk(raw)

    assert sorted(rejects["reject_reason"]) == sorted([
        "missing complaint_id",
        "invalid date_received",
        "sent before received",
        "missing company",
        "missing product",
    ])
    assert counts["rows_duplicate"] == 1
    assert counts["rows_out_of_range"] == 1
    assert len(good) == 4


# ---------- the whole chunk ----------

def test_clean_chunk_end_to_end():
    raw_rows = [
        # good row, with messy spaces and a lowercase state
        ["2017-03-01", "Mortgage", "Other", " Loan  servicing ", "", "", "TD BANK",
         "nj", "811XX", "", "Web", "2017-03-03", "Closed", "Yes", "1"],
        # duplicate of complaint 1: dropped
        ["2017-03-01", "Mortgage", "Other", "Something else", "", "", "TD BANK",
         "nj", "811XX", "", "Web", "2017-03-03", "Closed", "Yes", "1"],
        # missing company: rejected
        ["2017-03-01", "Mortgage", "Other", "Issue", "", "", "",
         "NY", "10001", "", "Web", "2017-03-03", "Closed", "No", "2"],
        # outside 2016-2018: filtered out, not rejected
        ["2024-05-30", "Mortgage", "Other", "Issue", "", "", "TD BANK",
         "NY", "10001", "", "Web", "2024-05-30", "Closed", "Yes", "3"],
    ]
    raw = pd.DataFrame(raw_rows, columns=RAW_COLUMNS, dtype="string")

    good, rejects, counts = clean.clean_chunk(raw)

    assert counts == {
        "rows_read": 4,
        "rows_out_of_range": 1,
        "rows_rejected": 1,
        "rows_duplicate": 1,
    }
    assert list(good["complaint_id"]) == ["1"]
    row = good.iloc[0]
    assert row["issue"] == "Loan servicing"
    assert row["state"] == "NJ"
    assert row["sub_issue"] == "Not provided"
    assert row["zip_code"] == "811XX"
    assert row["is_timely"] == True  # noqa: E712 (pandas boolean, not plain bool)
    assert row["days_to_company"] == 2

    assert list(rejects["complaint_id"]) == ["2"]
    assert list(rejects["reject_reason"]) == ["missing company"]
