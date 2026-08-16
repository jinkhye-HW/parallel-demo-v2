"""Mustache sections and HTML escaping through the public entry point.

Covers ticket #13 (T6): ``{{#records}}`` / ``{{#per_region}}`` loops,
conditional sections, and ``{{field}}`` (escaped) vs ``{{{field}}}`` (raw).
"""

from __future__ import annotations

from pathlib import Path

from batch_intake import process_batch

FIXTURES = Path(__file__).parent / "fixtures"


def test_records_section_renders_one_block_per_record() -> None:
    template = (
        "{{#records}}"
        "{{customer_id}}|{{region}}|{{email}}|{{phone}}|{{notes}}|"
        "{{validation_status}};"
        "{{/records}}"
    )
    result = process_batch(FIXTURES / "valid_batch.csv", template=template)

    # Three records, one block each, fields substituted.
    blocks = result.report.split(";")
    assert len(blocks) == 4  # three blocks plus a trailing empty from the final ';'
    assert blocks[0] == "1001|EMEA|alice@example.com|442079460958|prefers email|valid"
    assert blocks[1] == "1002|APAC|bob@example.com|6561234567|vip|valid"
    assert blocks[2] == "1003|AMER|carol@example.com|14155550142||valid"
    assert blocks[3] == ""


def test_records_section_exposes_errors_and_extra() -> None:
    # extra_columns.csv has unknown columns loyalty_tier / signup_source -> extra.
    # A record with no errors renders an empty errors section; extra is reachable
    # as a section context.
    template = (
        "{{#records}}"
        "{{customer_id}}:"
        "{{#errors}}ERR={{.}},{{/errors}}"
        "{{#extra}}{{loyalty_tier}}/{{signup_source}}{{/extra}};"
        "{{/records}}"
    )
    result = process_batch(FIXTURES / "extra_columns.csv", template=template)

    assert result.report == "1001:gold/web;"


def test_per_region_section_renders_one_block_per_region() -> None:
    template = (
        "{{#per_region}}{{name}}:{{records}}/{{valid}}/{{invalid}};{{/per_region}}"
    )
    result = process_batch(FIXTURES / "checksum_multi_region.csv", template=template)

    # EMEA: 2 records, 1 valid (bad email), 1 invalid.
    # APAC: 2 records, both valid.
    # AMER: 1 record, valid.
    assert result.report == "EMEA:2/1/1;APAC:2/2/0;AMER:1/1/0;"


def test_conditional_section_renders_only_when_truthy() -> None:
    # mixed_validation.csv: row 1 bad email -> invalid, row 2 phone "+12" (2
    # digits) -> invalid, row 3 valid. {{#invalid}} renders only invalid records.
    template = "{{#records}}{{#invalid}}{{customer_id}},{{/invalid}}{{/records}}"
    result = process_batch(FIXTURES / "mixed_validation.csv", template=template)

    assert result.report == "4001,4002,"


def test_conditional_section_skips_when_falsy() -> None:
    # The same fixture's single valid record (4003) is selected by {{#valid}}.
    template = "{{#records}}{{#valid}}{{customer_id}},{{/valid}}{{/records}}"
    result = process_batch(FIXTURES / "mixed_validation.csv", template=template)

    assert result.report == "4003,"


def test_double_brace_html_escapes_and_triple_brace_outputs_raw() -> None:
    template = "{{#records}}{{notes}}|{{{notes}}};{{/records}}"
    result = process_batch(FIXTURES / "notes_with_html.csv", template=template)

    # First record's notes carry HTML metacharacters; {{notes}} escapes them,
    # {{{notes}}} outputs them verbatim. The second record is plain text.
    assert result.report == (
        '&lt;b&gt;bold &amp; &quot;quoted&quot;&lt;/b&gt;|<b>bold & "quoted"</b>;'
        "plain|plain;"
    )


def test_end_to_end_section_and_escaping_template() -> None:
    # A single template exercising records + per_region + conditionals + escaping.
    template = (
        "Records:\n"
        "{{#records}}  - {{customer_id}} [{{validation_status}}]"
        "{{#invalid}} ERR{{/invalid}}: {{email}}\n"
        "{{/records}}"
        "By region:\n"
        "{{#per_region}}  {{name}}={{records}}\n{{/per_region}}"
    )
    result = process_batch(FIXTURES / "mixed_validation.csv", template=template)

    assert "Records:\n" in result.report
    assert "  - 4001 [invalid] ERR: bad-email\n" in result.report
    assert "  - 4002 [invalid] ERR: ok@example.com\n" in result.report
    assert "  - 4003 [valid]: ok2@example.com\n" in result.report
    assert "By region:\n" in result.report
    assert "  EMEA=1\n" in result.report
    assert "  APAC=1\n" in result.report
    assert "  AMER=1\n" in result.report
