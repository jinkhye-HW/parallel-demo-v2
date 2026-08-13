"""End-to-end test at the public entry point for the happy-path slice."""

from __future__ import annotations

from pathlib import Path

import pytest

from batch_intake import BatchResult, process_batch

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "valid_batch.csv"


@pytest.fixture
def valid_csv_contents() -> str:
    """UTF-8 contents of the valid-batch fixture."""

    return FIXTURE_PATH.read_text(encoding="utf-8")


def test_process_batch_valid_csv_returns_records_summary_and_report(
    valid_csv_contents: str,
) -> None:
    template = (
        "Records: {{total_records}} | Valid: {{valid_count}} "
        "| Invalid: {{invalid_count}}"
    )

    result = process_batch(valid_csv_contents, template=template)

    assert isinstance(result, BatchResult)
    assert len(result.records) == 3

    first = result.records[0]
    assert first.customer_id == "1001"
    assert first.region == "EMEA"
    assert first.email == "alice@example.com"
    assert first.phone == "+44-20-7946-0958"
    assert first.notes == "preferred"
    assert first.validation_status == "valid"
    assert first.errors == []
    assert first.extra == {}

    assert result.summary.total_records == 3
    assert result.summary.valid_count == 3
    assert result.summary.invalid_count == 0

    assert result.report == "Records: 3 | Valid: 3 | Invalid: 0"


def test_process_batch_accepts_path_to_file() -> None:
    result = process_batch(FIXTURE_PATH)

    assert result.summary.total_records == 3
    assert result.report == "Total: 3, Valid: 3, Invalid: 0"
