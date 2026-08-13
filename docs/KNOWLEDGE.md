# Knowledge

Institutional memory for AI agents. Append-only. Each entry tagged by topic.

## Bar for entry

An entry belongs here if a fresh agent would make a different decision or avoid a mistake if it knew this.

## Topics

### Tooling

- **2026-08-13** — No `pyproject.toml`, `requirements.txt`, or test config exists yet. The `practices/coding-practice.md` doc mandates `black`, `isort`/`ruff`, `mypy`/`pyright`, and a test framework, but none are installed or configured. A fresh agent should not assume `pytest` / `mypy` / `black` commands will run — set up the project manifest first when a ticket calls for running them.

### Layout

- **2026-08-13** — `practices/` holds engineering **standards** (read on demand by `/code-review`, `/jk-implement`, `/jk-security`), not domain or product docs. Don't treat `practices/coding-practice.md` as a description of what this repo currently does — it's the rules code should follow, mostly defaults. Domain docs live at `CONTEXT.md` + `docs/adr/` per `docs/agents/domain.md`.

- **2026-08-13** — The three `src/*` packages are independent stubs with no cross-imports. A ticket touching one package does not need to consider the others.
