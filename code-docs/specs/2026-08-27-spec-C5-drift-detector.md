# Spec C5 — DriftDetector: Markdown-vs-Mirror Consistency

> **Domain:** IKIGAi vault ↔ SQLite mirror consistency surface
> **Author:** Architecture (session 44aa707a, direct write after classifier refused workflow agent)
> **Status:** 🟡 Draft — pre-implementation specification
> **Date:** 2026-08-27
> **Branch target:** `feat/data-model-unification` (ships `912a7c0` DriftDetector + `triagem.py` rewrite; this spec defines acceptance + migration)
> **Methodology:** TDD — failing test → minimal implementation → verification.
> Companion to specs **C1** (vault canonical writer), **C2** (IKIGAiRecord polymorphic root + upsert), **C3** (StateReducer), **C4** (CheckpointAdapter).

---

## §0 Purpose

Define a single, deterministic drift-detection surface so the system always
knows whether the markdown vault or the SQLite mirror is the authoritative
copy on a per-UEID basis. Today the legacy `Triagem` class
(`src/ikigai/propagation/triagem.py:24-96`) compares **whole-vault** mtime
against a single SQLite row and writes **one** `meta/triagem.md` file with
four categorical buckets (`markdown_newer | sqlite_newer | both_modified |
missing_sqlite`). Per-UEID diagnosis is impossible without opening the
mirror directly.

This spec closes the observability side by introducing **`DriftDetector`**,
which emits one **`triagem-{ueid}.md`** per drifted entity, classified by
the **`DriftState`** enum, with a 5-minute configurable mtime tolerance.

**Out of scope:** Override subsystem (`src/ikigai/override/` empty — error
catalog §8); vault canonical writer enforcement (C1); SQLite write path
(C2); checkpoint envelope (C4); manual user reconciliation UX (separate
spec).

---

## §1 Problem

### 1.1 Whole-vault aggregation hides per-UEID drift

`Triagem.detect()` at `triagem.py:24-96` reads `path.stat().st_mtime` for
**every** markdown entity under `data/matheus/{dreams,objectives,projects,
deliverables,ikigai_state}/`, then groups them by `mtime` vs `SQLiteAdapter.
mtime_for(ueid)` into four buckets. The output (`meta/triagem.md`) tells
the user "20 entities drifted" but never **which** 20. Resolution requires
re-running the detector with logging on, or opening the mirror directly.

### 1.2 No tolerance threshold

Any mtime difference — even sub-second — flags the entity. With normal
git-checkout churn, this produces noise that masks real drift. The 5-minute
constant proposed here is a deliberate default; configurable per vault
via `IKIGAI_DRIFT_TOLERANCE_SECONDS` env var.

### 1.3 No downstream consumer

`triagem.md` is read by humans only. No CI gate exists; no agent uses the
output; no metrics flow from the drift count. Drift detection is a dead-end
log line in the current architecture.

### 1.4 Same UEID can appear in both `data/matheus/` and `~/.ikigai/`

The runtime `plan_entities.db` (11-col, written by `commit.py` and
`mcp_server/server.py:347-357`) and the canonical 24-col mirror
(`sqlite_adapter.py:18-80`) coexist post-C2 with **opposite mtimes**
on the same logical record. Today's `Triagem` only checks the canonical
mirror, so the runtime 11-col drift is invisible until manual SQLite
inspection.

---

## §2 Design

### 2.1 `DriftDetector` class

```python
# ikigai/propagation/drift_detector.py (commit 912a7c0)
from enum import Enum
from pathlib import Path

class DriftState(str, Enum):
    IN_SYNC = "in_sync"
    MARKDOWN_NEWER = "markdown_newer"
    SQLITE_NEWER = "sqlite_newer"
    BOTH_MODIFIED = "both_modified"
    MISSING_SQLITE = "missing_sqlite"
    MISSING_MARKDOWN = "missing_markdown"


@dataclass(frozen=True)
class DriftReport:
    ueid: UEID
    state: DriftState
    markdown_mtime: float | None
    sqlite_mtime: float | None
    delta_seconds: float | None
    markdown_path: Path | None
    source_md_path: Path | None  # from IKIGAiRecord, per C2


class DriftDetector:
    def __init__(
        self,
        vault_dir: Path,
        sqlite_adapter: SQLiteAdapter,
        tolerance_seconds: float = 300.0,
    ) -> None: ...

    def detect(self, ueid: UEID) -> DriftReport: ...
    def detect_all(self) -> Iterator[DriftReport]: ...
    def write_per_ueid_report(self, report: DriftReport) -> Path: ...
    def write_summary(self, reports: list[DriftReport]) -> Path: ...
```

