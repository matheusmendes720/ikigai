# 01 — Verified Inventory (8 Items)

**Source:** `docs/diagnostics/2026-08-28-ultracode-verified.md` §1
**Verdict scale:** ✅ CONFIRMED | ⚠️ PLAUSIBLE | ❌ FALSE
**Notation note:** "Fix category" describes WHAT KIND of fix would address the issue. Per Q2 scope (audit + open questions only), NO PATCHES are executed in this report. These are descriptive labels for Phase 3 context.

---

## B-01 — mcp-gateway STALE cwd paths

- **Claim:** `apps/mcp-gateway/config/gateways.yaml` cwd paths reference non-existent directories
- **Verdict:** ✅ **CONFIRMED**
- **Evidence:** `apps/mcp-gateway/config/gateways.yaml:4,9,14` — `C:/Users/mathe/code_space/apps/kanban/tuiboard`, `apps/dev-tools/taskdog`, `apps/calendar/solverforge-calendar` (all MISSING)
- **Correction:** Gateway lives at `C:\Users\mathe\code_space\apps\mcp-gateway\` — sibling of `life-oss/`, NOT inside `life/`
- **Fix category** (not executed): repoint 3 cwd paths to `life-oss/interfaces/...`

## B-02 — `langgraph_entry.py:27` broken IKIGAI_SRC path

- **Claim:** `IKIGAI_SRC = Path(__file__).parent.parent.parent / "life-ops" / "ikigai" / "src"` references deleted `life-ops/`
- **Verdict:** ✅ **CONFIRMED**
- **Evidence:** `vibe-ops/src/langgraph_entry.py:25-27` (3 path constants); `langgraph.json:6` wires this graph
- **Fix category:** fix path resolution (3-line edit)

## B-03 — PAV `__main__.py:9` broken import

- **Claim:** `from operational.cli.app import app` — `operational.cli` package was deleted
- **Verdict:** ✅ **CONFIRMED**
- **Evidence:** `src/operational/packages/core/src/operational/__main__.py:9`; `__init__.py:358` lists `"cli_app"` in `__all__` (no import statement); `verify_sprint.py:224-233` spawns `python -m operational.cli.app --help` as subprocess
- **Audit correction:** Audit path was off by 1 level. File is at `src/operational/packages/core/src/operational/__main__.py`, not `operational/packages/core/src/operational/__main__.py`
- **PAV cli/tui deletion context:** per memory `[[pav-cli-tui-future-feature-2026-08-27]]`, PAV CLI/TUI deprecated 2026-08-26 — orphan import refs not cleaned
- **Fix category:** delete `__main__.py` or point at real entry; drop dangling `"cli_app"` from `__init__.py:358` `__all__`

## B-04 — `tasks.jsonl` MISSING

- **Claim:** `data/tasks.jsonl` does not exist; CLI `interfaces/cli/read_tasks.py:27-29` returns `[]`
- **Verdict:** ✅ **CONFIRMED**
- **Audit correction:** Producer EXISTS (`vibe-ops/src/pipeline/daily_consolidator.py`, 327-408 lines, supports `--dry-run`) but was never invoked. Audit's "(no producer)" is imprecise; real cause is "producer never invoked"
- **Fix category:** invoke producer OR retire consumer (open question for Phase 3)

## B-05 — `vibe_ops.db` 0 rows

- **Claim:** 19 tables, all empty
- **Verdict:** ✅ **CONFIRMED**
- **Evidence:** `data/vibe_ops.db` (143,360 B), last written 2026-06-03
- **Audit corrections:**
  - `PRAGMA user_version` returns 0 (not 4 — schema v4 was audit inference)
  - Code opens CWD-relative `./vibe_ops.db` (not `data/`)
  - `pae_maintainer` references non-existent tables `pae_state`, `period_reports`
- **Fix category:** seed sensor (P3 priority); also fix path resolution (P1)

## B-06 — 4 LangGraph stub dispatchers

- **Claim:** `langgraph_entry.py:189,193,197,201` — 3-lambda shells dispatching to non-existent YAML workflows
- **Verdict:** ✅ **CONFIRMED**
- **More severe than audit claim:** Stubs CRASH on invocation. `langgraph_entry.py:159-167 _load_workflow_yaml` builds path `Path(__file__).parent / ".claude" / "skills" / "quarterly-planner" / "workflows"` which resolves to `vibe-ops/src/.claude/skills/...` — DOES NOT EXIST. Workflows live at `<root>/.claude/skills/quarterly-planner/workflows/`. `FileNotFoundError` before lambdas run.
- **Affected graphs:** `quarterly_replan`, `test_de_fogo_rollup`, `correction_protocol`, `dream_falsification`
- **Fix category:** decision-gated (implement or deregister) — see `04-sequencing.md` Step 7

## B-07 — dual PolicyEngine wired in parallel

- **Claim:** `daily_loop.py:4,7` imports TWO PolicyEngines in parallel
- **Verdict:** ❌ **FALSE**
- **Misidentification:** `vibe-ops/src/schemas/pydantic_v2.py` is 48 lines of Pydantic models (`PolicyState` enum, `PolicyDecision` BaseModel) — DATA MODELS, not engines. daily_loop wires ONE engine.
- **Stub state:** `pipeline/policy_engine.py:5` (118 lines) is DEAD CODE — only referenced by `main.py:86` unused import + `scratch/test_policy.py:1`
- **REAL bug found (more severe than audit claim):** canonical `evaluate()` signature mismatch with `daily_loop.py:33` call site
  - Canonical signature: `evaluate(self, qhe_metrics: QHEMetrics, infraction_count: int = 0, energy_level: EnergyLevel | None = None, on_date: date | None = None)`
  - Call site passes: `dict` for `QHEMetrics`, `PolicyDecision` for `int`, `date` for `EnergyLevel`
  - Result: type drift, possible silent wrong-decision (depends on positional arg interpretation)
- **Fix category:** signature alignment + collapse stub into canonical (P5 priority, gated by P2)

## B-08 — 1137-line orphan test file

- **Claim:** `tests/core/test_services.py` is 1137 lines, references deleted modules
- **Verdict:** ✅ **CONFIRMED**
- **Audit correction:** file is 942 lines (not 1137)
- **Evidence:** imports `operational.cli.services` and `operational.cli.state` (both DO NOT EXIST); cannot be collected by pytest
- **Secondary orphan:** `tests/e2e/test_cli_workflow.py` (66 lines) — also imports `operational.cli.app`
- **Empty/orphan directories:** `tests/{tui,ui,property}/` and `tests/unit/cli/` (empty)
- **Fix category:** delete or xfail 2 orphan test files; remove empty dirs

---

## Summary

| Verdict | Count | Items |
|---------|-------|-------|
| ✅ CONFIRMED | 7 | B-01, B-02, B-03, B-04, B-05, B-06, B-08 |
| ❌ FALSE | 1 | B-07 (audit misidentification; real bug found is more severe) |

**Audit corrections:** 3 items (B-04 producer nuance, B-05 user_version=0 not 4, B-08 line count 942 not 1137)
**Real bugs found beyond audit:** B-07 evaluate() signature drift, B-06 stubs CRASH (not "do nothing")