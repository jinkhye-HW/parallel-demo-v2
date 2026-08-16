"""Format-tolerance tests: encoding, delimiter, section-grouping, headerless.

All tests go through the public entry point :func:`process_batch`, per the
ticket. The parser must tolerate "weird" partner files: BOM/mixed encodings,
non-comma delimiters, section-grouped blocks, and must reject headerless files
with a file-level :class:`BatchParseError` rather than silently mis-parsing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from batch_intake import BatchParseError, process_batch

FIXTURES = Path(__file__).parent / "fixtures"


def test_bom_encoded_file_parses_without_error() -> None:
    result = process_batch(FIXTURES / "bom_batch.csv")
    assert result.summary.total_records == 2
    # The BOM must not leak into the first column name or value.
    assert result.records[0].customer_id == "1001"
    assert result.records[0].region == "EMEA"
    assert result.records[0].email == "alice@example.com"


def test_mixed_encoding_file_parses_via_replace_without_raising() -> None:
    # The file contains a non-UTF-8 byte; decoding with errors="replace" must
    # never raise, and the records are still produced.
    result = process_batch(FIXTURES / "mixed_encoding.csv")
    assert result.summary.total_records == 2
    assert result.records[0].customer_id == "1001"
    assert result.records[1].customer_id == "1002"


@pytest.mark.parametrize(
    "filename",
    ["tab_delimited.csv", "semicolon_delimited.csv", "pipe_delimited.csv"],
)
def test_non_comma_delimiter_auto_detected(filename: str) -> None:
    result = process_batch(FIXTURES / filename)
    assert result.summary.total_records == 2
    record = result.records[0]
    assert record.customer_id == "1001"
    assert record.region == "EMEA"
    assert record.email == "alice@example.com"
    assert record.phone == "442079460958"
    assert record.notes == "prefers email"


def test_section_grouped_csv_flattens_with_region_preserved() -> None:
    result = process_batch(FIXTURES / "section_grouped.csv")
    # Three data rows across two sections flatten into one record list.
    assert result.summary.total_records == 3
    regions = [r.region for r in result.records]
    assert regions == ["EMEA", "EMEA", "APAC"]
    # Schema fields are populated from the section's columns.
    assert result.records[0].customer_id == "1001"
    assert result.records[0].email == "alice@example.com"
    assert result.records[2].customer_id == "1003"
    assert result.records[2].email == "carol@example.com"


def test_headerless_file_surfaces_file_level_parse_error() -> None:
    with pytest.raises(BatchParseError) as exc_info:
        process_batch(FIXTURES / "headerless.csv")
    assert "header" in str(exc_info.value).lower()


def test_end_to_end_format_tolerance_fixtures() -> None:
    # BOM + mixed encoding parse without raising.
    bom = process_batch(FIXTURES / "bom_batch.csv")
    assert bom.summary.total_records == 2
    mixed = process_batch(FIXTURES / "mixed_encoding.csv")
    assert mixed.summary.total_records == 2

    # All non-comma delimiters parse correctly.
    for filename in (
        "tab_delimited.csv",
        "semicolon_delimited.csv",
        "pipe_delimited.csv",
    ):
        delimited = process_batch(FIXTURES / filename)
        assert delimited.summary.total_records == 2
        assert delimited.records[0].email == "alice@example.com"

    # Section-grouped flattens with region preserved.
    grouped = process_batch(FIXTURES / "section_grouped.csv")
    assert [r.region for r in grouped.records] == ["EMEA", "EMEA", "APAC"]

    # Headerless surfaces a file-level parse error.
    with pytest.raises(BatchParseError):
        process_batch(FIXTURES / "headerless.csv")


def test_oversized_field_raises_batch_parse_error_not_csv_error(
    tmp_path: Path,
) -> None:
    """A field exceeding csv.field_size_limit surfaces as BatchParseError.

    Without the catch in _read_rows, csv.DictReader raises a bare csv.Error
    out of process_batch and crashes the run. The pipeline must wrap it as a
    file-level BatchParseError, consistent with the delimiter-detection path.
    """
    import csv as _csv

    limit = _csv.field_size_limit()
    # A field comfortably larger than the limit (default 128 KiB).
    oversized = "x" * (limit + 1024)
    input_file = tmp_path / "oversized.csv"
    input_file.write_text(
        f"customer_id,region,email,phone,notes\n1,EMEA,a@b.com,+44 20,{oversized}\n",
        encoding="utf-8",
    )

    with pytest.raises(BatchParseError) as exc_info:
        process_batch(input_file)
    assert "CSV read error" in str(exc_info.value)
