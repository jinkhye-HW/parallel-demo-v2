"""Happy-path parse, summary, and render for partner batch files."""

from __future__ import annotations

import csv
import os
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


def _parse_records(contents: str) -> list[Record]:
    reader = csv.DictReader(StringIO(contents))
    records: list[Record] = []
    for row in reader:
        values = {name: (row.get(name) or "") for name in SCHEMA_FIELDS}
        records.append(
            Record(
                customer_id=values["customer_id"],
                region=values["region"],
                email=values["email"],
                phone=values["phone"],
                notes=values["notes"],
                validation_status="valid",
                errors=[],
                extra={},
            )
        )
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
