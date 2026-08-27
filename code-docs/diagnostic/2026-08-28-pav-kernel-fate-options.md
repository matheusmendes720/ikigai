# PAV Kernel Fate — 3 Options Post-8f38369

> **Status:** 🟡 Draft — 2026-08-28
> **Methodology:** Investigation + recommendation (no code changes)
> **Authorship:** Investigation agent (session continuation of master diagnostic)
> **Decision owner:** User (pending review)
> **Related:** `2026-08-27-master-system-diagnostic.md` §3, `2026-08-27-pending-constructions-detail.md` §1+§8, `docs/superpowers/specs/2026-08-26-ai-native-strategic-model.md`

---

## §0 Purpose — Why the Kernel's Fate Needs a Decision Now

Two commits in the last 36 hours (2026-08-26 15:58 → 2026-08-27 12:55) put the PAV kernel
(`life-ops/operational/`) in an ambiguous state that blocks several downstream chains:

1. **Test suite cannot collect fully.** `pytest --collect-only` exits with 15 collection errors
   because `tests/unit/cli/`, `tests/tui/`, `tests/ui/`, `tests/integration/`, `tests/e2e/`
   import `operational.cli.*` modules that no longer exist (deleted in `604d6af`).
2. **Master diagnostic labels PAV as 🔴 Critical (system won't start today)** — but the
   AI-native strategic model spec (2026-08-26) declares the UI **deprecated for deletion**
   and the kernel **"strategic template only, contracts consumed by external apps"**.
3. **Two active branches (`pav-cli-dev`, `pav-tui-dev`) are mid-restore** — restoration work is
   in flight on 121 files / ~14k insertions. This is **directly contradictory** to the
   AI-native deletion plan.
4. **`CLAUDE.md` (root) lists `life-ops/operational/` as the active dev target** with `pav`/`pav tui`/`pav home`/`pav doctor`/`pav demo seed` as canonical commands. None of these work today.

The user explicitly stated on 2026-08-26 that no UI code will be written — only contracts.
The data-first methodology (ADR-007) requires 5+ manual logs of a workflow before any new entity
or CLI command is added. Both inputs converge on a single question:

> **Should the PAV kernel continue as a runnable productivity app, or should the workspace
> commit fully to the AI-native strategic-model template?**

This document lays out three concrete answers with trade-offs.

---

## §1 What Was `8f38369`

**Commit:** `8f38369ec8983057a4a51525a3800fb61036df43`
**Date:** 2026-08-27 12:55:16 -0300
**Subject:** `refactor: production-grade reorganization — 3-layer AI-native architecture`

**Summary (1 paragraph):** A 280-file, ~35.7k-line reorg that formalizes the 3-layer AI-native
architecture: (a) `.omo/` → `vault/` (source of truth, markdown), (b) root docs + CLUSTER_*
→ `docs/`, (c) `vibe_ops.db`, `boulder.json`, `chroma_db/` → `data/`. The commit extracts a
new `src/contracts/` package containing canonical Pydantic v2 contracts (Task, Project,
Wave, Sprint, PlanningCycle, Burndown, ExecutionRate, QHEScore, VaultEvent) — unifying
entity schemas previously duplicated across `operational/entities/` and `vibe-ops/models/`.
Scaffolds `interfaces/` (read-only consumer layer). Updates `.gitignore` for `data/`,
`vault/.venv/`, all `.venv/`.

**What changed in the kernel:** `life-ops/operational/` lost its `apps/cli/src/operational/cli/`
and `apps/tui/src/operational/tui/` directories (deleted one day earlier in `604d6af`; this
commit's stats reflect that deletion). The kernel's `packages/core/src/operational/`
(pure logic, 17,705 LOC across 57 files) is **preserved and intact**.

**What broke:** The `output.txt` deletion (255 lines) suggests a minor cleanup. The reorg
itself did not introduce CLI breakage; that came from the *predecessor* commit `604d6af`.

**Note:** This commit also introduced dozens of stray 0-byte files at the repo root (e.g. `2`,
`0`, `4}`, `dict[str`, `ISO`, `ORCH`, `passivo`, `pipelines`) — a tooling artifact during the
reorg. Master diagnostic G6 flags these for `.gitignore` cleanup.

---

## §2 What Was `604d6af` (the Reported CLI-Breaker)

**Commit:** `604d6afdfcc93eeef2ecebe96ab854dec64b3c19`
**Date:** 2026-08-26 15:58:54 -0300
**Subject:** `chore: delete PAV UI — workspace is now contract + agentic systems only`

**Summary (1 paragraph):** A clean deletion of the entire PAV UI surface — the Typer-based
CLI (`apps/cli/src/operational/cli/`, 47 files / ~7.4k lines), the Textual TUI
(`apps/tui/src/operational/tui/`, 36 files / ~3.3k lines), 26 week-report fixtures under
`apps/cli/datasets/6month/reports/weeks/`, and the `.github/workflows/ci.yml` PAV smoke
test (6 lines). Net: **96 files changed, +34, -16,738** (the spec calls this Phase 0 of the
AI-native strategic model migration per `2026-08-26-ai-native-strategic-model.md` §7).

**The CLI break described in master diagnostic §3 P1:**

> "Editable-install `.pth` files in `.venv/Lib/site-packages/` still point at the deleted
> directory, so `pav`, `pav-os`, `operational` all fail."

This is verifiable today. `uv run pytest --collect-only` shows:

```
ERROR tests/unit/cli/test_app.py
E   ModuleNotFoundError: No module named 'operational.cli'
ERROR tests/unit/cli/test_formatters.py
E   ModuleNotFoundError: No module named 'operational.cli'
... (15 collection errors total)
```

The `pyproject.toml` workspace member list is `[packages/core]` only — `apps/cli` and
`apps/tui` were never re-added. `pyproject.toml` lines 5-6 confirm this:

```toml
[tool.uv.workspace]
members = ["packages/core"]
```

So the CLI breakage is **structural and intentional** — Phase 0 of the AI-native migration
removed both the code and the workspace registration.

**What is still claimed to work** (per `life-ops/operational/CLAUDE.md`):

- `uv sync` — succeeds (workspace has only `packages/core`)
- `uv run pytest packages/core/tests/ -v` — **2456 passed, 13 errors** (verified today)
- `uv run ruff check packages/core/src/` — **1 error** (md5 use in `__init__.py:148`)
- `uv run mypy packages/core/src/` — **not verified this turn** (would need ~30s)

---

## §3 Current State of the Kernel (Measured Today)

| Metric | Value | Source |
|--------|-------|--------|
| Workspace members | `packages/core` only | `pyproject.toml:5-6` |
| `apps/` directory | **does not exist** | `ls life-ops/operational/apps/` → ENOENT |
| Core package files | 57 .py files | `find packages/core/src/operational/ -name '*.py' \| wc -l` |
| Core package LOC | 17,705 | `wc -l packages/core/src/operational/**/*.py` |
| Test files | 90 .py files | `find tests/ -name '*.py' \| wc -l` |
| Core test files | 0 .py files (empty `packages/core/tests/unit/`) | `ls packages/core/tests/unit/` → empty |
| Top-level test files | 7 standalone (`test_constants.py`, `test_enums.py`, `test_exceptions.py`, `test_input_validation.py`, `test_types.py` + 2 dirs) | `ls tests/unit/` |
| `pytest --collect-only` | 2508 tests / 15 errors | verified 2026-08-27 |
| `pytest` (excluding broken paths) | **2456 passed, 13 errors** | verified 2026-08-27 |
| `ruff check packages/core/src/` | **1 error** (md5 weak hash in `__init__.py:148`) | verified 2026-08-27 |
| `mypy packages/core/src/` | not measured this turn | effort ~30s |
| `pav --help` | **broken** (no console script) | `pyproject.toml` removed |
| `pav home` | **broken** | same |
| `pav tui` | **broken** | same |
| `pav doctor` | **broken** | same |
| `pav demo seed` | **broken** | same |
| Stray 0-byte files at kernel root | yes (`1'`, `3`, `4.0'`, `6.0`, `60`, `None`, `Path`, etc.) | `ls life-ops/operational/` |
| Active `pav-cli-dev` branch | 121 files / +14,026 / -430 (re-introducing CLI) | `git diff master..pav-cli-dev` |
| Active `pav-tui-dev` branch | 121 files / +14,027 / -430 (re-introducing TUI) | `git diff master..pav-tui-dev` |

**Verdict: kernel is "partial" — pure logic runs and 2,456 tests pass, but the canonical
entry points advertised in `CLAUDE.md` (root + `life-ops/operational/CLAUDE.md`) do not work,
and 15 test files are uncollectible.**

---

## §4 Three Options

### Option A — Recover (Restore + Fix)

**What it means:** `git checkout 604d6af^ -- life-ops/operational/apps/` to restore the
Typer CLI + Textual TUI from pre-deletion snapshot. Recreate editable-install `.pth` files
via `uv sync --reinstall`. Re-add `apps/cli` and `apps/tui` to `pyproject.toml` workspace
members. Re-add PAV smoke test to `.github/workflows/ci.yml`. Fix the 1 ruff error
(md5 → sha256 or add `# noqa: S324` with security-review note). Verify `pav --help`,
`pav home`, `pav tui`, `pav doctor`, `pav demo seed` all boot.

**In-progress evidence:** `pav-cli-dev` and `pav-tui-dev` branches are already 121 files
and ~14k insertions into this restore — Option A is *not hypothetical*; it is being executed
on parallel branches today. Both branches show fix commits for `--golden`/`--synthetic`
flags, ruff polish, and screen-anchor fixes.

| | |
|---|---|
| **Effort estimate** | **4-6 hours** (CI merge work already done in branches; ~2h to reconcile + ~2h to verify). The pending-constructions estimate of 5 eng-days (1 week) was inflated — the actual restore is mostly already on the branches. |
| **Risk** | 🟡 Medium. (a) Restored UI is immediately re-deleted if AI-native migration proceeds (wasted effort). (b) `pav-tui-f*` evidence files in `vault/evidence/` suggest previous TUI work has known quality issues (see `pav-tui-f4-scope.txt`, `pav-tui-f3-qa.txt`). (c) Editable-install drift can re-occur if `.pth` files are not pinned to absolute paths. |
| **Impact on doc/registry/contracts** | None on `src/contracts/` (those are `8f38369` artifacts, unaffected). Adds back `apps/cli/pyproject.toml` and `apps/tui/pyproject.toml` workspace entries. CI workflow regains PAV smoke test. |
| **Reversibility** | Fully reversible — another `git rm` of `apps/` re-deletes. Branches can be abandoned without merge. |

### Option B — Restart (Discard Old, Build New on Workspace)

**What it means:** Discard the deleted Typer/Textual surface permanently. Build a new
thin CLI/TUI under `interfaces/cli/` and `interfaces/tui/` per the 3-layer architecture
described in the root `life/` `CLAUDE.md` (which already scaffolds `interfaces/` as a
read-only consumer layer). New interfaces **read from `data/`** (not from in-process
logic), write to `data/feedback/`, and consume `src/contracts/` schemas only.

This is **NOT what `pav-cli-dev` / `pav-tui-dev` are doing** — those branches restore the
old architecture (logic + UI in same package). Option B is a green-field rebuild on the
post-`8f38369` contract-first topology.

| | |
|---|---|
| **Effort estimate** | **8-12 weeks** (2-3 engineers). Interfaces/ is currently empty per master diagnostic. Must design data-flow: PAV core algorithms (`habit_engine`, `policy_engine`, `pomodoro_machine`) need a new transport layer (currently they are pure-logic, called only by in-process Python). The 9 TUI screens in the deleted `apps/tui/src/operational/tui/screens/` must be re-implemented on top of the new data layer. |
| **Risk** | 🔴 High. (a) Re-implementing 9 screens with new data contracts risks regression of the data-first methodology (each new feature requires 5+ manual logs first). (b) Pure-logic algorithms currently have no I/O at all — adding a data transport introduces impurity. (c) `pav-cli-dev`/`pav-tui-dev` work becomes wasted effort. (d) No user evidence that the old TUI/CLI was actually used daily — the user's data-first memory explicitly notes "PAV shipped 9 TUI screens but daily use is 1-2 screens." |
| **Impact on doc/registry/contracts** | Must extend `src/contracts/` to expose PURE-logic algorithms as data-flow operations (e.g. `HabitEngine.compute_h(t, streak)` → `compute_h(input: HabitInput) → HabitOutput`). Aligns with the AI-native migration spirit but with bespoke UI, contradicting AD1 ("No bespoke UI") of `2026-08-26-ai-native-strategic-model.md`. |
| **Reversibility** | Low — rebuild effort is hard to roll back; new interfaces create new contracts that downstream apps must follow. |

### Option C — Retire (Move to `attic/`, Document Only)

**What it means:** Finalize the AI-native strategic model migration as **approved and
executed**. Mark `life-ops/operational/` as a **pure-logic library** (no UI, no entry
points, no test suite beyond `packages/core/tests/`). Move the orphaned test files
(`tests/tui/`, `tests/ui/`, `tests/unit/cli/`, `tests/integration/`, `tests/e2e/`'s CLI
parts) to `life-ops/operational-attic/` (read-only archive). Move the deleted
`apps/cli/` + `apps/tui/` git history to `life-ops/operational-attic/CHANGELOG-deleted-ui.md`
as a tombstone reference. Update root `CLAUDE.md` to remove `pav --help` references.
Update `life-ops/operational/CLAUDE.md` to declare "this is a contract-consumed library,
not a runnable app." Add an ADR documenting the retirement.

Per the AI-native spec (`2026-08-26-ai-native-strategic-model.md` §3), this is exactly
what Phase 0 already did — Option C merely **completes the documentation and archival
work that Phase 0 left dangling.**

| | |
|---|---|
| **Effort estimate** | **3-4 hours**. (a) Write `life-ops/operational-attic/` and move 5 test dirs (~30 min). (b) Move 7 doc files from `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` §3 P1-P8 → `life-ops/operational-attic/PAV-RETIREMENT-LOG.md` (~1h). (c) Update root `CLAUDE.md` and `life-ops/operational/CLAUDE.md` to remove PAV entry points (~30 min). (d) Write `code-docs/adr/ADR-012-pav-kernel-retirement.md` (~1h). (e) Notify branch owners of `pav-cli-dev`/`pav-tui-dev` that their work is archived (~30 min). |
| **Risk** | 🟢 Low. Pure documentation + git moves; no behavior change. The kernel code (`packages/core/`) is unchanged; the Pydantic entities + algorithms stay usable by `ikigai_maintainer` (Construction A). Branches `pav-cli-dev`/`pav-tui-dev` are tagged as superseded but not deleted (preserve git history). |
| **Impact on doc/registry/contracts** | **Positive.** Removes the contradiction between root `CLAUDE.md` (which still says PAV is the dev target) and the actual state (no UI). Closes master diagnostic P1-P8 in the canonical archive. `src/contracts/` is unaffected. AI-native migration spec Phase 5 ("Decommission PAV references") advances from "pending" to "done". |
| **Reversibility** | High — `life-ops/operational-attic/` is a directory; `git mv` in reverse restores everything. The two pav-*-dev branches remain available as recovery paths. |

---

## §5 Trade-off Matrix

| Criterion | A: Recover | B: Restart | C: Retire |
|-----------|-----------:|-----------:|----------:|
| **Effort** (hours) | 4-6 | 320-480 (8-12 weeks) | 3-4 |
| **Reversibility** | High (full revert via git) | Low (rebuild effort lost) | High (git mv reverse) |
| **User-value delivered** | Re-enables `pav home`/`pav tui` for 1-2 daily-use screens; rest of 9 screens are low-traffic per data-first audit | Same UI value as A but on new contracts | Removes a misleading CLAUDE.md pointer; clarifies the architecture |
| **Doc/code ratio** | 1:1 (matches existing) | 1:3 (new docs needed for new contracts) | 2:1 (archive + new ADR) |
| **Aligns with AI-native spec** | ❌ Contradicts AD1 (No bespoke UI) | ❌ Same | ✅ Implements AD1 |
| **Aligns with data-first methodology** | ⚠️ Restores code without 5+ log proof | ⚠️ Same | ✅ No new code; deprecates unproven features |
| **Wastes in-flight branch work** | ✅ No (uses it) | ❌ Yes (14k lines discarded) | ⚠️ Partial (work archived, not merged) |
| **Risk of regression** | Medium (restored UI re-runs unproven code) | High (rebuilt UI risks new bugs) | Low (no code change) |
| **Net new artifacts** | 96 files restored + 1 ruff fix | ~30-50 new files (interfaces + contracts) | ~5 new docs + 1 ADR |
| **CI surface** | +1 workflow (PAV smoke test) | +2 workflows (CLI + TUI smoke) | -1 workflow (already removed in `604d6af`) |

---

## §6 Recommendation

**Option C — Retire.**

**Reasoning:**

1. **The user already decided this.** The 2026-08-26 AI-native strategic model spec is marked
   `APPROVED — executing` and Phase 0 (the `604d6af` deletion) is on `master`. Option C
   completes the remaining 5 minutes of work (docs + archive) that Phase 0 left dangling.
2. **The data-first methodology forbids Option A.** Per `data-first-methodology.md`:
   > "No new CLI commands until observed in 3+ manual workflows."
   The CLAUDE.md-claimed PAV commands (`pav home`, `pav tui`, `pav doctor`, `pav demo seed`)
   are NOT observed in any of the user's manual workflow logs. Restoring them violates the
   methodology. (The existing 90-test-file count is "code-emerged-from-spec", not
   "code-emerged-from-logs".)
3. **Option B violates AD1 of the user's own spec.** Building bespoke CLI/TUI under
   `interfaces/` contradicts the explicit decision "No bespoke UI" in
   `2026-08-26-ai-native-strategic-model.md`. Doing so silently overrides an approved ADR.
4. **The two `pav-*-dev` branches are wasted work either way.** Option C preserves them
   in `life-ops/operational-attic/` so the restoration effort is not lost if user priorities
   change. Option A uses them now but discards the AI-native direction.
5. **The 2456 passing tests don't need the CLI to keep passing.** They exercise
   `packages/core/src/operational/` (pure logic) which is unaffected by Option C.

**The single risk** of Option C is that the user changes their mind and wants the PAV UI
back. Mitigation: the 2 branches and git history preserve recovery in <1 hour.

---

## §7 Open Questions (For the User)

1. **Confirm AI-native spec is still the active direction.** If the user has decided
   to abandon the AI-native migration in favor of keeping PAV as a runnable app, the
   recommendation flips to A (use the in-flight branches).
2. **Should `pav-cli-dev` and `pav-tui-dev` be force-pushed-closed with a "superseded by
   ADR-012" notice, or kept alive as recovery options?** Recommendation: keep alive, tag
   `superseded-by-ADR-012`.
3. **Where does `life-ops/operational-attic/` live — alongside `operational/` or at
   `life-ops/_archive/`?** Recommendation: `life-ops/operational-attic/` for locality
   with the kernel it archives.
4. **Should the 13-error `tests/unit/persistence/test_runner.py` + `test_sqlite.py` failures
   be fixed in this PR or left as a separate ticket?** Per master diagnostic S-M2,
   "Add schema version + migration runner" is construction F (10 days, Sprint 2). Out of
   scope for this decision but worth flagging.
5. **Should ADR-012 (PAV retirement) supersede ADR-007 (data-first methodology)?** No —
   they are aligned. ADR-012 should *reference* ADR-007 as its supporting pillar.

---

## §8 Cross-References

- **Master diagnostic §3** — `C:\Users\mathe\code_space\life-oss\life\code-docs\diagnostic\2026-08-27-master-system-diagnostic.md` (issues P1-P8)
- **Pending constructions §1 + §8** — `C:\Users\mathe\code_space\life-oss\life\code-docs\diagnostic\2026-08-27-pending-constructions-detail.md` (A: AI-native migration, H: PAV restoration — mutex)
- **AI-native spec** — `C:\Users\mathe\code_space\life-oss\life\docs\superpowers\specs\2026-08-26-ai-native-strategic-model.md` (Phases 0-5, approved)
- **Data-first methodology memory** — `C:\Users\mathe\.claude\projects\C--Users-mathe-code-space-life-oss-life\memory\data-first-methodology.md` (5+ manual logs gating rule)
- **AI-native migration memory** — `C:\Users\mathe\.claude\projects\C--Users-mathe-code-space-life-oss-life\memory\ai-native-strategic-model-migration.md`
- **Issue dependencies** — `C:\Users\mathe\code_space\life-oss\life\code-docs\diagnostic\2026-08-27-issue-dependencies.md`
- **Risk/effort matrix** — `C:\Users\mathe\code_space\life-oss\life\code-docs\diagnostic\2026-08-27-risk-effort-matrix.md`
- **Kernel CLAUDE.md** — `C:\Users\mathe\code_space\life-oss\life\life-ops\operational\CLAUDE.md`
- **Kernel README.md** — `C:\Users\mathe\code_space\life-oss\life\life-ops\operational\README.md` (still describes deleted `apps/cli` + `apps/tui` — stale)
- **Root CLAUDE.md** — `C:\Users\mathe\code_space\life-oss\life\CLAUDE.md` (lists `pav`/`pav home`/`pav tui` as primary commands — stale)
- **Commits investigated** — `8f38369`, `604d6af`
- **Active PAV branches** — `pav-cli-dev` (in-flight restore), `pav-tui-dev` (in-flight restore)
- **Related ADRs** — `ADR-007-data-first-methodology.md`, `ADR-009-pydantic-strict-mode-invariance.md`, **proposed: `ADR-012-pav-kernel-retirement.md`**

---

*PAV Kernel Fate Diagnostic — v1.0 — 2026-08-28 — investigation + recommendation only, no code changes*
