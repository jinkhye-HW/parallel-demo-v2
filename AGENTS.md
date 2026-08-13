## Agent skills

### Issue tracker

Issues live as GitHub issues in this repo, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles, label string equal to role name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Build lifecycle

Spec work runs **one spec, one branch, one PR** through `/jk-spec-flow`. Starting it is the human's call — asked to begin building a multi-ticket spec, name the skill and let them type it, then work the tickets it hands you.

Building **one ticket** onto a branch that already exists is `/jk-implement`, which you can run yourself. It carries the red-green loop, the review, and the commit contract that keeps the work traceable to its ticket.

<!-- jk-scan:start -->

## Session context

At session start, read:

- `docs/ARCHITECTURE.md` — the codebase map
- `docs/PRODUCT.md` — what the system is and who it's for
- `CONTEXT.md` — domain glossary

Read `docs/KNOWLEDGE.md` entries on demand via links from `docs/ARCHITECTURE.md`.

## Documentation maintenance

When you make a **significant** change, update the doc that describes it:

- Structural change → `docs/ARCHITECTURE.md`
- Domain term → `CONTEXT.md`
- Non-obvious learning or mistake avoided → `docs/KNOWLEDGE.md`

Trivial changes (rename, small refactor) skip doc updates.

**Fixing doc errors:** when you find a factual error in the docs, rewrite the original text — don't append a correction that contradicts it. If you're unsure whether it's an error, surface it to the user instead.

<!-- jk-scan:end -->
