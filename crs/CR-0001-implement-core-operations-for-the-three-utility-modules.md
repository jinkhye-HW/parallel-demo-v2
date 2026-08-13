---
id: CR-0001
title: Implement core operations for the three utility modules
requester:
  name: jinkhye-HW
  role: maintainer
submitted_at: 2026-08-13
type: feature
affected_systems:
  - math_utils
  - string_utils
  - list_utils
status: intake
---

## Original Request

> CR: Implement core operations for the three utility modules
>
> We need working implementations in math_utils, string_utils, and list_utils — right now they're empty stubs. Ship a first useful slice of each:
>
> math_utils
> - gcd(a, b) and lcm(a, b)
> - is_prime(n)
> - mean(values) and median(values)
>
> string_utils
> - slugify(text) — turn arbitrary text into a URL-safe slug
> - truncate(text, length) — shorten with an ellipsis if too long
> - is_palindrome(text)
>
> list_utils
> - chunk(items, size) — split a list into fixed-size batches
> - flatten(nested) — flatten arbitrary nesting
> - dedupe(items) — remove duplicates, order-preserving
>
> Ship it as normal library functions, fully tested. Use your judgment on edge cases (empty inputs, negatives, unicode, uneven chunk sizes, etc.) — just be consistent within each module.

## Description

Implement a first useful slice of functions across the three utility modules:

- **math_utils**: `gcd(a, b)`, `lcm(a, b)`, `is_prime(n)`, `mean(values)`, `median(values)`
- **string_utils**: `slugify(text)`, `truncate(text, length)`, `is_palindrome(text)`
- **list_utils**: `chunk(items, size)`, `flatten(nested)`, `dedupe(items)`

All as normal library functions, fully tested. Edge cases (empty inputs, negatives, unicode, uneven chunk sizes, etc.) handled consistently within each module.

## Business Justification

The three utility modules are currently empty stubs. Working implementations are needed before the library can be consumed.

## Intake Notes

Affected systems as named by the requester: the three modules under `src/`. Requester identity taken from the repo git user. Type `feature` — new function implementations, not a fix to existing behavior.
