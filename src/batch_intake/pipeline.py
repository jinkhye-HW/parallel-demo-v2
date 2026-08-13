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
# namespaced under `extra` (see ADR 0001).
SCHEMA_FIELDS: tuple[str, ...] = (
    "customer_id",
    "region",
    "email",
    "phone",
    "notes",
)

# Pipeline-owned field names. A partner column colliding with one of these is
# quarantined into `extra` under a `<name>__conflict` key so the CSV cannot
# overwrite the pipeline's computed verdict (ADR 0001, security-critical).
RESERVED_FIELDS: tuple[str, ...] = ("validation_status", "errors", "extra")

# A file with more than this many columns surfaces a file-level parse error.
MAX_COLUMNS = 64


class BatchParseError(Exception):
    """File-level parse error surfaced to the caller.

    Distinct from a record-level ``invalid`` validation status: the file
    itself could not be parsed (e.g. it exceeds the column cap), so no
    records are produced. Raised from :func:`process_batch` for the caller
    to catch.
    """


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

    If ``source`` points at an existing file, read it as UTF-8 text (BOM-tolerant
    via ``utf-8-sig``); on a :class:`UnicodeDecodeError` fall back to decoding
    with ``errors="replace"`` so a mixed-encoding partner file never raises at
    the I/O boundary. Otherwise treat ``source`` as raw CSV contents. This keeps
    the public entry point a single function that accepts a path or contents,
    per the ticket.
    """
    candidate = Path(os.fspath(source))
    if candidate.is_file():
        data = candidate.read_bytes()
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError:
            return data.decode("utf-8-sig", errors="replace")
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


def _validate_record(values: dict[str, str], extra: dict[str, str]) -> Record:
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
        extra=extra,
    )


def _partition_row(
    row: dict[str, str | None],
) -> tuple[dict[str, str], dict[str, str]]:
    """Split a CSV row into schema values and the ``extra`` dict.

    Schema fields go into the values dict. Reserved field names
    (``validation_status``, ``errors``, ``extra``) are quarantined into
    ``extra`` under ``<name>__conflict`` keys so a partner CSV cannot
    overwrite the pipeline's computed fields (ADR 0001). Any other unknown
    column is namespaced into ``extra`` under its own name. Unknown columns
    are never flat-merged onto the record.
    """
    values: dict[str, str] = {}
    extra: dict[str, str] = {}
    for name, raw in row.items():
        if name is None:
            # DictReader yields a None key for surplus columns in rows that
            # have more fields than the header; there is no column name to
            # namespace under, so skip the surplus value.
            continue
        value = raw or ""
        if name in SCHEMA_FIELDS:
            values[name] = value
        elif name in RESERVED_FIELDS:
            extra[f"{name}__conflict"] = value
        else:
            extra[name] = value
    # Ensure every schema field is present even if missing from the header.
    for name in SCHEMA_FIELDS:
        values.setdefault(name, "")
    return values, extra


# Delimiters the sniffer may choose between. Restricted so a stray character in
# the data is not mistaken for a delimiter; comma is the default.
_CANDIDATE_DELIMITERS = ",\t;|"


def _detect_delimiter(contents: str) -> str:
    """Auto-detect the CSV delimiter, defaulting to comma when uncertain.

    Uses :class:`csv.Sniffer` on a leading sample. If the sample is too short
    or the sniffer cannot determine a delimiter, comma is returned so a
    well-formed comma file still parses.
    """
    sample = contents[:2048]
    if not sample:
        return ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=_CANDIDATE_DELIMITERS)
    except csv.Error:
        return ","
    return dialect.delimiter


def _looks_like_data_value(value: str) -> bool:
    """Heuristic: does ``value`` look like record data, not a column name?

    Column names are identifiers; record data carries an email (``@``), a phone
    (leading ``+``), or a purely-numeric id. Used to detect a headerless file
    whose first row :class:`csv.DictReader` would otherwise treat as the header.
    """
    if "@" in value:
        return True
    if value.startswith("+"):
        return True
    if value and all("0" <= ch <= "9" for ch in value):
        return True
    return False


def _is_headerless(fieldnames: list[str]) -> bool:
    """Return True if the header row looks like a data row (no header).

    A real partner header carries at least one known schema column name. If none
    of the fieldnames match the schema and at least one looks like a data value
    (email, phone, numeric id), the file is headerless and would be silently
    positionally mis-parsed by :class:`csv.DictReader`.
    """
    if any(name in SCHEMA_FIELDS for name in fieldnames):
        return False
    return any(_looks_like_data_value(name) for name in fieldnames)


def _is_section_grouped(contents: str) -> bool:
    """Return True if ``contents`` is a section-grouped CSV.

    A section-grouped file's first non-blank line is a bare region label (a
    single field with no delimiter) and the following line is a CSV header (it
    contains a delimiter). A normal CSV's first line is the header itself, which
    contains a delimiter.
    """
    lines = [ln for ln in contents.splitlines() if ln.strip()]
    if len(lines) < 2:
        return False
    first_has_delim = any(d in lines[0] for d in _CANDIDATE_DELIMITERS)
    second_has_delim = any(d in lines[1] for d in _CANDIDATE_DELIMITERS)
    return not first_has_delim and second_has_delim


def _split_sections(contents: str) -> list[list[str]]:
    """Split section-grouped contents into sections of non-blank lines.

    Sections are separated by one or more blank lines. Within a section, the
    first line is the region label and the rest is a CSV with its own header.
    """
    sections: list[list[str]] = []
    current: list[str] = []
    for line in contents.splitlines():
        if line.strip():
            current.append(line)
        else:
            if current:
                sections.append(current)
                current = []
    if current:
        sections.append(current)
    return sections


def _read_rows(csv_text: str) -> list[dict[str, str | None]]:
    """Read ``csv_text`` with an auto-detected delimiter.

    Returns the rows. Raises :class:`BatchParseError` if the file is headerless
    or exceeds the column cap.
    """
    delimiter = _detect_delimiter(csv_text)
    reader = csv.DictReader(StringIO(csv_text), delimiter=delimiter)
    fieldnames = reader.fieldnames
    if fieldnames is None:
        return []
    fieldnames_list = list(fieldnames)
    if _is_headerless(fieldnames_list):
        raise BatchParseError(
            "headerless file: first row has no recognized column names"
        )
    if len(fieldnames_list) > MAX_COLUMNS:
        raise BatchParseError(
            f"file has {len(fieldnames_list)} columns; cap is {MAX_COLUMNS}"
        )
    return list(reader)


def _parse_records(contents: str) -> list[Record]:
    if _is_section_grouped(contents):
        return _parse_section_grouped(contents)
    return _parse_flat(contents)


def _parse_flat(contents: str) -> list[Record]:
    records: list[Record] = []
    for row in _read_rows(contents):
        values, extra = _partition_row(row)
        records.append(_validate_record(values, extra))
    return records


def _parse_section_grouped(contents: str) -> list[Record]:
    """Parse a section-grouped CSV into a flat record list with ``region``.

    Each section is a region label line followed by a CSV with its own header.
    The label is preserved as the ``region`` field on every record in that
    section, overriding any ``region`` column in the section's header (the
    grouping is the source of truth for region).
    """
    records: list[Record] = []
    for section in _split_sections(contents):
        if len(section) < 2:
            # A label with no header/data yields no records.
            continue
        region = section[0].strip()
        csv_text = "\n".join(section[1:])
        for row in _read_rows(csv_text):
            values, extra = _partition_row(row)
            values["region"] = region
            records.append(_validate_record(values, extra))
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
