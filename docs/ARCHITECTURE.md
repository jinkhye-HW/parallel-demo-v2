# Architecture

A Python utility library, currently a **seed/skeleton** — three packages staged under `src/` with no implementation yet.

## Tech stack

- **Language:** Python (no version pinned yet — no `pyproject.toml` / `requirements.txt` present)
- **Build tool:** none configured
- **Test framework:** none present
- **CI:** none

## Entry points

None. This is a library, not an application. Once functions are added, consumers import from `src/<package>`.

## Logical structure

Three independent utility packages, one per concern. They are physically separated already (one directory each) and have no cross-dependencies:

- **`list_utils`** — list-manipulation functions (empty)
- **`math_utils`** — math helper functions (empty)
- **`string_utils`** — string-processing functions (empty)

Each `src/*/__init__.py` currently holds only a module docstring. No functions, classes, or tests yet.

## Key directories

- `src/` — source packages (one dir per utility domain)
- `practices/` — engineering standards (coding & security), referenced by `AGENTS.md`
- `docs/agents/` — per-repo agent skill configuration (issue tracker, labels, domain layout)

## File size hotspots

None — largest files are the standards docs in `practices/` (~9–11 KB), not source code.

## KNOWLEDGE links

- Tooling gap (no manifest/tests yet) → see `docs/KNOWLEDGE.md` § Tooling
- Standards docs location → see `docs/KNOWLEDGE.md` § Layout
