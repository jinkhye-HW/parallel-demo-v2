"""Disk cache of parsed records + summary, through the public entry point.

Cache key is the SHA-256 of the input file's contents; the cache file is
``<cache_dir>/<sha256_hex>.json``. On a hit the parsed records and summary are
loaded from disk and parsing is skipped; on a miss or hash mismatch the file is
re-parsed and the cache (over)written. The report is always rendered fresh
against the call's template. Tests use a tmp dir for the cache so the repo is
not polluted.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from batch_intake import process_batch
from batch_intake.pipeline import DEFAULT_CACHE_DIRNAME

CSV = (
    "customer_id,region,email,phone,notes\n"
    "79927398713,EMEA,alice@example.com,+44 20 7946 0958,hello\n"
    "79927398710,APAC,bob@example.com,+65 6123 4567,world\n"
)

CSV_AFTER_MODIFY = (
    "customer_id,region,email,phone,notes\n"
    "79927398713,EMEA,alice@example.com,+44 20 7946 0958,changed notes\n"
    "79927398710,APAC,bob@example.com,+65 6123 4567,world\n"
    "18,AMER,carol@example.com,+1 415 555 0142,extra row\n"
)


def _write_input(tmp_path: Path, contents: str = CSV) -> Path:
    input_file = tmp_path / "input.csv"
    # newline="" so the bytes on disk are exactly contents.encode("utf-8");
    # the cache key is the SHA-256 of those bytes, and we assert against the
    # same encoding below.
    input_file.write_text(contents, encoding="utf-8", newline="")
    return input_file


def _cache_file(cache_dir: Path, contents: str) -> Path:
    key = hashlib.sha256(contents.encode("utf-8")).hexdigest()
    return cache_dir / f"{key}.json"


def test_first_run_parses_and_writes_cache_keyed_by_sha256(tmp_path: Path) -> None:
    input_file = _write_input(tmp_path)
    cache_dir = tmp_path / "cache"

    result = process_batch(input_file, cache_dir=cache_dir)

    cache_file = _cache_file(cache_dir, CSV)
    assert cache_file.is_file()
    assert cache_file.name == hashlib.sha256(CSV.encode("utf-8")).hexdigest() + ".json"

    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    assert "records" in payload and "summary" in payload
    assert len(payload["records"]) == result.summary.total_records == 2
    # Records + summary only; no pre-rendered report in the cache.
    assert "report" not in payload


def test_second_run_on_unchanged_file_loads_from_cache_and_skips_parse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_file = _write_input(tmp_path)
    cache_dir = tmp_path / "cache"

    first = process_batch(input_file, cache_dir=cache_dir)

    def _boom(contents: str) -> list[object]:
        raise AssertionError("parse must be skipped on a cache hit")

    monkeypatch.setattr("batch_intake.pipeline._parse_records", _boom)

    second = process_batch(input_file, cache_dir=cache_dir)

    assert second.records == first.records
    assert second.summary == first.summary


def test_modifying_file_re_parses_and_overwrites_cache(tmp_path: Path) -> None:
    input_file = _write_input(tmp_path)
    cache_dir = tmp_path / "cache"

    process_batch(input_file, cache_dir=cache_dir)
    old_cache = _cache_file(cache_dir, CSV)
    assert old_cache.is_file()

    input_file.write_text(CSV_AFTER_MODIFY, encoding="utf-8", newline="")

    result = process_batch(input_file, cache_dir=cache_dir)

    # Re-parsed: the new content has three records and changed notes.
    assert result.summary.total_records == 3
    assert result.records[0].notes == "changed notes"

    # The cache now holds an entry for the new content (keyed by its SHA-256).
    new_cache = _cache_file(cache_dir, CSV_AFTER_MODIFY)
    assert new_cache.is_file()
    payload = json.loads(new_cache.read_text(encoding="utf-8"))
    assert len(payload["records"]) == 3


def test_cache_location_configurable_default_alongside_input(tmp_path: Path) -> None:
    input_file = _write_input(tmp_path)
    # With no cache_dir, the default is `.batch_cache/` alongside the input file.
    default_cache_dir = input_file.parent / DEFAULT_CACHE_DIRNAME

    process_batch(input_file)

    assert default_cache_dir.is_dir()
    assert _cache_file(default_cache_dir, CSV).is_file()

    # An explicit cache_dir overrides the default location.
    explicit = tmp_path / "custom_cache"
    input_file.write_text(CSV, encoding="utf-8", newline="")  # same content
    process_batch(input_file, cache_dir=explicit)
    assert _cache_file(explicit, CSV).is_file()


def test_report_always_rendered_fresh_against_call_template_on_cache_hit(
    tmp_path: Path,
) -> None:
    input_file = _write_input(tmp_path)
    cache_dir = tmp_path / "cache"

    process_batch(input_file, template="A: {{total_records}}", cache_dir=cache_dir)

    # Same file (cache hit) but a different template: the report must reflect
    # the new template, proving rendering always runs fresh.
    result_b = process_batch(
        input_file, template="B: valid={{valid_count}}", cache_dir=cache_dir
    )
    assert result_b.report == "B: valid=2"

    result_default = process_batch(input_file, cache_dir=cache_dir)
    assert result_default.report != result_b.report


def test_cache_key_is_content_hash_independent_of_file_name(tmp_path: Path) -> None:
    # Two files with identical contents but different names: the cache key is
    # the SHA-256 of the contents, so the cache filename is the same. The cache
    # path is derived from the input file path / contents, never from a
    # partner-supplied string.
    one = tmp_path / "partner_a.csv"
    two = tmp_path / "partner_b.csv"
    one.write_text(CSV, encoding="utf-8", newline="")
    two.write_text(CSV, encoding="utf-8", newline="")
    cache_dir = tmp_path / "cache"

    process_batch(one, cache_dir=cache_dir)
    process_batch(two, cache_dir=cache_dir)

    key = hashlib.sha256(CSV.encode("utf-8")).hexdigest()
    assert list(cache_dir.iterdir()) == [cache_dir / f"{key}.json"]


def test_cache_hit_with_custom_checksum_recomputes_count(tmp_path: Path) -> None:
    input_file = _write_input(tmp_path)
    cache_dir = tmp_path / "cache"

    def accept_nothing(customer_id: str) -> bool:
        return False

    first = process_batch(input_file, cache_dir=cache_dir, checksum=accept_nothing)
    assert first.summary.checksum_valid_count == 0

    def accept_everything(customer_id: str) -> bool:
        return True

    # Cache hit, but a different checksum predicate: the count must reflect the
    # call's predicate, not a stale cached value.
    second = process_batch(input_file, cache_dir=cache_dir, checksum=accept_everything)
    assert second.summary.checksum_valid_count == 2


def test_raw_contents_source_is_not_cached(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"

    process_batch(CSV, cache_dir=cache_dir)

    # No input file path to derive a cache location from, so nothing is written.
    assert not cache_dir.exists() or not any(cache_dir.iterdir())


def test_tampered_cache_recomputed_verdict_wins(tmp_path: Path) -> None:
    """A tampered cache file must NOT be trusted for validation_status / errors.

    An attacker who can write into the cache directory could plant
    ``validation_status: "valid"`` on a record with a bad email, and inject a
    reserved name into ``extra`` to defeat the ADR-0001 quarantine. On a cache
    hit the pipeline must recompute the verdict from the cached raw fields and
    re-quarantine reserved names, so the on-disk verdict is irrelevant.
    """
    input_file = _write_input(tmp_path)
    cache_dir = tmp_path / "cache"

    # Build a tampered cache payload by hand: one record with a bad email but
    # validation_status forced to "valid", and a reserved name ("errors")
    # planted directly in extra.
    key = hashlib.sha256(CSV.encode("utf-8")).hexdigest()
    cache_file = cache_dir / f"{key}.json"
    cache_dir.mkdir(parents=True, exist_ok=True)
    tampered = {
        "records": [
            {
                "customer_id": "79927398713",
                "region": "EMEA",
                "email": "not-an-email",
                "phone": "442079460958",
                "notes": "hello",
                "validation_status": "valid",  # planted lie
                "errors": [],  # planted lie
                "extra": {
                    "errors": "injected reserved name",  # reserved name in extra
                    "partner_col": "ok",
                },
            },
            {
                "customer_id": "79927398710",
                "region": "APAC",
                "email": "bob@example.com",
                "phone": "6561234567",
                "notes": "world",
                "validation_status": "valid",
                "errors": [],
                "extra": {},
            },
        ],
        "summary": {
            "total_records": 2,
            "valid_count": 2,  # planted lie
            "invalid_count": 0,
            "checksum_valid_count": 2,
            "per_region": [
                {"name": "EMEA", "records": 1, "valid": 1, "invalid": 0},
                {"name": "APAC", "records": 1, "valid": 1, "invalid": 0},
            ],
        },
    }
    cache_file.write_text(json.dumps(tampered), encoding="utf-8")

    result = process_batch(input_file, cache_dir=cache_dir)

    # The recomputed verdict wins: the bad-email record is invalid.
    bad = result.records[0]
    assert bad.validation_status == "invalid"
    assert any("not a valid email" in e for e in bad.errors)
    # The reserved name in extra is quarantined under __conflict.
    assert "errors" not in bad.extra
    assert bad.extra["errors__conflict"] == "injected reserved name"
    assert bad.extra["partner_col"] == "ok"


def test_end_to_end_cache_hit_miss_and_template_variation(tmp_path: Path) -> None:
    input_file = _write_input(tmp_path)
    cache_dir = tmp_path / "cache"

    # First run: parse + write cache.
    r1 = process_batch(input_file, cache_dir=cache_dir)
    assert r1.summary.total_records == 2

    # Second run, unchanged: cache hit, same records + summary, fresh report.
    r2 = process_batch(
        input_file, template="total={{total_records}}", cache_dir=cache_dir
    )
    assert r2.records == r1.records
    assert r2.summary == r1.summary
    assert r2.report == "total=2"

    # Modify the file: cache miss, re-parse, overwrite.
    input_file.write_text(CSV_AFTER_MODIFY, encoding="utf-8", newline="")
    r3 = process_batch(input_file, cache_dir=cache_dir)
    assert r3.summary.total_records == 3
    assert _cache_file(cache_dir, CSV_AFTER_MODIFY).is_file()
