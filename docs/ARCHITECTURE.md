# Architecture

A Python utility library, currently a skeleton: three packages with no implementations yet.

## Tech stack

- **Language:** Python (no version pinned — no `pyproject.toml` / `setup.py` / `requirements.txt` present)
- **Build tools:** none
- **Frameworks:** none
- **Databases:** none

## Entry points

None. This is a library, not an application. Consumers would import from `src.<module>`.

## Logical structure

Three independent utility modules, physically separated as sibling packages under `src/`:

| Module | Path | Status |
| --- | --- | --- |
| `math_utils` | `src/math_utils/__init__.py` | stub — docstring only, no functions |
| `string_utils` | `src/string_utils/__init__.py` | stub — docstring only, no functions |
| `list_utils` | `src/list_utils/__init__.py` | stub — docstring only, no functions |

No shared code, no cross-module dependencies. The three modules are parallel peers.

## Key directories

- `src/` — all source code, one subdirectory per utility module
- `docs/agents/` — per-repo agent skill configuration (issue tracker, triage labels, domain docs)

## File size hotspots

None. Largest source files are 1 line each.

## Test presence

None. No test framework, no test files, no CI config.

## KNOWLEDGE links

No `docs/KNOWLEDGE.md` entries yet — the repo has no non-obvious behavior to record at this stage.