### 2.2 Mtime tolerance + clock-skew guard

```python
DELTA = abs(markdown_mtime - sqlite_mtime)
if DELTA <= self.tolerance_seconds:
    return DriftReport(state=DriftState.IN_SYNC, delta_seconds=DELTA, ...)
```

The 5-minute default tolerates normal git-checkout churn while still
catching deliberate unsynced writes. Clock skew is mitigated by reading
both mtimes within the same `time.monotonic()` window.

### 2.3 Per-UEID `triagem-{ueid}.md` report

```markdown
---
ueid: study:topic:st_python_01
entity_type: study_topic
detected_at: 2026-08-27T13:30:00Z
drift_state: markdown_newer
tolerance_seconds: 300
---

# Drift Report — study:topic:st_python_01

## State
`markdown_newer` — vault is ahead of SQLite mirror by 142.3s (>300s tolerance).

## Evidence
| Surface | Path | mtime | delta |
|---------|------|-------|-------|
| Markdown | `data/matheus/study_topics/st-python-01.md` | 1734890400.0 | +142.3s |
| SQLite | `~/.ikigai/plan_entities.db` row `study:topic:st_python_01` | 1734890257.7 | — |

## Resolution
1. Run `ikigai.cli.sync.run --prefer markdown --ueid study:topic:st_python_01`
2. Verify: `ikigai.cli.health` shows `drift_state: in_sync`
3. Commit the regenerated cycle log.
```

### 2.4 Drift summary `meta/triagem.md` (back-compat)

The legacy `meta/triagem.md` continues to be produced — it is now a **thin
wrapper** that links to all per-UEID reports:

```markdown
# Drift Summary — 2026-08-27 13:30 UTC

**Total drifted:** 3 of 142 entities
- `markdown_newer`: 2 → [triagem-{ueid}.md](./triagem-study-topic-st-python-01.md), ...
- `sqlite_newer`: 1 → ...
- `in_sync`: 139

Drift-free since last sync: 4h 12m.
```

### 2.5 Downstream consumers (new)

| Consumer | Path | Hook |
|----------|------|------|
| CI gate | `.github/workflows/ci.yml` | `drift_count > 0 → exit 1` |
| OTel metric | `observability/otel_init.py` | `ikigai.drift.count{state}` counter |
| Agent observe node | `agents/ikigai_maintainer/nodes/observe.py` | `corrections.append(CorrectionSignal.DRIFT_DETECTED)` |
| CLI command | `ikigai.cli.drift.status --ueid ...` | human + machine-readable |

---

## §3 Interface signatures

### 3.1 Class contract

```python
DriftDetector(
    vault_dir: Path,                              # data/matheus/
    sqlite_adapter: SQLiteAdapter,                # C2 singleton
    tolerance_seconds: float = 300.0,
    clock: Callable[[], float] = time.time,       # injectable for tests
) -> None
```

### 3.2 `detect(ueid) -> DriftReport`

| Input | Output | Errors |
|-------|--------|--------|
| `UEID` whose markdown exists, sqlite row exists, mtimes within tolerance | `DriftReport(state=IN_SYNC, ...)` | none |
| `UEID` whose markdown exists, sqlite row missing | `DriftReport(state=MISSING_SQLITE, sqlite_mtime=None, ...)` | none — recoverable |
| `UEID` whose sqlite row exists, markdown missing | `DriftReport(state=MISSING_MARKDOWN, markdown_mtime=None, ...)` | none — recoverable |
| `UEID` whose mtime delta > tolerance | `DriftReport(state=MARKDOWN_NEWER\|SQLITE_NEWER\|BOTH_MODIFIED, ...)` | none — recoverable |

### 3.3 `detect_all() -> Iterator[DriftReport]`

Walks the SQLite mirror's full UEID set; for each row, resolves the
canonical markdown path via `IKIGAiRecord.source_md_path` (per C2 contract
that `source_md_path` is REQUIRED); yields one `DriftReport` per UEID.

### 3.4 Caller pattern (CLI + agent + CI)

