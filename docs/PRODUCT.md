# Product

## What

A small Python utility library collecting reusable helpers for lists, math, and strings. Currently a skeleton — the three packages exist but contain no functions yet.

## Who

Developers in this repo pulling common helpers off the shelf instead of re-implementing them per ticket. No end users; this is an internal library.

## Why

Centralize the boring, repeated bits (chunking, formatting, numeric helpers) so feature code stays short and the helpers get one tested home rather than N ad-hoc copies.

## Key domain concepts

- **List utils** — operations on lists/iterables (chunk, flatten, dedupe, …)
- **Math utils** — numeric helpers (clamp, safe division, rounding, …)
- **String utils** — text processing (normalize, truncate, slugify, …)

See `CONTEXT.md` for definitions as terms get nailed down.
