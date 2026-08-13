"""Field validation tests (email, phone, notes) through the public entry point."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from batch_intake import process_batch

FIXTURES = Path(__file__).parent / "fixtures"

SCHEMA = ["customer_id", "region", "email", "phone", "notes"]


def _build_csv(rows: list[dict[str, str]]) -> str:
    """Build CSV contents with proper quoting for embedded control chars."""
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=SCHEMA)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def test_malformed_email_is_invalid_with_email_error() -> None:
    result = process_batch(FIXTURES / "bad_email.csv")
    assert len(result.records) == 1
    record = result.records[0]
    assert record.validation_status == "invalid"
    assert any("email" in err for err in record.errors)
    assert result.summary.invalid_count == 1
    assert result.summary.valid_count == 0


def test_valid_email_passes() -> None:
    result = process_batch(FIXTURES / "valid_batch.csv")
    for record in result.records:
        assert record.validation_status == "valid"
        assert record.errors == []


def test_phone_outside_range_is_invalid_with_phone_error() -> None:
    result = process_batch(FIXTURES / "bad_phone.csv")
    assert len(result.records) == 1
    record = result.records[0]
    assert record.validation_status == "invalid"
    assert any("phone" in err for err in record.errors)


def test_valid_phone_stored_as_normalized_digits() -> None:
    result = process_batch(FIXTURES / "valid_batch.csv")
    assert result.records[0].phone == "442079460958"
    assert result.records[1].phone == "6561234567"
    assert result.records[2].phone == "14155550142"


def test_long_notes_truncated_to_ten_thousand_chars() -> None:
    raw_notes = "a" * 10001 + "\x00bold\x07"
    contents = _build_csv(
        [
            {
                "customer_id": "1",
                "region": "EMEA",
                "email": "ok@example.com",
                "phone": "+44 20 7946 0958",
                "notes": raw_notes,
            }
        ]
    )
    result = process_batch(contents)
    record = result.records[0]
    assert record.validation_status == "valid"
    assert len(record.notes) == 10000
    assert record.notes == "a" * 10000


def test_control_chars_stripped_except_newline_and_tab() -> None:
    raw_notes = "line1\x00\x07\nline2\ttabbed"
    contents = _build_csv(
        [
            {
                "customer_id": "1",
                "region": "EMEA",
                "email": "ok@example.com",
                "phone": "+44 20 7946 0958",
                "notes": raw_notes,
            }
        ]
    )
    result = process_batch(contents)
    record = result.records[0]
    assert record.notes == "line1\nline2\ttabbed"


def test_invalid_count_matches_invalid_records_in_mixed_batch() -> None:
    result = process_batch(FIXTURES / "mixed_validation.csv")
    assert result.summary.total_records == 3
    assert result.summary.invalid_count == 2
    assert result.summary.valid_count == 1
    # Row 4001: bad email; Row 4002: bad phone; Row 4003: valid.
    assert result.records[0].validation_status == "invalid"
    assert result.records[1].validation_status == "invalid"
    assert result.records[2].validation_status == "valid"
