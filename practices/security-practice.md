# Security practice (Python)

Python-specific security standards. `/code-review` and `/security-review` read this file; `/jk-implement` reads it when a ticket touches I/O, deserialization, subprocesses, or credentials.

## Injection

### SQL: parameterize, never format

```python
# Wrong — the value is part of the query text
cur.execute(f"SELECT * FROM users WHERE email = '{email}'")

# Right — the driver treats the value as data, never as SQL
cur.execute("SELECT * FROM users WHERE email = %s", (email,))
```

Every DB-API driver (`psycopg`, `sqlite3`, `pymysql`) supports parameterized queries. An f-string or `.format()` building SQL from a variable is the injection, full stop — it doesn't matter how the value was validated upstream, because the fix belongs at the query boundary, not the input boundary. An ORM (`SQLAlchemy`, `Django ORM`) sidesteps this by construction, but `.raw()` / `text()` escape hatches reintroduce the same risk and need the same parameterization.

### Shell commands: `subprocess` with a list, `shell=False`

```python
# Wrong — os.system and shell=True hand the string to /bin/sh
subprocess.run(f"convert {filename} out.png", shell=True)

# Right — args passed as a list never reach a shell
subprocess.run(["convert", filename, "out.png"], shell=False)
```

`shell=True` (the default for `os.system`, `os.popen`) means any shell metacharacter in an argument — backticks, `;`, `$()`, `|` — executes. Pass a list of arguments instead; the OS execs the binary directly and no shell ever parses the string. If `shell=True` is genuinely unavoidable, every interpolated value must go through `shlex.quote()`, and that should be rare enough to be a review flag on its own.

### Deserialization: never `pickle.load` on untrusted bytes

`pickle` can execute arbitrary code during deserialization — a crafted payload's `__reduce__` runs on `load()`, before any application code sees the "data." Never unpickle a value that crossed a trust boundary (a network request, a file a user uploaded, a queue message from outside the system). Use `json` for data interchange; if binary serialization is required, use a format with no code-execution primitive (`protobuf`, `msgpack`).

`yaml.load()` has the same shape of problem — it can instantiate arbitrary Python objects by default. Use `yaml.safe_load()` unconditionally; there is no case where the unsafe loader is the right default.

### `eval` / `exec` on any input that touched the outside world

Both execute arbitrary Python. `ast.literal_eval` is the safe substitute when the goal is parsing a literal (a list, dict, or number) out of a string — it evaluates only literal syntax, nothing callable. If a project's design seems to require `eval` on user input, that design is the problem to escalate, not the `eval` call to patch around.

## Secrets

### No literal secrets in source, ever — not even in tests

A credential committed once is compromised permanently, because git history keeps it even after a later commit removes it. Load secrets from environment variables (`os.environ`) or a secrets manager (Vault, AWS Secrets Manager, GCP Secret Manager); use `.env` files for local dev only, and `.env` belongs in `.gitignore` from the first commit, not added after something leaks. Test fixtures use obviously-fake values (`"test-key-not-real"`), never a redacted-looking real one.

### Secrets never reach logs or exception messages

```python
logger.info(f"Authenticating with token {token}")   # the token is now in every log sink
```

A logged secret reaches every downstream consumer of that log — aggregators, error trackers, sometimes a dashboard visible to more people than the code's author expected. Log that authentication happened, and the account or key *identifier* if needed for correlation — never the credential value itself. The same applies to exception messages: an exception carrying a raw request body or header dict can carry a bearer token straight into an error tracker.

### Constant-time comparison for anything security-sensitive

```python
import hmac
hmac.compare_digest(provided_signature, expected_signature)   # not: provided == expected
```

Python's `==` on strings short-circuits at the first differing byte, so its timing leaks how many leading bytes were correct — enough signal for a timing attack against an API key, an HMAC signature, or a password (though passwords should be going through a hashing library's own `verify`, not a direct comparison at all, per below).

### Passwords: a slow, salted hash — never a fast one, never reversible

Use `bcrypt`, `argon2` (via `argon2-cffi`), or `passlib` — never `hashlib.md5`/`sha256` directly, and never symmetric encryption you can decrypt back to the plaintext. A fast general-purpose hash is exactly what makes offline brute-forcing a leaked hash database cheap; a deliberately slow KDF is what makes it expensive.

## Input handling

### Every argument crossing a trust boundary is validated at the boundary

A request handler, a CLI entry point, a public library function reading a file path or a URL from a caller — each of these is a place untrusted data enters, and each should validate type, range, and shape before passing the value deeper into the system. Internal functions past that point trust their inputs; re-validating the same invariant at every layer just hides which layer is actually responsible.