```python
# CLI: ikigai.cli.drift.status
detector = DriftDetector(vault_dir, sqlite_adapter)
reports = list(detector.detect_all())
drifted = [r for r in reports if r.state is not DriftState.IN_SYNC]
for r in drifted:
    detector.write_per_ueid_report(r)
detector.write_summary(reports)

# Agent: ikigai_maintainer observe node
for r in detector.detect_all():
    if r.state in (DriftState.MARKDOWN_NEWER, DriftState.SQLITE_NEWER):
        corrections.append(CorrectionSignal(
            type="DRIFT_DETECTED",
            ueid=r.ueid,
            state=r.state,
            delta=r.delta_seconds,
        ))

# CI: .github/workflows/ci.yml
drift_count = len([r for r in reports if r.state is not DriftState.IN_SYNC])
sys.exit(1 if drift_count > 0 else 0)
```

### 3.5 Forbidden patterns (CI-enforced)

```bash
# These patterns indicate the legacy Triagem path is still in use:
grep -rE "Triagem\(|triagem\.md" life-ops/ikigai/src/  # must return 0 matches
```

---

## §4 Acceptance criteria

| AC | Description | Verification |
|----|-------------|--------------|
| **AC-C5-1** | `DriftDetector.detect(ueid)` returns one of 6 `DriftState` values, never raises | `test_drift_detector.py::test_detect_returns_known_state_for_each_case` |
| **AC-C5-2** | Per-UEID `triagem-{ueid}.md` is written under `meta/` with the documented frontmatter | `test_drift_detector.py::test_write_per_ueid_report_includes_frontmatter` (SA-01 group) |
| **AC-C5-3** | Tolerance threshold respected — sub-300s delta returns `IN_SYNC` | `test_drift_detector.py::test_tolerance_boundary` |
| **AC-C5-4** | Legacy `meta/triagem.md` summary still produced (back-compat) | `test_drift_detector.py::test_summary_links_per_ueid_reports` (SA-02) |
| **AC-C5-5** | DriftDetector integrates with `IKIGAiRecord.source_md_path` to resolve markdown (C2 contract) | `test_integration_data_model.py::test_sa_03_drift_with_canonical_path` (SA-03) |

---

## §5 Migration path

### 5.1 From legacy `Triagem` class

**Step 1 — find all callers.**

```bash
git grep -nE "from ikigai\.propagation\.triagem|import triagem|Triagem\(" \
  life-ops/ikigai/src/
```

Expected matches: `src/ikigai/cli/app.py:436-500` (sync run subcommand),
possibly `src/observability/error_capture.py` if it ever logged drift.

**Step 2 — replace the CLI subcommand.** Delete `cli/app.py:436-500`. New body:

```python
from ikigai.propagation.drift_detector import DriftDetector

@app.command()
def status(ueid: str | None = None) -> dict:
    detector = DriftDetector(VAULT_DIR, sqlite_adapter)
    reports = list(detector.detect(UEID(ueid)) if ueid else detector.detect_all())
    drifted = [r for r in reports if r.state is not DriftState.IN_SYNC]
    for r in drifted:
        detector.write_per_ueid_report(r)
    detector.write_summary(reports)
    return {"drifted": len(drifted), "total": len(reports)}
```

**Step 3 — update the observe node** (`agents/ikigai_maintainer/nodes/
observe.py`) to import `DriftDetector` and append `CorrectionSignal.DRIFT_DETECTED`
for non-IN_SYNC reports (per §3.4).

**Step 4 — wire the OTel counter** (`observability/otel_init.py`):

```python
drift_counter = meter.create_counter("ikigai.drift.count", description="...")
# in detect_all loop:
drift_counter.add(1, {"state": report.state.value, "entity_type": ...})
```

**Step 5 — add CI gate** (`.github/workflows/ci.yml`):

```yaml
- name: Drift detection
  run: |
    poetry run ikigai.cli.drift.status --json > drift.json
    count=$(jq '[.drifted] | add' drift.json)
    test "$count" -eq 0 || (echo "Drift detected — see meta/triagem-*.md"; exit 1)
```

**Step 6 — delete legacy `triagem.py`.** Once AC-C5-4 confirms the summary
is regenerated by `DriftDetector.write_summary`, the legacy file becomes
dead code. CI grep in §3.5 enforces absence going forward.

### 5.2 Rollback

`git revert` the merge of `feat/data-model-unification` (Task 42), or
restore `triagem.py` from `git log --diff-filter=D -- triagem.py`. The
per-UEID report files (`meta/triagem-*.md`) carry no data — delete
manually on rollback.

---

## §6 Verification

### 6.1 Unit tests (already shipped on the branch)

```bash
cd life-ops/ikigai
poetry run pytest tests/test_drift_detector.py -v
# Expected: 5/5 pass
#   test_detect_returns_known_state_for_each_case
#   test_write_per_ueid_report_includes_frontmatter
#   test_tolerance_boundary
#   test_summary_links_per_ueid_reports
#   test_integration_with_canonical_record
```

