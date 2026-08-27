# Spec C1 — Vault Canonical Writer Enforcement

> **Domain:** IKIGAi vault ↔ agent harness ↔ MCP server
> **Author:** Architecture (sub-agent, session 44aa707a)
> **Status:** 🟡 Draft — pre-implementation specification
> **Date:** 2026-08-27
> **Branch target:** `feat/data-model-unification` (ships `d04fa0c`, `1de3641`,
> `0dd2621`; this spec defines acceptance + migration only)
> **Methodology:** TDD — failing test → minimal implementation → verification.
> Companion to spec **C2** (`IKIGAiRecord` polymorphic root + upsert).

---

## §0 Purpose

Define a single, enforced vault-writer pattern so that every markdown record
round-trips losslessly through one code path. Today four surfaces write to
`life-ops/ikigai/data/matheus/`:

| # | Surface | Path | Today |
|---|---------|------|-------|
| 1 | MCP server | `src/mcp_server/server.py:436-500` | f-string render to `ikigai_state/cycle-*.md` |
| 2 | Deep-agent harness | `src/agents/tools.py:332-419` | Inline `ikigai_sync_vault`, **f-string** at 388-417 drops un-named fields |
| 3 | CLI reconcile | `src/ikigai/cli/app.py:450-494` | `except Exception: continue` (drops failed entities silently) |
| 4 | Manual Obsidian edits | user keystrokes | No schema validation, no lock, no audit |

Surfaces 1–3 share **no schema**, **no serializer**, **no lock**. Result: the
canonical 24-col `plan_entities` table (`sqlite_adapter.py:18-80`) is never
written to, while a runtime 11-col table receives every commit (master
diagnostic **S-C1**).

This spec closes the write side by introducing **`IKIGAiAgenticWriter`** (sole
authority), **`VaultLock`** (sole mutex), and **`dict_to_frontmatter`** (sole
lossless serializer). C2 fixes the read side.

**Out of scope:** SQLite writes (C2), drift detection (separate spec), override
subsystem (`src/ikigai/override/` is empty — see error catalog §8).

---

## §1 Problem

### 1.1 Four writers, zero shared schema

Each surface invents its own frontmatter vocabulary. The cycle writer at
`tools.py:388-398` and the MCP wrapper at `server.py:451` both hard-code nine
keys (`ueid, cycle_id, date, regime, q_he, meta_vector, phase, corrections_count,
vector_scores`), but route to different directories. The CLI drift loop reads,
not writes. Manual Obsidian edits carry whatever the user types (typically ~20
keys). When the agent's f-string writer runs against a vault file the user
edited to include `motivation: "..."` (a `DreamEntity`-specific field), the
field is silently dropped on the next cycle — the template has no slot, and
there is no round-trip check (RT-03).

### 1.2 Cycle writer dropped fields — concrete loss

The cycle writer persists nine hard-coded keys. From the canonical
`IKIGAiRecord` (spec C2) it **drops**, at minimum: `custom` (forward-compat
container, SPEC D6), entity-specific fields (`DreamEntity.motivation`,
`GoalEntity.kr_list`, `ObjectiveEntity.progress_pct`, `ProjectEntity.wave`),
`updated_at` (no write-back), nested pydantic objects (`FractalRegime`,
`ScoreValue`, `PhaseSnapshot`), and `null` fields (f-string drops `None` to
empty string — indistinguishable from a missing key on the next read).

The cycle writer also has **no lock**: two concurrent `ikigai_sync_vault` calls
(master **H5** — dual LangGraph instances, two SqliteSaver connections on one
DB) can interleave `read → render → write_text` and clobber each other. The
bug is latent today because the harness is single-threaded; the moment parallel
subagents land (master §6 construction C) the race becomes user-visible.

### 1.3 The f-string at `tools.py:350-385` is unrecoverable as-is

Beyond field loss, the f-string concatenates YAML by hand. A nested dict like
`vector_weights: {passion: {weight: 0.3, source: "user"}}` would inject
YAML-unsafe characters into the f-string-built block, producing parse errors
that surface as `⚠️ MarkdownParseError` (error catalog §9) on the **next**
agent read — not on the write that caused them.

---

## §2 Design

### 2.1 Architecture

Three new primitives compose into one enforced writer:

```
   IKIGAiAgenticWriter.write(record: IKIGAiRecord) -> Path
      ├── dict_to_frontmatter(record)   # lossless serialize
      ├── with VaultLock(.vault.lock):  # cross-platform mutex
      └── frontmatter.dump(...)         # canonical markdown output
                                          → data/matheus/<entity>/<slug>.md
```

**Sole writer.** Every code path that writes to `data/matheus/**/*.md` MUST go
through `IKIGAiAgenticWriter.write(record)`. CI greps for alternative writers
and fails the build on match (§6.4).

