# Diagnostic 03 — Interfaces + Drift Detector + Tests + TUI

**Date:** 2026-09-04
**Agent:** diagnostic agent 03 of 10
**Scope:** Component Hierarchy — `interfaces/`, drift detector, test infra, vault templates
**Method:** read-only static inspection (no pytest execution, per constraint)
**Branch:** `sonho-tree/plan-a-planning-contract`

---

## 1. Inventory

| Component | File path | Lines | Status | Verified by |
|---|---|---|---|---|
| CLI package root (Typer assembly) | `interfaces/cli/__init__.py` | 46 | ✅ live | Read; `app.add_typer(server_app)` + `add_typer(v2_app)` at `__init__.py:43-44` |
| CLI entrypoint | `interfaces/cli/__main__.py` | 6 | ✅ live | Read |
| CLI task/mesh commands | `interfaces/cli/read_tasks.py` | 522 | ✅ live | Grep — 8 `@app.command` |
| CLI server sub-app | `interfaces/cli/server.py` | 483 | ⚠️ partial (start/stop STUB) | Grep — 5 `@server_app.command`; STUB noted at `__init__.py:16` |
| CLI v2 sub-app | `interfaces/cli/v2.py` | 172 | ✅ live | Read — 3 commands |
| CLI MCP gateway probe | `interfaces/cli/mcp_gateway_probe.py` | 91 | ✅ live | wc |
| Operator TUI app | `interfaces/tui/operator/app.py` | 372 | ✅ live — **4 tabs, not 3** | Read `app.py:1-16`, `:84-91` |
| Operator TUI data layer | `interfaces/tui/operator/data.py` | 370 | ✅ live | wc; imported at `app.py:31-38` |
| Operator TUI styles | `interfaces/tui/operator/styles.tcss` | — | ✅ present | `app.py:80` `CSS_PATH` |
| Operator TUI entry | `interfaces/tui/operator/__main__.py` | 18 | ✅ live | ls |
| Drift detector | `src/ikigai/tests/test_canonical_scope.py` | 469 | ✅ live — **8 tests** | Read (full) |
| Root conftest | `conftest.py` | 27 | ✅ live | Read |
| Tests conftest | `tests/conftest.py` | 24 | ✅ live | Read |
| ikigai conftest | `tests/ikigai/conftest.py` | 54 | ⚠️ workaround-laden | Read |
| v2 conftest | `tests/ikigai/agents/v2/conftest.py` | 57 | ❌ not sufficient — debug scaffolding present | Read |
| pytest config | `pytest.ini` | 3 | ❌ root cause of collection failure | Read (full) |
| Vault templates (6-tier) | `vault/ikigai/` | — | ❌ **absent** | find — 0 SONHO/OBJETIVO/META/PROJETO/ENTREGA/TAREFA templates |

**Note:** `interfaces/cli/` contains a vendored `.venv/` with site-packages. All line counts above exclude it.

---

## 2. TUI tabs

The memory `option-a-phase-9-shipped-2026-09-03.md:17` claims **3 tabs (Adapters/Backend/Queue)**. Current code has **4**. Docstring at `interfaces/tui/operator/app.py:3-8`:

| # | Tab | Purpose | Binding |
|---|---|---|---|
| 1 | **Tasks** | Live view of `data/tasks.jsonl` (Deep Agent output); auto-refresh every 2s via filesystem poll | `Binding("1", "show_tasks")` — `app.py:85` |
| 2 | **Adapters** | Fork adapter registry + storage-path liveness | `app.py:86` |
| 3 | **Backend** | Backend process status (`mcp_gateway`, `review_queue_worker`); Tier-2 adds Started + Uptime columns from pidfile mtime | `app.py:87` |
| 4 | **Queue** | Pending `TaskChange` events in `data/review_queue/`; press `d` to drill down to full JSON payload | `app.py:88` |

Extra bindings: `d` drilldown (`app.py:89`), `r` refresh (`:90`), `q` quit (`:91`).
`QueueDetailScreen` (`app.py:46-72`) is a read-only `ModalScreen` — explicitly documented as never mutating state, upholding the dual-layer architecture invariant (`app.py:49-50`).

**Drift finding:** memory says 3 tabs + 5s refresh + bindings `1/2/3/r/q`. Code says 4 tabs + 2s Tasks refresh + bindings `1/2/3/4/d/r/q`. The Tasks tab is undocumented in memory.

---

## 3. Drift detector invariants

