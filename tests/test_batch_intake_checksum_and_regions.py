"""ID checksum and per-region summary stats through the public entry point."""

from __future__ import annotations

from pathlib import Path

import pytest

from batch_intake import process_batch

FIXTURES = Path(__file__).parent / "fixtures"


def _csv(customer_ids: list[str], region: str = "EMEA") -> str:
    rows = "\n".join(
        f"{cid},{region},ok@example.com,+44 20 7946 0958,ok" for cid in customer_ids
    )
    return "customer_id,region,email,phone,notes\n" + rows + "\n"


# Known Luhn results:
#   79927398713 -> valid (Wikipedia example)
#   79927398710 -> invalid (last digit changed)
#   18 -> valid  (8 + 1*2 = 10)
#   19 -> invalid (9 + 1*2 = 11)
#   26 -> valid  (6 + 2*2 = 10)


@pytest.mark.parametrize(
    "customer_id, expected",
    [
        ("79927398713", True),
        ("79927398710", False),
        ("18", True),
        ("19", False),
        ("26", True),
    ],
)
def test_default_checksum_is_luhn(customer_id: str, expected: bool) -> None:
    result = process_batch(_csv([customer_id]))
    assert result.summary.checksum_valid_count == (1 if expected else 0)


def test_checksum_valid_count_counts_only_luhn_valid_ids() -> None:
    result = process_batch(_csv(["79927398713", "79927398710", "18", "19", "26"]))
    assert result.summary.checksum_valid_count == 3


def test_custom_checksum_callable_overrides_luhn() -> None:
    # A partner rule: only the literal id "18" is valid. Under Luhn both "18"
    # and "26" would be valid (count 2), so a count of 1 proves the custom
    # callable overrode the default.
    def partner_rule(customer_id: str) -> bool:
        return customer_id == "18"

    result = process_batch(_csv(["79927398713", "18", "26"]), checksum=partner_rule)
    assert result.summary.checksum_valid_count == 1


def test_per_region_has_one_entry_per_region_in_first_appearance_order() -> None:
    result = process_batch(FIXTURES / "checksum_multi_region.csv")
    per_region = result.summary.per_region
    assert [r.name for r in per_region] == ["EMEA", "APAC", "AMER"]


def test_per_region_counts_records_valid_invalid() -> None:
    result = process_batch(FIXTURES / "checksum_multi_region.csv")
    by_name = {r.name: r for r in result.summary.per_region}

    # EMEA: 2 records, row 2 has a bad email -> 1 valid, 1 invalid.
    assert by_name["EMEA"].records == 2
    assert by_name["EMEA"].valid == 1
    assert by_name["EMEA"].invalid == 1

    # APAC: 2 records, both valid.
    assert by_name["APAC"].records == 2
    assert by_name["APAC"].valid == 2
    assert by_name["APAC"].invalid == 0

    # AMER: 1 record, valid.
    assert by_name["AMER"].records == 1
    assert by_name["AMER"].valid == 1
    assert by_name["AMER"].invalid == 0


def test_end_to_end_multi_region_checksum_and_region_stats() -> None:
    result = process_batch(FIXTURES / "checksum_multi_region.csv")

    # Five records, three Luhn-valid IDs.
    assert result.summary.total_records == 5
    assert result.summary.checksum_valid_count == 3

    # Per-region records sum back to the total.
    assert sum(r.records for r in result.summary.per_region) == 5
    # Per-region valid/invalid sum back to the summary totals.
    assert sum(r.valid for r in result.summary.per_region) == result.summary.valid_count
    assert (
        sum(r.invalid for r in result.summary.per_region)
        == result.summary.invalid_count
    )
