# Coding practice (Python)

Python engineering standards. `/code-review`'s Standards axis reads this file; `/jk-implement` writes against it. Where a project's own conventions conflict with a rule here, the project wins — this file is the default, not an override.

## Style and structure

### PEP 8, enforced by a tool, not by eye

Formatting is `black`'s job and import order is `isort`'s (or `ruff` doing both). A human reviewer's attention is too expensive to spend on where a comma goes — spend it on logic. If a project has no formatter configured, that's a finding before the first PR lands, not a style preference to raise later.

### Type hints on every public function

`def parse(raw: str) -> Config:`, not `def parse(raw):`. Hints are the fastest way for a caller — human or agent — to know a function's contract without reading its body, and they let `mypy` or `pyright` catch a whole class of bugs before a test does. Use `from __future__ import annotations` (or target 3.10+) so hints don't cost anything at import time.

Prefer precise types over `Any`: `list[int]` over `list`, `Literal["asc", "desc"]` over `str` when only two values are ever valid. `Any` at a boundary defeats the type checker for everyone downstream of that call.

### Iterables: accept broad, return concrete

A function that only reads its input once should accept `Iterable[T]`; a function that needs length, random access, or multiple passes should say `Sequence[T]` or take a `list[T]` and materialize immediately:

```python
def process(values: Iterable[int]) -> list[int]:
    materialized = list(values)
    ...
```

Never leave a generator half-consumed by accident — a function that iterates its input twice without materializing first will silently see an empty sequence the second time. And never return a generator from a function documented to return a collection; the caller expects to iterate it more than once.

### Dataclasses over dict-shaped data

A dict passed around as `{"name": ..., "age": ...}` has no schema a type checker or IDE can verify. Once a piece of data has more than one caller, give it a `@dataclass` (or `TypedDict` at a genuine JSON boundary, or `pydantic` where validation is needed). The dataclass is free documentation of the shape, and it turns a typo'd key into an `AttributeError` at the call site instead of a silent `None` at runtime.

### Context managers for anything with a lifecycle

A file handle, a lock, a database connection, a temp directory — anything with an open/close or acquire/release pairing goes in a `with` block, never a manual `.close()` a reviewer has to trust runs on every code path including exceptions. Write a project's own `__enter__`/`__exit__` or `@contextmanager` for any resource that recurs across the codebase rather than repeating the try/finally.

## Errors and failure

### Catch the narrowest exception the code can actually raise

`except Exception:` around a whole function body means a `KeyboardInterrupt`-adjacent bug two calls deep gets silently absorbed along with the one failure you meant to handle. Catch the specific exception type, around the specific expression that raises it:

```python
try:
    value = registry[key]
except KeyError:
    value = default
```

### Raise specific, built-in-compatible exception types

`TypeError` for a wrong argument type, `ValueError` for a right type with a bad value, `KeyError`/`IndexError` for missing lookups — reuse the stdlib vocabulary a caller already knows how to catch, rather than inventing a project-specific exception for something a built-in type already covers. Reserve custom exceptions for domain-specific failures a caller genuinely needs to distinguish (`InsufficientFundsError`, not `MyAppError`).

### Never bare `except:`

A bare `except:` (no type) catches `SystemExit` and `KeyboardInterrupt` along with everything else, meaning `Ctrl-C` can get swallowed by a handler meant for network errors. Use `except Exception:` at minimum, and only that broad when the code truly must handle every possible failure the same way — logging at a boundary, for example.

### `isinstance(x, bool)` before `isinstance(x, int)`

`bool` subclasses `int` in Python, so `isinstance(True, int)` is `True` and `True + True == 2`. A function that means to accept integers and silently accepts booleans will do the wrong thing on a caller's typo (`is_valid=True` where an id was expected). Guard explicitly wherever a boolean sneaking through would be a bug: `if not isinstance(n, int) or isinstance(n, bool): raise TypeError(...)`.

### Mutable default arguments are a bug, not a style choice

```python
def add_item(item, items=[]):   # the same list, reused across every call with no items given
```

The default is created once, at function definition time, and shared across every call that doesn't override it. Use `None` and create the mutable value inside the function body instead.

## Testing

