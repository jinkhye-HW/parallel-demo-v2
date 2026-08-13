# Knowledge

Institutional memory for AI agents. Append-only. Each entry tagged by topic.

## Bar for entry

An entry belongs here if a fresh agent would make a different decision or avoid a mistake if it knew this.

## Topics

### Build & packaging

- **2026-08-13** — No `pyproject.toml`, `setup.py`, or `requirements.txt` exists. The packages under `src/` are not installable as-is. An agent adding dependencies or packaging should create the manifest rather than assuming one exists.
