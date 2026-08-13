# Context

Domain glossary. Only terms non-obvious from the code are listed; refined by `/domain-modeling` as terms get resolved.

- **Batch** — a daily file of customer records received from a partner.
- **Record** — one customer entry parsed from a row of a batch. Carries a `validation_status` (`valid` / `invalid`) and an `errors` list; invalid records are retained, not dropped. Schema fields (`customer_id`, `region`, `email`, `phone`, `notes`) map to canonical names; unknown partner columns are namespaced under `extra: dict[str, str]`, never flat-merged onto the record.
- **Reserved field** — a field the pipeline owns (`validation_status`, `errors`, `extra`). A partner column colliding with a reserved name is quarantined into `extra` under a conflict-marked key rather than overwriting the pipeline's computed value — the CSV cannot spoof its own validity verdict.
- **Region grouping** — the partner's grouping of records by region (a region column or section-grouped blocks). Flattening removes the grouping but preserves the `region` as a field on each record.
- **Validation status** — per-record flag set by field validation: `valid` or `invalid`, with specifics in the `errors` list.
- **Parsed-batch cache** — the parsed batch written to disk keyed by SHA-256 of the input file's contents, so a re-run on an unchanged file skips parsing. Cache directory is derived from the input file's path, never from a partner-supplied string.
- **Report template** — an ops-supplied text template with `{{field}}` placeholders that the renderer substitutes with record/summary values. The template determines the output format.
