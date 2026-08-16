"""Unknown-column namespacing, reserved-field quarantine, and column-cap tests.

All tests go through the public entry point :func:`process_batch`, per the
ticket. ADR-0001 guarantees the pipeline's computed ``validation_status``,
``errors``, and ``extra`` fields cannot be spoofed by a partner CSV column of
the same name.
"""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

import pytest

from batch_intake import BatchParseError, process_batch

FIXTURES = Path(__file__).parent / "fixtures"

SCHEMA = ["customer_id", "region", "email", "phone", "notes"]


def _build_csv(fieldnames: list[str], rows: list[dict[str, str]]) -> str:
    """Build CSV contents with proper quoting for the given fieldnames."""
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def test_unknown_columns_appear_under_extra_not_top_level() -> None:
    result = process_batch(FIXTURES / "extra_columns.csv")
    assert len(result.records) == 1
    record = result.records[0]
    # Unknown partner columns are namespaced under extra, not flat-merged.
    assert record.extra == {"loyalty_tier": "gold", "signup_source": "web"}
    # The record has no attribute for unknown columns.
    assert not hasattr(record, "loyalty_tier")
    assert not hasattr(record, "signup_source")


def test_validation_status_column_quarantined_and_computed_status_intact() -> None:
    # Adversarial CSV: bad email + a spoofed validation_status='valid' column.
    result = process_batch(FIXTURES / "adversarial_reserved_columns.csv")
    assert len(result.records) == 1
    record = result.records[0]
    # The pipeline's computed verdict wins: bad email => invalid.
    assert record.validation_status == "invalid"
    assert any("email" in err for err in record.errors)
    # The spoofed column is quarantined under a conflict key, not dropped.
    assert record.extra["validation_status__conflict"] == "valid"


def test_errors_column_quarantined_under_conflict_key() -> None:
    contents = _build_csv(
        SCHEMA + ["errors"],
        [
            {
                "customer_id": "1",
                "region": "EMEA",
                "email": "ok@example.com",
                "phone": "+44 20 7946 0958",
                "notes": "",
                "errors": "spoofed",
            }
        ],
    )
    result = process_batch(contents)
    record = result.records[0]
    # Computed errors list is empty (valid record); the spoofed value is
    # quarantined, not merged onto the record.
    assert record.errors == []
    assert record.extra["errors__conflict"] == "spoofed"


def test_extra_column_quarantined_under_conflict_key() -> None:
    contents = _build_csv(
        SCHEMA + ["extra"],
        [
            {
                "customer_id": "1",
                "region": "EMEA",
                "email": "ok@example.com",
                "phone": "+44 20 7946 0958",
                "notes": "",
                "extra": "injected",
            }
        ],
    )
    result = process_batch(contents)
    record = result.records[0]
    # The partner's `extra` column cannot overwrite the extra dict; it is
    # quarantined under a conflict key inside the real extra dict.
    assert record.extra == {"extra__conflict": "injected"}


def test_more_than_64_columns_raises_file_level_parse_error() -> None:
    with pytest.raises(BatchParseError) as exc_info:
        process_batch(FIXTURES / "too_many_columns.csv")
    # The error message names the cap so the caller can report it.
    assert "64" in str(exc_info.value)


def test_sixty_four_columns_is_accepted() -> None:
    # Exactly at the cap: 5 schema + 59 unknown = 64 columns.
    fieldnames = SCHEMA + [f"extra_{i}" for i in range(1, 60)]
    assert len(fieldnames) == 64
    contents = _build_csv(
        fieldnames,
        [
            {
                "customer_id": "1",
                "region": "EMEA",
                "email": "ok@example.com",
                "phone": "+44 20 7946 0958",
                "notes": "",
            }
        ],
    )
    result = process_batch(contents)
    assert result.summary.total_records == 1
    assert result.records[0].validation_status == "valid"


def test_end_to_end_adversarial_validation_status_and_too_many_columns() -> None:
    # End-to-end: the adversarial fixture parses with the pipeline's verdict
    # intact, and the >64-column fixture surfaces a file-level parse error.
    adversarial = process_batch(FIXTURES / "adversarial_reserved_columns.csv")
    assert adversarial.records[0].validation_status == "invalid"
    assert adversarial.records[0].extra["validation_status__conflict"] == "valid"

    with pytest.raises(BatchParseError):
        process_batch(FIXTURES / "too_many_columns.csv")
