from __future__ import annotations

from pathlib import Path

from batch_intake import process_batch

FIXTURE = Path(__file__).parent / "fixtures" / "valid_batch.csv"


def test_valid_csv_round_trips_through_public_entry_point() -> None:
    result = process_batch(FIXTURE)

    # Records: all valid, schema fields populated, unknown columns ignored.
    assert len(result.records) == 3
    for record in result.records:
        assert record.validation_status == "valid"
        assert record.errors == []
        assert record.extra == {}

    assert result.records[0].customer_id == "1001"
    assert result.records[0].region == "EMEA"
    assert result.records[0].email == "alice@example.com"
    assert result.records[0].phone == "442079460958"
    assert result.records[0].notes == "prefers email"
    assert result.records[2].notes == ""

    # Summary counts.
    assert result.summary.total_records == 3
    assert result.summary.valid_count == 3
    assert result.summary.invalid_count == 0

    # Rendered report substitutes scalar placeholders.
    assert "3" in result.report


def test_custom_template_substitutes_scalar_placeholders() -> None:
    template = "total={{total_records}} valid={{valid_count}} invalid={{invalid_count}}"
    result = process_batch(FIXTURE, template=template)
    assert result.report == "total=3 valid=3 invalid=0"


def test_accepts_raw_csv_contents() -> None:
    contents = "customer_id,region,email,phone,notes\n" "1,EMEA,a@example.com,+1,hi\n"
    result = process_batch(contents)
    assert result.summary.total_records == 1
    assert result.records[0].customer_id == "1"