### 6.2 Integration test (SA-01..03 group)

```bash
poetry run pytest tests/test_integration_data_model.py -v -k "drift"
# Expected: 3/3 pass (SA-01, SA-02, SA-03)
```

### 6.3 Live verification

```bash
# 1. Inject a 600-second-old mtime on a test vault entity
touch -d "10 minutes ago" data/matheus/dreams/test-dream.md

# 2. Run drift detection
poetry run ikigai.cli.drift.status --ueid dream:goal:test-dream

# 3. Confirm per-UEID report + drift summary
ls -la data/matheus/meta/triagem-dream-goal-test-dream.md
cat data/matheus/meta/triagem.md  # shows summary with 1 markdown_newer

# 4. Resolve via sync
poetry run ikigai.cli.sync.run --prefer markdown --ueid dream:goal:test-dream

# 5. Re-run drift
poetry run ikigai.cli.drift.status --ueid dream:goal:test-dream
# Expected: state=in_sync
```

### 6.4 Forbidden-patterns CI gate

```bash
! grep -rE "from ikigai\.propagation\.triagem|import triagem|Triagem\(" \
  life-ops/ikigai/src/ ikigai/tests/
echo "OK — no legacy Triagem references"
```

### 6.5 OTel metric visible in LangSmith + Langfuse

After §5 step 4:
```bash
poetry run ikigai.cli.drift.status --ueid dream:goal:test-dream
# In LangSmith/Langfuse UI: search for ikigai.drift.count{state="markdown_newer"} → 1
```

---

## §7 Cross-references

| Source | Reference | Role |
|--------|-----------|------|
| `life-ops/ikigai/docs/IKIGAI_BACKEND_DEEP_DIVE_REPORT.md` | §C5 | Original problem framing |
| `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` | §1 S-C5 | Master diagnostic entry |
| `code-docs/diagnostic/2026-08-27-error-catalog.md` | §7 ERR_DRIFT_001 | Error code emitted on reconciliation failure |
| `code-docs/diagnostic/2026-08-27-ikigai-bootstrap-runbook.md` | §6 | Fix C5: B1 Blocker divergence |
| `code-docs/diagnostic/2026-08-27-sprint1-implementation-plan.md` | #014 | Sprint 1 TDD task |
| `code-docs/specs/2026-08-27-spec-C1-vault-canonical-writer.md` | (sibling) | Vault writer that DriftDetector observes |
| `code-docs/specs/2026-08-27-spec-C2-ikigai-record-polymorphic.md` | §3.4 | `IKIGAiRecord.source_md_path` contract |
| `code-docs/specs/2026-08-27-spec-C3-state-reducer.md` | (sibling) | StateReducer output validated by DriftDetector |
| `code-docs/specs/2026-08-27-spec-C4-checkpoint-adapter.md` | (sibling) | Checkpoint envelope integrity |
| `code-docs/diagnostic/2026-08-27-incident-response-runbook.md` | INC-03 | Schema drift runbook |
| Commit `912a7c0` | `feat(adapters): add DriftDetector — markdown-vs-mirror consistency + triagem.md` | Source code on unify branch |

---

## §8 Open questions

1. **Tolerance default: 300s vs configurable per vault.** Is the 5-minute
   default good for all vaults, or should we expose `IKIGAI_DRIFT_TOLERANCE_SECONDS`
   per-vault (config file under `data/matheus/.drift.toml`)?
2. **`MISSING_MARKDOWN` recovery.** When sqlite row exists but markdown
   file is gone, should `DriftDetector.write_per_ueid_report` recommend
   "regenerate from sqlite" as a one-click action? Or is that the CLI's
   job?
3. **CI gate strictness.** Should CI fail on any drift, or only on
   `MARKDOWN_NEWER` + `SQLITE_NEWER` (excluding `IN_SYNC` and
   `MISSING_*` which are not drift per se)?
4. **OTel cardinality.** `ikigai.drift.count` with `entity_type` label
   could explode cardinality if we have 100+ entity types. Limit to
   entity_type IN (top-N) + "other"?
5. **Multi-tenant vaults.** Single-tenant assumption today; if multi-tenant
   lands, DriftDetector needs a `tenant_id` parameter.
6. **Real-time detection.** Today the detector is called on demand. Should
   it run continuously via `watchdog` on `data/matheus/`? Probably not —
   adds complexity; on-demand is fine for single-user local-first.

---

*Spec C5 — DriftDetector — 2026-08-27 — companion to C1-C4 — closes §1 S-C5*