### Path traversal: resolve and check containment, don't just strip `..`

```python
base = Path("/var/app/uploads").resolve()
target = (base / user_supplied_name).resolve()
if not target.is_relative_to(base):
    raise ValueError("path escapes upload directory")
```

Stripping literal `../` substrings is not sufficient — encoded variants, symlinks, and absolute paths (`/etc/passwd` handed to a naive `os.path.join`) all bypass a string-level filter. Resolve to an absolute path and check containment against the intended root before any file operation.

### SSRF: a URL taken from a request is not automatically safe to fetch

Any code path where a user-supplied URL is passed to `requests.get()` or similar server-side is a candidate for reaching internal-only services (a metadata endpoint, an admin panel on localhost, another host on the internal network) — the request comes from inside the trust boundary, so internal firewall rules don't apply to it. Validate the resolved host against an allowlist before fetching, and disable redirect-following or re-validate the destination after every redirect hop.

### `re` against untrusted input: keep patterns linear

A pattern with nested or overlapping quantifiers (`(a+)+`, `(a|a)*`, `(.*)+`) can backtrack exponentially on a crafted string, tying up a worker thread on a single request — this is ReDoS, and it needs no special payload, just an unlucky-shaped one. Avoid nested quantifiers in any pattern applied to caller-controlled text; if a pattern's complexity is unavoidable, cap the input length before it reaches the regex, or use a bounded matcher (`re2`-backed libraries don't backtrack).

## Cost and availability

### State the algorithmic cost of anything that touches unbounded input

A function whose runtime scales with the *value* of an argument rather than its *size* — trial division on a large integer, unbounded recursion on nested input, a quadratic fallback path triggered by a particular input shape — is a denial-of-service vector the moment that argument can come from outside the system. Document the cost; bound the input at the boundary if arbitrary values aren't acceptable.

### Recursion on caller-controlled depth needs an explicit limit

Python's default recursion limit (1000) is a blunt backstop, not a designed one — it raises `RecursionError` at an arbitrary depth that has nothing to do with what the caller can safely handle, and raising the limit with `sys.setrecursionlimit` just moves the crash, it doesn't remove it. A function that recurses once per level of caller-controlled nesting (parsing nested JSON, walking a user-supplied tree) should convert to an iterative approach with an explicit, chosen depth cap, or reject input past a documented depth before recursing into it.

## Dependencies and supply chain

### Every dependency executes with the process's full permissions

A library import runs with the same filesystem, network, and environment access as the rest of the process — there is no sandbox by default. Prefer the standard library or a small first-party function over a dependency for anything trivial. When a dependency is warranted, check its maintenance status and download counts as a rough signal, and prefer one with a narrow, auditable scope over one that pulls in a large transitive tree for a small piece of functionality.

### Run a vulnerability scanner in CI

`pip-audit` or `safety` against the resolved dependency set, on every PR and on a schedule (dependencies can gain a CVE after they're already merged). A project with no dependency scanning is running unknown, unaudited vulnerability exposure — this is worth flagging as a gap the first time it's noticed, not deferring.

### Pin with hashes for anything deployed

A version pin (`requests==2.31.0`) still trusts the index to serve the same bytes for that version next time; a hash pin (`requests==2.31.0 --hash=sha256:...`, or a `poetry.lock`/`uv.lock` which do this by default) verifies the exact artifact. This is what stops a compromised or yanked-and-replaced package version from silently changing what gets installed.

## Cryptography

### Use `secrets`, never `random`, for anything security-relevant

```python
import secrets
token = secrets.token_urlsafe(32)   # cryptographically secure
```

The `random` module is a Mersenne Twister — deterministic and predictable from enough output, not suitable for tokens, password reset codes, or session IDs. `secrets` is the stdlib's CSPRNG-backed module specifically for this; reach for it by default any time the value needs to be unguessable.

### Don't write your own crypto primitive

AES, RSA, and their modes have failure states that are invisible until exploited (a reused nonce, a padding oracle, a missing authentication tag). Use a high-level, audited library (`cryptography`'s `Fernet` for simple symmetric encryption, or the library's documented recipe for the specific need) rather than composing primitives by hand from `cryptography.hazmat`. The `hazmat` namespace name is the library's own warning label.

---

**Applying this file:** the review question is what the worst input a caller could send would do — execute, leak, hang, or corrupt. Every finding names the specific vector (SQL injection, ReDoS, SSRF, etc.) and the line it applies to; "looks insecure" is not a finding.