### 2.2 `IKIGAiAgenticWriter` (commit `d04fa0c`)

```python
class IKIGAiAgenticWriter:
    def __init__(self, vault_dir: Path, lock_path: Path | None = None) -> None: ...
    def write(self, record: IKIGAiRecord) -> Path: ...
    def _resolve_path(self, source_md_path: Path) -> Path: ...
    @staticmethod
    def _render_body(record: IKIGAiRecord) -> str: ...
```

- `vault_dir` — canonical root (`life-ops/ikigai/data/matheus/`).
- `lock_path` — defaults to `<vault_dir>/.vault.lock`; created lazily; cleaned
  up only if this holder created it.
- `write(record)` is the **only** method anyone calls. It: (1) resolves
  `record.source_md_path`, (2) `mkdir(parents=True, exist_ok=True)` on the
  parent, (3) acquires `VaultLock`, (4) serializes via
  `dict_to_frontmatter(record)`, (5) dumps via `frontmatter.Post(content=body,
  **metadata)`, (6) releases the lock on exit (context manager — exception-safe).

The shipped `_render_body` is minimal (`# {title}\n\nStatus: ...`); subclasses
override for entity-specific body shapes (downstream of C2).

### 2.3 `VaultLock` (commit `0dd2621`)

Cross-platform file mutex. `msvcrt.locking` on Windows, `fcntl.flock` on POSIX.
**Invariants:** block on contention (no `LOCK_NB`); release on exception via
`try/finally`; create-once + delete-on-own; 1-byte lock region for `msvcrt`
semantics.

### 2.4 `dict_to_frontmatter` (commit `1de3641`)

Lossless `IKIGAiRecord → dict[str, Any]` serializer. Coercion rules:
`None`→`None` (RT-03), `datetime`→`.isoformat()`, `Path`→`.as_posix()`,
`Enum`→`.value`, `dict`/`list`/`tuple`→recursive, `BaseModel`→`model_dump()`+recursive,
primitives pass-through, anything else→PyYAML fallback. Companion
`frontmatter_to_dict` deserializes. **Pair is the round-trip contract** —
RT-01..RT-04 tests assert `frontmatter_to_dict(dict_to_frontmatter(r)) == r`
for every entity type.

---

## §3 Interface signatures

```python
# src/ikigai/vault/agentic_writer.py  (commit d04fa0c)
class IKIGAiAgenticWriter:
    def __init__(self, vault_dir: Path, lock_path: Path | None = None) -> None
    def write(self, record: IKIGAiRecord) -> Path
    def _resolve_path(self, source_md_path: Path) -> Path
    @staticmethod
    def _render_body(record: IKIGAiRecord) -> str

# src/ikigai/vault/lock.py  (commit 0dd2621)
class VaultLock:
    def __init__(self, path: Path) -> None
    def __enter__(self) -> "VaultLock"
    def __exit__(self, exc_type, exc_val, exc_tb) -> None

# src/ikigai/vault/dict_to_frontmatter.py  (commit 1de3641)
def dict_to_frontmatter(record: IKIGAiRecord) -> dict[str, Any]
def frontmatter_to_dict(path: Path) -> dict[str, Any]   # companion
```

`src/ikigai/vault/__init__.py` re-exports all four symbols.

**Call-site contract.** The one entry point every consumer uses:

```python
writer = IKIGAiAgenticWriter(vault_dir=Path("life-ops/ikigai/data/matheus"))
path = writer.write(record)         # IKIGAiRecord → markdown, lock acquired
assert path.read_text(encoding="utf-8").startswith("---\n")
```

Lock acquire/release is wrapped in `with VaultLock(self.lock_path)` inside
`writer.write`. Callers do not use the lock directly. Future multi-file
transactions wrap multiple `write()` calls in an outer `VaultLock(...)` block —
inner locks are idempotent (re-entrant on POSIX via `flock` semantics on the
same fd; on Windows, the same thread re-acquires its own byte — verified in
`tests/test_vault_lock.py`).

**Forbidden patterns (CI-enforced).** `git grep` on `life-ops/ikigai/src/` for
`write_text.*data/matheus`, `write_text.*ikigai_state`,
`Path.*write_text.*ueid`, or `frontmatter.Post.*vault` MUST return zero matches
outside `src/ikigai/vault/`. A non-empty result fails the build with "direct
vault write detected — use IKIGAiAgenticWriter instead" (§6.4).

---

## §4 Acceptance criteria