`src/ikigai/tests/test_canonical_scope.py` — **8 test functions** (matches "8/8 PASS" claim in the roadmap; the count is correct even though the roadmap's grouping of them is not stated).

Scan scope (`:62-68`): `src/ikigai/src/{agents, mcp_server, ikigai/gateway, ikigai/cli, ikigai/adapters}`. Explicitly **excludes** `vibe-ops/` and `src/mesh/` (`:60-61`).

| # | Test (line) | Invariant |
|---|---|---|
| 1 | `test_no_forbidden_imports` (`:158`) | No production module imports the 8 deleted math/kernel paths in `FORBIDDEN_IMPORTS` (`:76-91`): `ikigai.core{,.scoring,.heuristics}`, `agents.ikigai_maintainer`, `src.agents.ikigai_maintainer`, `ikigai_scorer`, `cybernetics.daily_loop`, `vibe_ops.cybernetics.daily_loop` |
| 2 | `test_no_forbidden_function_calls_or_defs` (`:186`) | No def/call of the 15 `FORBIDDEN_FUNCTIONS` (`:94-113`) — `compute_meta_vector`, `compute_qhe`, `compute_score`, `compute_regime`, `compute_phase`, 5× `compute_*_score`, `compute_alignment_label`, `compute_weighted_priority`, `rank_tasks`, `classify_opportunity`, `apply_hysteresis` |
| 3 | `test_no_forbidden_class_references` (`:217`) | No ClassDef or Name reference to the 6 `FORBIDDEN_CLASSES` (`:116-125`): `IkigaiScorer`, `QHEScorer`, `PassionScorer`, `RegimeClassifier`, `PhaseDetector`, `VectorScorer` |
| 4 | `test_no_forbidden_mcp_tool_wrappers` (`:245`) | No `@MCP.tool(name=...)` registers a forbidden tool. ⚠️ **`FORBIDDEN_MCP_TOOLS` is an EMPTY frozenset** (`:131`) — this test is currently vacuous. Emptied in Phase 8.2 when 7 `ikigai_*` tools were re-registered as vault-reading observation wrappers (`:128-130`) |
| 5 | `test_ikigai_tools_count_is_12` (`:275`) | `IKIGAI_TOOLS` in `agents/tools.py` == exactly 12 entries; counts initial `= [...]` assignment plus `.extend([...])` calls (`:289-311`) |
| 6 | `test_ueid_canonical_regex_enforced` (`:324`) | `src/contracts/common.py` contains the **4-part** UEID pattern `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` (`:339`) |
| 7 | `test_fork_adapter_protocol_coverage` (`:347`) | Every `src/mesh/adapters/*.py` (excluding `base.py`, `__init__.py`, `a2ui_schema.py`) has a class defining `read`/`apply_change`/`supports_field` (`:359-363`) |
| 8 | `test_review_queue_append_only` (`:390`) | Only `queue.py` and `review_queue_worker.py` (allowlist `:410`) may pair `review_queue` mentions with write patterns `open(` / `.write_text(` / `.write_bytes(` (`:411-416`); plus `def enqueue` must exist in `queue.py` (`:443`) |

### 3a. Contradiction found — UEID 4-part vs 5-part

- Drift test #6 (`test_canonical_scope.py:337-344`) asserts the **4-part** regex is canonical and cites `ueid-5part-canonical-decision-2026-08-31` as its justification, with the docstring reading: *"a 5-part promotion was considered but the actual canonical regex … remains 4-part"*.
- `CLAUDE.md` states the opposite: *"UEID is the canonical join key … (5-part regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` per `ueid-5part-canonical-decision-2026-08-31`)"*.
- The memory `ueid-5part-canonical-decision-2026-08-31` title says *"5-part UEID promoted to canonical; 4-part deprecated alias"*.

Both cite the **same** decision record for opposite conclusions. The drift detector is currently pinning 4-part; CLAUDE.md and the memory say 5-part. One of the two is wrong and the detector will actively block a 5-part migration. **Needs adjudication.**

### 3b. Blind spots

- Invariant #4 is inert (empty forbidden set) — a re-added math tool would pass silently.
- No SONHO-tree invariants (d)/(e)/(h)/(i) exist despite Plan A/B/C claiming them (see §8).
- Detector never scans `interfaces/`, `src/mesh/` (for math), or `vibe-ops/`.

---

## 4. Test collection failure — root cause analysis

**Reported symptom:** `ModuleNotFoundError: No module named 'src.ikigai.src'` at collection of `tests/ikigai/agents/v2/`.

### Established facts

| Fact | Evidence |
|---|---|
| `src/__init__.py` **does not exist** | `ls` → No such file |
| `src/ikigai/__init__.py` **does not exist** | `ls` → No such file |
| `src/ikigai/src/__init__.py` **does not exist** | `ls` → No such file |
| `src/contracts/__init__.py` **does exist** | `ls` → 2275 bytes |
| `tests/__init__.py` **does not exist** | `ls` → No such file |
| `tests/ikigai/__init__.py` **does not exist** | `ls` → No such file |
| `tests/ikigai/agents/__init__.py` **does exist** (0 bytes) | `ls` |
| `tests/ikigai/agents/v2/__init__.py` **does exist** | `ls tests/ikigai/agents/v2/` |
| `pytest.ini` sets only `pythonpath = src` + `testpaths = tests`; **no `consider_namespace_packages`, no `importmode`** | `pytest.ini:1-3` (whole file) |
| v2 tests import via the dotted namespace chain | `tests/ikigai/agents/v2/test_commit_node.py:16-18` — `from src.ikigai.src.agents.v2.graph import NODES, make_v2_graph` |
| v2 production nodes also use the absolute dotted chain | `src/ikigai/src/agents/v2/nodes/commit.py:21-22` |

### Two independent defects

**Defect A — namespace-package resolution (primary, matches the reported error).**
`src.ikigai.src` is a 3-level *implicit namespace* chain (none of the three has `__init__.py`). pytest's default `prepend` import mode calls `insert_missing_modules()`, which fabricates placeholder `ModuleType` objects for absent parent modules. A fabricated `src` placeholder has **no `__path__`**, so the very next resolution step (`src.ikigai`) raises `ModuleNotFoundError: No module named 'src.ikigai.src'` — even though every sys.path entry is correct. pytest only walks real namespace portions when `consider_namespace_packages = true` is set; `pytest.ini:1-3` does not set it. This is exactly the failure the conftests are fighting: `tests/ikigai/conftest.py:13-17` explicitly names *"Windows + pytest 9.1.1 namespace packages"* as the blocker, and `tests/ikigai/agents/v2/conftest.py:9-13` was created solely as an ordering workaround. **sys.path was never the problem** — all three conftests add correct paths (`conftest.py:23-27`, `tests/conftest.py:10-24`, `tests/ikigai/agents/v2/conftest.py:28-39`), and the failure persists. That is the diagnostic signature of an import-mode/namespace issue rather than a path issue.

**Defect B — broken test package chain causing `agents` shadowing (latent).**
`tests/ikigai/agents/__init__.py` exists but `tests/ikigai/__init__.py` does not. Under `prepend` mode, pytest computes the basedir by walking up only while `__init__.py` is present, stopping at `tests/ikigai/`. It inserts `tests/ikigai/` at `sys.path[0]` and registers the test module as `agents.v2.test_commit_node`. This binds **`agents` → `tests/ikigai/agents`** in `sys.modules`, shadowing the real `src/ikigai/src/agents` package for any bare-`agents.*` import. `src/ikigai/src/agents/v2/graph.py:53-64` happens to use relative imports (`.nodes.*`), so v2 dodges this — but `test_canonical_scope.py:83` lists `agents.ikigai_maintainer` as a live bare-import path, confirming bare `agents.*` is a real style in this tree. This will bite as soon as any imported module uses it.

### Fix

1. Add to `pytest.ini`:
   ```
   consider_namespace_packages = true
   ```
   Optionally `importmode = importlib` (stronger, but requires all test module basenames be unique — several `conftest.py` and `test_*.py` names repeat across `tests/`, `src/ikigai/tests/`, and `interfaces/cli/tests/`, so verify before switching).
2. Normalize the `tests/` package chain — either add `tests/__init__.py` + `tests/ikigai/__init__.py`, **or** delete `tests/ikigai/agents/__init__.py` and `tests/ikigai/agents/v2/__init__.py`. Do not leave it mixed.
3. Once (1) lands, the three redundant conftest workarounds (`tests/ikigai/conftest.py`, `tests/ikigai/agents/v2/conftest.py` including its `pytest_load_initial_conftests` hooks and `DEBUG_CONFTEST` scaffolding at `conftest.py:21-23,40-50`) can be collapsed back to a single `tests/conftest.py`.

**Estimate:** 2–4 hours, not the 1 day allotted in roadmap task A.1 — *provided* Defect A is the real cause. The change to `pytest.ini` is one line; the bulk of the time is re-running the full suite and cleaning the conftest debris. If `consider_namespace_packages` does not resolve it, escalate to `importmode = importlib` + basename deduplication, which is the 1-day scope.

**Confidence:** high on the facts (all `ls`/Read verified), medium-high on Defect A being the operative cause — I could not run pytest to confirm, per constraint.

---

## 5. Vault templates status

`vault/ikigai/` contains **35 `.md` files** across 3 top-level dirs:

```
vault/ikigai/
├── closing-2026/
│   ├── 01-q3-2026/  {00-sonho, 01-plano-trimestral, 02-onda-{1,2,3},
│   │                 03-revisões-semanais, 04-relatórios-diários}
│   ├── 02-q4-2026/  {same 7 subdirs}
│   └── 99-archive/
├── meta/
└── mock-datasets/
```

### Tiers represented: **0 of 6**

The 6-level SONHO hierarchy (Sonho / Objetivo / Meta / Projeto / Entrega / Tarefa) shipped as Pydantic contracts in Plan A has **no corresponding vault templates**. What exists instead:

- `00-sonho/placeholder.md` in both quarters — placeholders, not templates. Their content is the *quarter-cycle* SONHO artifact concept, predating the 6-tier contract.
- The directory taxonomy is the **old** cycle vocabulary (sonho → plano-trimestral → onda → revisão semanal → relatório diário), which is orthogonal to the 6-tier contract hierarchy.
- The only real template-shaped file under `vault/` is `vault/evidence/agentic-md-1-quarterly-template.txt` — a `.txt`, in `evidence/`, unrelated to the 6 tiers.
- A repo-wide `find -iname "*template*"` returns hits only in `.github/`, `strategics/planning-with-files/` (vendored skill), `taskwarrior/config/`, and `vibe-ops/planning/` (`TEMPLATE-epic-sprint.md`, `TEMPLATE-micro-ciclo.md`, `TEMPLATE-weekly-review.md` — the old cycle vocabulary again). **Nothing under `vault/ikigai/`.**

**Contradiction:** the memory `plan-a-planning-contract-shipped-2026-09-03` claims *"+ 4 vault templates"* as part of Plan A's shipped scope. No such files are on disk on this branch. Either they were never written, were written outside `vault/`, or the memory over-claims. The roadmap (`roadmap-2026-09-04-harness-mvp.md:97`) independently contradicts the Plan A memory, listing *"vault/ templates seeded — 0 SONHOs.md in vault/"* as an open blocker (Task A.4). **The roadmap is correct; the Plan A memory over-claims.**

---

## 6. Incoming dependencies

Who depends on the components in this scope:

| Consumer | Depends on | Via |
|---|---|---|
| `python -m interfaces.cli` (user entry) | `interfaces/cli/__init__.py` → `read_tasks.app`, `server_app`, `v2_app` | `__init__.py:39-44` |
| Roadmap Task A.5 (CLI wrapper → graph.invoke) | `interfaces/cli/v2.py` `_run_cycle()` | `v2.py:54-66` — already exists; A.5 may be partially done |
| CI quality gate | `src/ikigai/tests/test_canonical_scope.py` | roadmap claims "CI green" |
| All v2 node tests | `tests/ikigai/agents/v2/conftest.py` | currently blocked |
| Operator TUI Tasks tab | `data/tasks.jsonl` (Deep Agent output) | `app.py:32` `TASKS_JSONL` |
| Operator TUI Queue tab | `data/review_queue/` | `app.py:37` `load_queue_rows` |
| Operator TUI Backend tab | pidfiles for `mcp_gateway`, `review_queue_worker` | `app.py:11-12` |

## 7. Outgoing dependencies

| Component | Depends on |
|---|---|
| `interfaces/cli/__init__.py` | sys.path injection of `<repo>` + `<repo>/src` **at import time** (`__init__.py:33-37`) — a fragile pattern documented at `:26-29` as required because pytest imports the package chain before conftest runs |
| `interfaces/cli/v2.py` | `src.ikigai.src.mcp_server.server._handle_ikigai_score` / `_handle_ikigai_regime`, `src.ikigai.src.agents.v2.graph.make_v2_graph` — all lazily imported inside `_load_handlers()` (`v2.py:35-51`) to defer the sys.path dependency |
| `interfaces/cli/read_tasks.py` | `src.contracts` (UEID), `src.mesh` adapters, `data/tasks.jsonl`, `data/feedback.jsonl` |
| `interfaces/tui/operator/app.py` | `textual` (App, Binding, DataTable, ModalScreen), `interfaces.tui.operator.data` (`:24-38`) |
| `test_canonical_scope.py` | stdlib `ast` + `pathlib` only — no imports of the code under test (pure AST scan). This is why it passes while the rest of the suite cannot collect. |
| v2 graph | `langgraph.checkpoint.sqlite.SqliteSaver`, `langgraph.graph.StateGraph` (`graph.py:20-21`) |

**Architectural note:** the drift detector's independence from the import graph is a genuine strength — it is the one green signal that survives the collection failure. It is also why "drift detector 8/8 PASS" cannot be read as evidence that anything else works.

---

## 8. Known gaps

| # | Gap | Severity | Evidence |
|---|---|---|---|
| G1 | Pytest collection broken for `tests/ikigai/agents/v2/` | **HIGH** — blocks roadmap A.1→A.6 entirely | §4 |
| G2 | Zero 6-tier vault templates; Plan A memory over-claims "4 vault templates" | **HIGH** — blocks A.4, B.3 | §5 |
| G3 | UEID 4-part (drift test) vs 5-part (CLAUDE.md + memory) contradiction, both citing the same decision record | **HIGH** — detector will block a 5-part migration | §3a |
| G4 | `FORBIDDEN_MCP_TOOLS` is empty → drift test #4 is vacuous | MEDIUM | `test_canonical_scope.py:131` |
| G5 | Drift invariants (d) SONHO-tree coverage, (e) actor-routing, (h) investigation queue, (i) external roots — all claimed by Plans A/B/C, **none present** in the detector (8 tests, none SONHO-related) | MEDIUM | full Read of detector |
| G6 | `tests/` package chain is mixed (`agents/__init__.py` without `ikigai/__init__.py`) → latent `agents` shadowing | MEDIUM | §4 Defect B |
| G7 | `life server start` / `stop` are STUBs | MEDIUM | `interfaces/cli/__init__.py:16` |
| G8 | `interfaces/cli/__init__.py` mutates `sys.path` at import time (`:33-37`); `v2.py` does it again (`:22-24`) — three overlapping path-fixup sites plus four conftests | MEDIUM — this is the accumulated scar tissue from G1 |
| G9 | TUI tab count documented as 3 in memory, is 4 in code; Tasks tab undocumented | LOW | §2 |
| G10 | `interfaces/cli/.venv/` is vendored inside the source tree | LOW — pollutes `find`/`grep`; risks accidental collection | `find` output |
| G11 | `DEBUG_CONFTEST` print scaffolding left in `tests/ikigai/agents/v2/conftest.py:21-23,40-50` | LOW | Read |

---

## 9. Verified claims

**28 claims verified by direct file inspection.** All line citations in this document were read, not inferred.

Highlights:
- 8 drift-detector tests enumerated by reading all 469 lines — count matches the "8/8" claim.
- 4 TUI tabs confirmed from both the module docstring and the `BINDINGS` list — **contradicts** the 3-tab memory claim.
- 8 `@app.command` + 5 `@server_app.command` + 3 v2 commands = 16 CLI commands confirmed by grep.
- Absence of `__init__.py` at `src/`, `src/ikigai/`, `src/ikigai/src/`, `tests/`, `tests/ikigai/` confirmed by `ls` (each returned "No such file").
- `pytest.ini` read in full (3 lines) — `consider_namespace_packages` and `importmode` confirmed absent.
- 0 six-tier vault templates confirmed by `find vault/ikigai -name "*.md"` (35 files, all old-vocabulary) plus a repo-wide `-iname "*template*"` sweep.

## 10. Unverifiable claims

| Claim | Why unverifiable |
|---|---|
| Exact pytest error text / traceback for the collection failure | pytest execution forbidden by constraint. Root cause in §4 is inferred from static evidence (missing `consider_namespace_packages` + 3-level namespace chain + conftest docstrings naming the exact symptom). Confidence medium-high, not certain. |
| "24/24 tests pass" (Phase 9 memory) | Cannot execute. Given G1, at minimum the v2 subset cannot currently collect. |
| "Drift detector 8/8 PASS" / "CI green" | Cannot execute. The detector is import-independent, so it *plausibly* still passes — but test #4 is vacuous and #6 may now conflict with the contracts (see G3). |
| Whether `consider_namespace_packages = true` alone fixes G1 | Requires a test run. |
| Whether `importmode = importlib` is viable | Requires checking for duplicate test-module basenames across `tests/`, `src/ikigai/tests/`, `interfaces/cli/tests/` — likely collisions (`conftest.py` repeats confirmed; `test_*.py` basenames not exhaustively compared). |
| Whether Plan A's "4 vault templates" exist outside `vault/` under a non-"template" name | Searched `-iname "*template*"` repo-wide and inspected all 35 `vault/ikigai/*.md`; nothing matched. Cannot rule out a differently-named file elsewhere. |
| Runtime behavior of the Operator TUI (does the Textual app actually launch) | Requires a TTY. |
