---
name: M169-paperclip
description: Paperclip meta-orchestrator graph — spec to HIL pause to worktree to agent to merge. Fourth graph in langgraph.json.
status: DONE
owner: matheus-mendes
created: 2026-10-11
constitution_refs:
  - tests_are_the_contract
  - state_on_disk_not_conversation
  - reversibility_over_cleverness
  - composition_over_inheritance
  - multi_package_boundaries_are_sacred
estimated_cost_usd: 0.00
---

# M169 — Paperclip meta-orchestrator (MVP)

**Status:** 🟢 DONE (MVP)
**Date:** 2026-10-11
**Author:** matheus-mendes (with Claude Code assist)
**Plan file:** `C:\Users\mathe\.claude\plans\vivid-giggling-locket.md`

---

## TL;DR

Paperclip is the **fourth LangGraph graph** in `life-oss/life`, registered
in `langgraph.json` as `ikigai_paperclip`. It turns a software-company
abstraction into an executable graph:

```
read_spec  ─▶ spec_analyzer ─▶ (gaps? yes) hil_pause ─▶ merge_user_resolution ─▶ spec_analyzer
                         └─▶ (gaps? no)  worktree_create ─▶ implement ─▶ (tests? ok) worktree_commit
                                                                              └▶ (fail) implement
                                                                 worktree_merge ─▶ worktree_cleanup ─▶ END
```

Auto-throttle, GitBucket PR sync, TUI surface, and fan-out are explicitly
**deferred** to Waves N+1 through N+5.

---

## What changed

```
src/ikigai/src/agents/paperclip/             # NEW
├── __init__.py                              # package marker + version
├── state.py                                 # PaperclipStateDict (TypedDict, all NotRequired)
├── graph.py                                 # make_paperclip_graph + _build_paperclip_graph
├── nodes/
│   ├── __init__.py
│   ├── read_spec.py                         # validate task_id + spec_text
│   ├── spec_analyzer.py                     # Claude subprocess → spec_gaps (cap MAX_GAP_LOOPS=5)
│   ├── hil_pause.py                         # langgraph_sdk.interrupt() (NEW in repo)
│   ├── worktree.py                          # create/commit/merge/cleanup via scripts/worktree-helper.sh
│   └── implement.py                         # ClaudeAdapter.run() + best-effort pytest (cap MAX_IMPLEMENT_ITERS=3)
├── agents/
│   ├── __init__.py                          # exports AgentAdapter Protocol + AgentResult model
│   ├── base.py                              # Protocol + Pydantic v2 strict BaseModel
│   ├── claude.py                            # REAL adapter — subprocess to `claude` CLI
│   ├── pi.py                                # STUB — NotImplementedError
│   ├── mcode.py                             # STUB
│   ├── omo.py                               # STUB
│   ├── hermes.py                            # STUB
│   └── openclaw.py                          # STUB
└── tests/
    ├── __init__.py
    ├── test_graph_smoke.py                  # 5 tests: compiles, factory sig, state schema, protocol, imports
    └── test_hil_pause.py                    # 12 tests: JSON gap parsing, interrupt payload, merge logic, cap

src/ikigai/tests/test_paperclip_drift.py     # NEW — 2 drift-net invariants
specs/M169-paperclip/SPEC.md                 # this file
langgraph.json                               # 1-line edit: add ikigai_paperclip entry
```

**Total: ~13 new files, 1-line langgraph.json edit, ~1,150 LOC.**

---

## Architecture decisions

### Why a fourth graph (not a new feature on v2)

`ikigai_maintainer_v2` reasons about **planning** (it does NOT write code
to the repo — that's the v2 graph's discipline per ADR-013 planner-only
scope). `ikigai_taskdog_mcp` executes **taskdog tasks**. Paperclip
operates on **specs**: read one, get clarity via HIL, create a worktree,
invoke an AI agent, merge back. It's a distinct lane.

### Why `langgraph_sdk.interrupt()` (not kill_switch)

`kill_switch` is the only existing pause mechanism in the repo
(`sys_ikigai/security/kill_switch.py`) but it's a **binary abort** —
there is no mechanism to capture and respond to user input. Paperclip
introduces the first true HIL pattern. The fallback when
`langgraph_sdk` isn't installed is a `RuntimeError` carrying the
payload as JSON — a harness can catch it and serialise/resume.