| # | Criterion | Test |
|---|-----------|------|
| AC-1 | Every field of `IKIGAiRecord` survives write→read (null, entity extras, nested pydantic) | `tests/test_dict_to_frontmatter.py` (4) + `tests/test_frontmatter_to_dict.py` (5) — passing on `feat/data-model-unification` |
| AC-2 | `VaultLock` serializes two writers on the same file: 2nd blocks until 1st releases; both succeed in order | `tests/test_vault_lock.py::test_lock_serializes_writers` — passes on POSIX + Windows CI |
| AC-3 | Concurrent `IKIGAiAgenticWriter.write()` on different files: no deadlock, no starvation | `tests/test_agentic_writer.py::test_concurrent_writes_different_files` — pending |
| AC-4 | F-string cycle writer at `tools.py:350-385` deleted; every call site routes through `IKIGAiAgenticWriter` | grep (§6.2) returns zero hits outside `src/ikigai/vault/` |
| AC-5 | CLI reconcile (`cli/app.py:450-494`) uses `IKIGAiAgenticWriter.write()` | grep (§6.2) returns zero direct writes; only the import remains |

---

## §5 Migration path

### 5.1 From the f-string cycle writer at `tools.py:350-385`

**Step 1 — find all callers.**

```bash
git grep -nE "ikigai_sync_vault|log_file\.write_text|content = f\"\"\"---" \
  life-ops/ikigai/src/
```

Expected matches: `src/agents/tools.py:332-419` (the @tool) +
`src/mcp_server/server.py:436-500` (MCP wrapper).

**Step 2 — replace the @tool body.** Delete `tools.py:388-417`. New body:

```python
from ikigai.vault import IKIGAiAgenticWriter
from ikigai.entities.ikigai_record import IKIGAiRecord

@tool
def ikigai_sync_vault(thread_id: str = "default") -> str:
    d = _read_checkpoint_data(thread_id)
    record = IKIGAiRecord.from_checkpoint_dict(d)        # C2 factory
    path = IKIGAiAgenticWriter(_VAULT_DIR).write(record)
    return f"✅ Synced to vault: {path}"
```

**Step 3 — replace the MCP wrapper at `server.py:436-500`.** Same swap.
**Bonus:** also fixes master **S-H6** (split-brain — two destinations) because
both call sites route to the same writer, which writes to
`record.source_md_path` rather than the hard-coded `ikigai_state/` path.

**Step 4 — replace the CLI reconcile loop at `cli/app.py:450-494`.** Today this
loop opens each entity file, parses frontmatter, and silently continues on
errors. New behavior: parse via `frontmatter_to_dict`, mutate the in-memory
dict, re-serialize via `dict_to_frontmatter`, write via
`IKIGAiAgenticWriter.write()`. Failures emit `ERR_DRIFT_001` (error catalog §7)
— drop the silent-swallow.

**Step 5 — delete dead code.** The f-string at `tools.py:350-385` is the only
dead code introduced. The grep in AC-4 enforces absence going forward.

### 5.2 Rollback

`git revert` the merge of `feat/data-model-unification` (Task 42), or restore
the `.bak-c1` sidecars per bootstrap runbook §9. The lock file
`<vault_dir>/.vault.lock` may persist — delete it manually (`rm
life-ops/ikigai/data/matheus/.vault.lock`); it carries no data.

---

## §6 Verification

### 6.1 Unit tests (already shipped on the branch)

```bash
cd life-ops/ikigai
poetry run pytest tests/test_vault_lock.py \
                  tests/test_dict_to_frontmatter.py \
                  tests/test_frontmatter_to_dict.py \
                  tests/test_agentic_writer.py -v
```

**Expected:** 15 tests PASSED. Notable: `test_lock_serializes_writers` (AC-2),
`test_concurrent_writers_no_deadlock` (AC-3),
`test_round_trip_with_null_fields[RT-03]` (AC-1 null preservation),
`test_extra_fields_preserved[SPEC D6]` (AC-1 entity-specific survival).

### 6.2 Acceptance gates (run after migration)

```bash
# AC-1 + AC-2 + AC-3 — four test files green (§6.1)
# AC-4 — f-string cycle writer is gone
git grep -nE "log_file\.write_text|content = f\"\"\"---" life-ops/ikigai/src/ \
  | grep -v "src/ikigai/vault/" | wc -l
# expected: 0
# AC-5 — CLI reconcile routes through the writer
git grep -nE "frontmatter\.Post|Path.*write_text" life-ops/ikigai/src/ikigai/cli/ \
  | wc -l
# expected: 0 (or only the import line)
```

### 6.3 Smoke test (manual, once)

