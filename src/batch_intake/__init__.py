"""Partner batch intake pipeline.

Public entry point: :func:`process_batch` accepts a batch file (path or CSV
contents) and an optional report template, and returns the parsed records,
summary stats, and rendered report.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import chevron

__all__ = [
    "BatchResult",
    "Record",
    "Summary",
    "process_batch",
]

ValidationStatus = Literal["valid", "invalid"]

#: Default report template rendered when the caller omits one. Scalar
#: placeholders only -- no mustache sections.
DEFAULT_TEMPLATE: str = (
    "Total: {{total_records}}, Valid: {{valid_count}}, Invalid: {{invalid_count}}"
)


@dataclass(frozen=True)
class Record:
    """One customer entry parsed from a row of a batch.

    Invalid records are retained, not dropped; in this slice every record is
    ``valid`` with empty ``errors`` (field validation lands in a later ticket).
    """

    customer_id: str
    region: str
    email: str
    phone: str
    notes: str
    extra: dict[str, str] = field(default_factory=dict)
    validation_status: ValidationStatus = "valid"
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Summary:
    """Aggregate counts over a parsed batch."""

    total_records: int
    valid_count: int
    invalid_count: int


@dataclass(frozen=True)
class BatchResult:
    """The result of processing a batch: records, summary, and rendered report."""

    records: list[Record]
    summary: Summary
    report: str


def _read_csv(contents: str) -> list[Record]:
    """Parse CSV ``contents`` into records on the happy path.

    Args:
        contents: UTF-8, comma-delimited CSV with a header row and a
            ``region`` column.

    Returns:
        Records carrying the known schema fields; unknown columns are ignored.
    """

    reader = csv.DictReader(contents.splitlines())
    records: list[Record] = []
    for row in reader:
        records.append(
            Record(
                customer_id=row.get("customer_id", ""),
                region=row.get("region", ""),
                email=row.get("email", ""),
                phone=row.get("phone", ""),
                notes=row.get("notes", ""),
            )
        )
    return records


def _summarize(records: list[Record]) -> Summary:
    """Build summary stats from ``records``."""

    valid = sum(1 for r in records if r.validation_status == "valid")
    return Summary(
        total_records=len(records),
        valid_count=valid,
        invalid_count=len(records) - valid,
    )


def process_batch(
    source: str | os.PathLike[str],
    template: str | None = None,
) -> BatchResult:
    """Parse a partner batch file and render its report.

    Args:
        source: Either the CSV contents as a ``str`` or a path-like object
            (e.g. :class:`pathlib.Path`) pointing at a UTF-8, comma-delimited
            CSV file with a header row and a ``region`` column.
        template: Optional mustache template with scalar placeholders (e.g.
            ``{{total_records}}``). When omitted, :data:`DEFAULT_TEMPLATE` is
            used. No sections are supported in this slice.

    Returns:
        The parsed records, summary stats, and rendered report.
    """

    if isinstance(source, os.PathLike):
        contents = Path(source).read_text(encoding="utf-8")
    else:
        contents = source

    records = _read_csv(contents)
    summary = _summarize(records)
    report = chevron.render(
        template=template if template is not None else DEFAULT_TEMPLATE,
        data={
            "total_records": summary.total_records,
            "valid_count": summary.valid_count,
            "invalid_count": summary.invalid_count,
        },
    )
    return BatchResult(records=records, summary=summary, report=report)
