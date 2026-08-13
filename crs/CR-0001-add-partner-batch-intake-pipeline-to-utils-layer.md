---
id: CR-0001
title: Add partner batch intake pipeline to utils layer
requester:
  name: Priya Nandakumar
  role: Partner Integrations Lead
submitted_at: 2026-08-13
type: feature
affected_systems: []
status: intake
---

## Original Request

> We're onboarding a new partner who'll send us daily batch files of customer records (CSV-ish text, sometimes nested/grouped by region). We need our utils layer to be able to: parse and validate the fields (emails, phone numbers, free-text notes), flatten their nested region groupings into one big list, compute some summary stats across the batch (totals, an ID checksum/validity check), and spit out a rendered summary report where ops can plug in their own report template with placeholders for the fields. Also we want to cache the parsed batch to disk so re-running the report for the same file is instant instead of re-parsing every time. Would like this to work with whatever weird formatting partners throw at us without crashing. Requester: Priya Nandakumar, Partner Integrations Lead.

## Description

Add a partner batch intake pipeline to the utils layer (`src/`) that can:

1. Parse and validate customer-record fields from daily partner batch files — CSV-ish text, sometimes nested/grouped by region. Fields include emails, phone numbers, and free-text notes.
2. Flatten nested region groupings into a single flat list of records.
3. Compute summary stats across the batch — totals and an ID checksum/validity check.
4. Render a summary report from a user-supplied template with placeholders for the fields (ops plugs in their own template).
5. Cache the parsed batch to disk so re-running the report for the same file is instant instead of re-parsing every time.

Must tolerate "whatever weird formatting partners throw at us" without crashing.

## Business Justification

A new partner is being onboarded who will send daily batch files of customer records. Ops needs to turn these into validated, summarized reports without re-parsing on every re-run, and without the pipeline crashing on partner formatting variations.

## Intake Notes

- No system named beyond "our utils layer" — colloquial mention maps to `src/` (`list_utils`, `math_utils`, `string_utils`). `affected_systems` left empty per no canonical system name.
- Request bundles five capabilities (parse/validate, flatten, summary stats, report rendering, disk cache); requester chose to capture as one CR. Downstream spec may still split into multiple tickets.
- "CSV-ish text" and "weird formatting" are intentionally loose in the request — tolerance to format variation is an explicit requirement, not an oversight.