### Why subprocess (not MCP) for the Claude adapter

Per the user's answer in plan phase: "Path 1 style (recommended)".
Mirrors `run_taskdog` (`src/ikigai/tools/vault_taskdog_sync.py:61-75`):
`subprocess.run(["claude", prompt], cwd=worktree, capture_output=True,
text=True, timeout=180, env=...)`. The JSON-RPC-framed `StdioAdapter`
in `sys_ikigai/gateway/stdio_adapter.py` is reserved for binary MCP
servers — `claude` CLI is one-shot text-in/text-out so the simpler
wrapper suffices.

### Why `AgentAdapter` Protocol (mirrors `ForkAdapter`)

Same shape as `ForkAdapter` in `src/mesh/adapters/`. Each adapter is
just `name` + `timeout_s` + `run(prompt, cwd, *, timeout_s) -> AgentResult`.
Result is a frozen Pydantic v2 model (`frozen=True, extra="forbid"`)
per the project-wide invariant in `CLAUDE.md`.

### Adapter shipping status (2026-10-11)

| Adapter | MVP (M169) | Wave N+1 (M170-M173) | Notes |
|---------|-----------|---------------------|-------|
| `claude.py` | ✅ real | ✅ real | 109 LOC, `claude <prompt>` positional |
| `pi.py` | stub | ✅ real (M170) | 109 LOC, `pi <prompt>` positional |
| `omo.py` | stub | ✅ real (M171) | 108 LOC, omo is fork of Pi |
| `openclaw.py` | stub | ✅ real (M172) | 123 LOC, subcommand `agent --local --no-color --message <prompt>` |
| `mcode.py` | stub | stub | `mmx-cli` skill loaded but no binary on machine |
| `hermes.py` | stub | stub | Binary not on PATH; listed in N+2 wave |

The drift invariant `test_paperclip_agents_have_adapters` checks presence
+ parseability of all 6 files — stubs satisfy the contract by existing;
real adapters satisfy it by working.

---

## Verification

```bash
# 1. Drift net — must show 70/70 (was 68)
uv run pytest src/ikigai/tests/test_paperclip_drift.py src/ikigai/tests/test_drift_invariants.py src/ikigai/tests/test_drift_extended_invariants.py src/ikigai/tests/test_canonical_scope.py -v
# Expected: 70 passed (2 new + 68 preserved)

# 2. Smoke tests — graph compiles, factory signature, state schema, protocol
uv run pytest src/ikigai/src/agents/paperclip/tests/test_graph_smoke.py -v
# Expected: 5 passed

# 3. HIL flow tests — JSON gap parsing, interrupt payload, merge logic, cap
uv run pytest src/ikigai/src/agents/paperclip/tests/test_hil_pause.py -v
# Expected: 12 passed

# 4. langgraph.json validates
python -c "import json; print(json.load(open('langgraph.json'))['graphs']['ikigai_paperclip'])"
# Expected: ./src/ikigai/src/agents/paperclip/graph.py:make_paperclip_graph
```

(All 4 verifications were run during implementation; results logged in
`MEMORY.md` under the M169 entry.)

---

## Acceptance

- [x] `ikigai_paperclip` registered in `langgraph.json` (4th graph)
- [x] 9-node StateGraph: read_spec, spec_analyzer, hil_pause, merge_user_resolution, worktree_create, implement, worktree_commit, worktree_merge, worktree_cleanup
- [x] `_safe_node` wrapper mirrors v2/graph.py:88-109
- [x] 2-arg `make_paperclip_graph(runtime, config)` signature (M102 mandate)
- [x] `SqliteSaver` checkpointer (data/paperclip.db default)
- [x] 6 agent adapters declared (1 real + 5 stubs); drift test enforces presence
- [x] `PaperclipStateDict` — all fields `NotRequired`, `messages` carries the `Annotated[list, operator.add]` reducer (OPEN-3 lesson)
- [x] `AgentAdapter` Protocol + `AgentResult` Pydantic v2 strict (frozen, extra=forbid)
- [x] `interrupt()`-based HIL pause (first in repo)
- [x] Worktree nodes wrap `scripts/worktree-helper.sh` (M24.1 Windows-safe)
- [x] Drift net: **68 → 70** (`+2` new invariants)
- [x] Smoke tests: **5/5 PASS**
- [x] HIL tests: **12/12 PASS**

---

## Lessons