### `pytest`, not `unittest`, for new code

Plain `assert` statements, fixtures over `setUp`/`tearDown`, `pytest.raises` over `assertRaises` — less ceremony, and fixtures compose in a way `unittest`'s class hierarchy doesn't. Adopting `unittest` conventions in a `pytest`-based project (or vice versa) is friction for no benefit; match what the project already runs.

### One seam: the public function or endpoint

Tests import from the package's public surface (`from mypackage import parse`), never from a name prefixed `_`. A test reaching into a private helper breaks the moment that helper is renamed during a refactor that changed nothing externally — that's a false failure, and it teaches the team to distrust red tests.

### Parametrize instead of copy-pasting test bodies

```python
@pytest.mark.parametrize("value,expected", [(0, False), (1, False), (2, True), (17, True)])
def test_is_prime(value, expected):
    assert is_prime(value) == expected
```

Five near-identical test functions differing only in their literals is a maintenance trap — a bug in the shared assertion logic has to be fixed five times. `parametrize` keeps the assertion in one place and the cases in a table.

### Fixtures for setup, not copy-pasted boilerplate

If three tests each build the same `Client` or seed the same test data, that's a fixture, not three copies. A fixture also makes teardown explicit and automatic (`yield` then cleanup), instead of relying on every test author to remember it.

### Mock at the boundary, not the internals

Patch the HTTP client, the database driver, the filesystem call — the actual edge of the system under test — not an internal function three layers deep. Mocking deep internals couples the test to the current implementation, and it stops testing anything real about how the pieces fit together.

## Packaging and environment

### `pyproject.toml` as the single source of project metadata

Dependencies, build system, and tool configuration (`black`, `ruff`, `mypy`, `pytest`) all live in `pyproject.toml`. A project splitting config across `setup.py`, `setup.cfg`, `requirements.txt`, and a `pytest.ini` scattered at the root has four places to update instead of one, and they drift.

### Pin runtime dependencies, pin dev tooling looser

Runtime dependencies get pinned (via a lockfile — `uv.lock`, `poetry.lock`, or a hash-pinned `requirements.txt`) so the code that runs in production is the code that was tested. Dev tooling (`black`, `ruff`) can float on a compatible range since it never ships.

### A virtual environment per project, never a global install

`pip install` outside a venv (or without `uv`/`poetry`/`pipenv` managing one) pollutes the system interpreter and makes "works on my machine" the default outcome. This is the first thing to check when a project has no `venv`/`.venv` and no lockfile — it's not a style nit, it's why the bug report doesn't reproduce.

### `src/` layout for anything published

Package code under `src/<package>/`, tests under `tests/`, nothing importable sitting loose at the repo root. The `src/` layout forces tests to run against the *installed* package rather than accidentally importing the working directory, which is the difference between a test suite that catches a packaging bug and one that can't.

## Documentation

### Google or NumPy docstring style, pick one per project and hold the line

```python
def chunk(items: Iterable[T], size: int) -> list[list[T]]:
    """Split items into fixed-size batches.

    Args:
        items: The iterable to split.
        size: Maximum length of each batch. Must be positive.

    Returns:
        A list of batches; the last may be shorter than size.

    Raises:
        ValueError: If size is not a positive integer.
    """
```

Every exception a function can raise on its own belongs under `Raises:` — that's the one piece of the contract a type checker can't verify and a reader can't get from the signature.

### A README that states what the project is, how to install it, and how to run it

Three sections, minimum: what this is and who it's for, how to install it, how to run it and its tests. A public entry point added or changed in a way a user would notice belongs here — a caller who has to read `src/` to learn the entry point's name is reading the wrong file. Internal design rationale stays out; that's `docs/ARCHITECTURE.md`.

### Docstrings on the public surface, comments for the non-obvious internal step

A docstring documents *what a caller can rely on*. A comment inside the body earns its place only by explaining *why* a non-obvious line exists — a workaround, a constraint from outside the function, a deliberate deviation from the obvious approach. A comment that restates the line below it in English is a no-op; delete it.

---

**Applying this file:** a review that has read it names the specific rule a change violates, or names none. "Not Pythonic" is not a finding — a rule from this list, with the line it applies to, is.
