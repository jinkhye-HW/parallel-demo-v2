"""Parse, validate, summarise, and render partner batch files."""

from __future__ import annotations

import csv
import os
import re
import unicodedata
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Literal

import chevron

ValidationStatus = Literal["valid", "invalid"]

# Canonical schema fields the pipeline knows about. Unknown partner columns are
# ignored in this slice (see ADR 0001 for the eventual `extra` namespacing).
SCHEMA_FIELDS: tuple[str, ...] = (
    "customer_id",
    "region",
    "email",
    "phone",
    "notes",
)

# Pinned linear email pattern: no nested or overlapping quantifiers, so it is
# ReDoS-safe on partner-controlled text. Do not substitute a backtracking-prone
# pattern (see practices/security-practice.md, "re against untrusted input").
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Phone is stored as the digit run; 7-15 digits are accepted.
PHONE_MIN_DIGITS = 7
PHONE_MAX_DIGITS = 15

# Notes are plain text into a text template: capped length, control chars
# stripped (newline and tab preserved as structural whitespace).
NOTES_MAX_LENGTH = 10_000

DEFAULT_TEMPLATE = (
    "Batch report\n"
    "total_records: {{total_records}}\n"
    "valid_count: {{valid_count}}\n"
    "invalid_count: {{invalid_count}}\n"
)


@dataclass(frozen=True)
class Record:
    """One customer entry parsed from a row of a batch."""

    customer_id: str
    region: str
    email: str
    phone: str
    notes: str
    validation_status: ValidationStatus
    errors: list[str]
    extra: dict[str, str]


@dataclass(frozen=True)
class Summary:
    """Aggregate counts across the parsed batch."""

    total_records: int
    valid_count: int
    invalid_count: int


@dataclass(frozen=True)
class BatchResult:
    """The parsed records, summary stats, and rendered report."""

    records: list[Record]
    summary: Summary
    report: str


def _load_contents(source: str | os.PathLike[str]) -> str:
    """Read ``source`` as file contents.

    If ``source`` points at an existing file, read it as UTF-8 text. Otherwise
    treat it as raw CSV contents. This keeps the public entry point a single
    function that accepts a path or contents, per the ticket.
    """
    candidate = Path(os.fspath(source))
    if candidate.is_file():
        return candidate.read_text(encoding="utf-8")
    return os.fspath(source)


def _validate_email(email: str) -> list[str]:
    """Return a list of email error messages (empty if the email is valid)."""
    if not EMAIL_PATTERN.match(email):
        return [f"email: {email!r} is not a valid email address"]
    return []


def _normalize_phone(phone: str) -> tuple[str, list[str]]:
    """Extract digits from ``phone`` and validate the digit count.

    Returns the normalized digit string and a list of error messages. The
    normalized digits are returned regardless of validity so the record always
    carries the digit run.
    """
    # ASCII digits only: str.isdigit() also accepts Unicode digits (e.g. '٣'),
    # which would leak non-ASCII characters into the normalized digit string.
    digits = "".join(ch for ch in phone if "0" <= ch <= "9")
    errors: list[str] = []
    if not (PHONE_MIN_DIGITS <= len(digits) <= PHONE_MAX_DIGITS):
        errors.append(
            f"phone: must contain {PHONE_MIN_DIGITS} to {PHONE_MAX_DIGITS} digits, "
            f"got {len(digits)}"
        )
    return digits, errors


def _clean_notes(notes: str) -> str:
    """Strip control chars (except ``\\n`` and ``\\t``) and cap the length."""
    stripped = "".join(
        ch for ch in notes if ch in ("\n", "\t") or unicodedata.category(ch) != "Cc"
    )
    return stripped[:NOTES_MAX_LENGTH]


def _validate_record(values: dict[str, str]) -> Record:
    errors: list[str] = []
    errors.extend(_validate_email(values["email"]))
    phone_digits, phone_errors = _normalize_phone(values["phone"])
    errors.extend(phone_errors)
    notes = _clean_notes(values["notes"])
    return Record(
        customer_id=values["customer_id"],
        region=values["region"],
        email=values["email"],
        phone=phone_digits,
        notes=notes,
        validation_status="invalid" if errors else "valid",
        errors=errors,
        extra={},
    )


def _parse_records(contents: str) -> list[Record]:
    reader = csv.DictReader(StringIO(contents))
    records: list[Record] = []
    for row in reader:
        values = {name: (row.get(name) or "") for name in SCHEMA_FIELDS}
        records.append(_validate_record(values))
    return records


def _summarise(records: list[Record]) -> Summary:
    valid_count = sum(1 for r in records if r.validation_status == "valid")
    return Summary(
        total_records=len(records),
        valid_count=valid_count,
        invalid_count=len(records) - valid_count,
    )


def process_batch(
    source: str | os.PathLike[str],
    template: str | None = None,
) -> BatchResult:
    """Parse a partner batch file and render its summary report.

    Args:
        source: Path to a UTF-8 CSV file, or raw CSV contents. A string that
            points at an existing file is read from disk; anything else is
            treated as the CSV text itself.
        template: Optional mustache template with scalar placeholders
            (``{{total_records}}``, ``{{valid_count}}``, ``{{invalid_count}}``).
            Defaults to a built-in summary template.

    Returns:
        The parsed records, summary stats, and rendered report.
    """
    contents = _load_contents(source)
    records = _parse_records(contents)
    summary = _summarise(records)
    report = chevron.render(
        template or DEFAULT_TEMPLATE,
        {
            "total_records": summary.total_records,
            "valid_count": summary.valid_count,
            "invalid_count": summary.invalid_count,
        },
    )
    return BatchResult(records=records, summary=summary, report=report)