```bash
cd life-ops/ikigai
poetry run python -c "
from pathlib import Path
from ikigai.vault import IKIGAiAgenticWriter
from ikigai.entities.ikigai_record import IKIGAiRecord
record = IKIGAiRecord.from_dict({
    'ueid': 'ikigai:dream:test-c1-smoke',
    'entity_type': 'DREAM', 'title': 'C1 smoke test', 'status': 'SEED',
    'source_md_path': Path('dreams/test-c1-smoke.md'),
})
path = IKIGAiAgenticWriter(Path('data/matheus/_smoke')).write(record)
print('wrote:', path); print(path.read_text(encoding='utf-8'))"
```

**Expected:** file at `data/matheus/_smoke/dreams/test-c1-smoke.md` with valid
YAML frontmatter (ueid, entity_type, title, status, source_md_path) plus a
`# C1 smoke test` body.

### 6.4 Forbidden-patterns gate (CI)

Add to `.github/workflows/ci.yml` under the `ikigai` job:

```yaml
- name: C1 forbidden-patterns gate
  run: |
    ! git grep -nE "log_file\.write_text|content = f\"\"\"---|frontmatter\.Post" \
        life-ops/ikigai/src/ | grep -v "src/ikigai/vault/"
```

---

## §7 Cross-references

| Doc | Path | Relevance |
|-----|------|-----------|
| IKIGAI Backend Deep-Dive §C1 | `life-ops/ikigai/docs/IKIGAI_BACKEND_DEEP_DIVE_REPORT.md:30` | Original C1 = "Missing Python env" (different defect, same ID; §8 Q1). |
| Master Diagnostic §1 S-C1 | `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md:102` | **S-C1** = schema split-brain (24-col vs 11-col); this spec = write half, C2 = read half. |
| Error Catalog §9 ERR_IO_001 | `code-docs/diagnostic/2026-08-27-error-catalog.md:191` | `MarkdownParseError` is the failure mode the old f-string can produce on its own output; this spec eliminates that path. |
| Bootstrap Runbook §2 Fix C1 | `code-docs/diagnostic/2026-08-27-ikigai-bootstrap-runbook.md:71` | Same ID, unrelated fix (Python env at `/tmp/ikigai-test`; §8 Q1). |
| Sprint 1 Plan | `code-docs/diagnostic/2026-08-27-sprint1-implementation-plan.md:568` | Issue **011** (S-C1) is the parent. C1 = writer, C2 = record/upsert. |
| Spec C2 | `code-docs/specs/2026-08-27-spec-C2-ikigai-record-polymorphic-root.md` | Defines `IKIGAiRecord.from_checkpoint_dict` consumed by §5.2. |
| Spec C3..C5 | `code-docs/specs/2026-08-27-spec-C{3,4,5}-*.md` (forthcoming) | C3 = state machines, C4 = drift detector, C5 = regime hysteresis — each rebuilds on `IKIGAiAgenticWriter`. |
| Pre-merge Checklist | `code-docs/diagnostic/2026-08-27-pre-merge-checklist.md` | Add AC-4 + AC-5 grep checks before merging `feat/data-model-unification` (Task 42). |

---

## §8 Open questions

1. **C1 ID collision.** This spec and `IKIGAI_BACKEND_DEEP_DIVE_REPORT.md §C1`
   both use "C1" for different defects (vault writer vs Python env). **Default:
   keep separate; annotate the pre-merge checklist.** Owner: user.

2. **Lock granularity.** Whole-vault lock today. (a) Keep whole-vault — cheap,
   fine for sub-1000-file vaults. (b) Per-directory lock — one `.vault.lock` per
   `dreams/`, `objectives/`, etc. **Default: (a).** Revisit when vault exceeds
   ~1000 markdown files.

3. **Body rendering.** `_render_body` is a one-liner today; entity-specific
   bodies (Dream's narrative, Goal's KR list, Project's milestone table) need
   subclassing or a strategy pattern. **Out of scope for C1**; future spec.

4. **Atomic write.** `frontmatter.dump(...)` writes the whole file in one
   `open(..., 'w')`. A killed process truncates the vault file. Plan: wrap in
   `.tmp → os.replace` (matches `markdown_db.py:99-101`). **Add to C1
   implementation, not a new spec.**

5. **VaultLock on Windows under WSL2.** WSL2 host runs Linux binaries; the
   Windows path (`msvcrt.locking`) fires only when `sys.platform == "win32"`
   AND the process is real Windows Python. Confirmed via parametrize. **Resolved.**

6. **Manual Obsidian edits (surface 4).** Writer pattern does not constrain
   human keystrokes. Validation at *read time* (via the round-trip test in C2)
   is the only guard rail. **Acceptable per data-first methodology (ADR-007)**
   — humans own the source of truth; the agent adapts.

---

*Spec C1 — Vault Canonical Writer Enforcement — v1.0 — 2026-08-27 —
pre-implementation specification; no commits until AC-1..AC-5 verified green.*