1. **Two iteration counters are better than one.** First pass conflated
   `gap_iteration` (spec_analyzer cap) and `implement_iteration`
   (implement cap) — fixed by adding `gap_iteration` to
   `PaperclipStateDict`. State field naming should reflect which loop it
   guards.

2. **TypedDict undeclared keys are silently filtered.** `implement_node`
   initially returned `_tests_ok` (undeclared) — LangGraph's state
   schema filtered it. Fix: declare every returned key in the
   TypedDict, or use a `_`-stripped public name. We chose the latter:
   `tests_ok: NotRequired[bool]`.

3. **HIL fallback matters.** `langgraph_sdk.interrupt` may not be
   installed in every test env. The `_interrupt` helper raises
   `RuntimeError("PAPERCLIP_HIL_PAUSE: {json}")` as a graceful
   fallback — a harness can catch it and serialise/resume.

4. **Drift test = +1 per `def test_*` function.** No `pytester.runpytest`
   trick. Two new functions (`test_paperclip_graph_registered`,
   `test_paperclip_agents_have_adapters`) → drift count 68 → 70.

---

## Deferred (future waves)

| Wave | Adds | Drift count |
|------|------|-------------|
| **M169 (this)** | Claude Code adapter + SSD loop + HIL + worktree | 70/70 |
| ~~N+1~~ | **SHIPPED 2026-10-11** — M170 Pi + M171 omo + M172 OpenClaw real adapters; M173 cost gate | 70/70 |
| ~~N+2~~ | **SHIPPED 2026-10-11/12** — M175 wall-clock gate + M176 risk gate; M178 MSYS path fix; M180 HIL resume; M183 state persistence | 74/74 |
| ~~N+3~~ | **SHIPPED 2026-10-12** as M174 — self-managed auto-spawner (inbox → Paperclip → adapter router); 6th daemon in the loop fleet | 72/72 |
| ~~N+5 fanout~~ | **SHIPPED 2026-10-12** — 4 parallel subagents (M190 canonical HTTP adapter, M191 Dynamic Workflows skeleton = 5th LangGraph graph `ikigai_dynamic`, M192 ADR-036 4 nested loops, M193 8-stacks comparison matrix) + wbcf3izew M178/M180/M183 | 79/79 |
| N+6 | GitBucket PR sync (resurrect M185); TUI 6th tab; ntfy.sh pause notifications; real-LLM wiring for paperclip_dynamic | 81/81 |
| ~~N+3~~ | **SHIPPED 2026-10-11** as M174 — self-managed auto-spawner (inbox → Paperclip → adapter router); 6th daemon in the loop fleet | 72/72 |
| ~~N+4 partial~~ | **SHIPPED 2026-10-11** as M175 — wall-clock gate (`WallClockGate` fail-open, default 3600s = 1h, env `PAPERCLIP_WALL_CLOCK_THRESHOLD_S`); wired into implement.py AFTER cost gate | 73/73 |
| ~~N+2 risk gate~~ | **SHIPPED 2026-10-11** as M176 — `RiskGate` fail-CLOSED on 18 dangerous keywords (rm -rf, drop database, git push --force, .env, secrets, etc.); wired into implement.py AFTER wall-clock, BEFORE adapter; env override `PAPERCLIP_RISK_KEYWORDS`. **First fail-CLOSED gate.** | 74/74 |
| N+4 remaining | GitBucket PR sync; TUI 6th tab; ntfy.sh pause notifications | 76/76 |
| N+4 | TUI 6th tab; ntfy.sh pause notifications | 76/76 |
| N+5 | Multi-graph fan-out (one spec → many parallel Paperclip runs) | 78/78 |

---

## Critical risks (mitigations in place)

| Risk | Mitigation |
|------|-----------|
| `interrupt()` API instability | `try/except ImportError` fallback raises `RuntimeError` with payload |
| Subprocess hang | Hard `timeout=180s` in ClaudeAdapter + TODO daemon-watchdog hookup (M39) |
| Worktree cleanup on crash | Orphan-GC via `scripts/worktree-helper.sh cleanup-all` |
| Spec ambiguity loop | `MAX_GAP_LOOPS=5` cap in spec_analyzer; `MAX_IMPLEMENT_ITERS=3` cap in implement |
| Merge conflict | `error_type=MergeConflictError` — explicit HIL resolution (Wave N+3 candidates) |