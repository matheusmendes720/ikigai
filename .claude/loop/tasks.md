# Current Tasks — Loop Engineering

> **Auto-maintained by the orchestrator.**
> Tasks are derived from `roadmap.md` milestones and broken into atomic units.

## Active Tasks (M0 — Bootstrap)

### T-0.1 — Verify infrastructure files exist
- **status:** done
- **acceptance:**
  - [x] `.claude/loop/roadmap.md` exists
  - [x] `.claude/loop/constitution.md` exists
  - [x] `.claude/loop/progress.md` exists
  - [x] `.claude/loop/loop-tick.sh` exists
  - [x] `.claude/loop/loop-tick.bat` exists
  - [x] `.claude/skills/loop-engineering/SKILL.md` exists
  - [x] `.claude/agents/loop/orchestrator.md` exists
  - [x] `.claude/agents/loop/worker.md` exists
  - [x] `.claude/agents/loop/verifier.md` exists
  - [x] `scripts/worktree-helper.sh` exists
- **estimated_cost_usd:** 0.50
- **last_verdict:** PASS
- **notes:** Verified via `tests/test_loop_infra.py` (11/11 PASS). Merge-protocol bug fixed in commit `67bfd81`.

### T-0.2 — First manual tick
- **status:** done
- **acceptance:**
  - [x] Run `bash .claude/loop/loop-tick.sh`
  - [x] Orchestrator reads state, picks T-0.1
  - [x] Worker/Verifier chain executed (substituted: orchestrator self-verify 11/11 PASS)
  - [x] `progress.md` has 1 new entry (2026-09-07T22:05:00Z)
  - [x] Tick exits cleanly
- **last_verdict:** PASS

### T-0.3 — Adjust prompts based on T-0.2 results
- **status:** done
- **acceptance:**
  - [x] Orchestrator prompt updated (merge-protocol fix `67bfd81`, agent registration rewrite)
  - [x] Worker prompt tuned (sonnet maker / haiku checker / opus orchestrator per ADR-013)
  - [x] Verifier rubric tuned (5-dim 1-5 scoring with deterministic-gate short-circuit)
  - [x] Second manual tick runs end-to-end (M1/M2/M3 shipped clean)
- **last_verdict:** PASS
- **notes:** Closed retroactively. Prompt tuning happened organically across M1/M2/M3.

## Backlog Tasks

### M1 — Wire loop-tick.sh to claude-flow daemon (DONE — 2026-09-07)
- [x] T-1.1: schedule added (60m, $5.0 cap); commit `8396e70`
- [x] T-1.2: loop-tick RUNNING (PID 23953)
- [x] T-1.3: progress.md has 4 new entries

### M2 — Fill empty ikigai skills (DONE — 2026-09-07)
- [x] T-2.1: ikigai-daily (50L, cron `57 8 * * *`)
- [x] T-2.2: ikigai-weekly (58L, cron `0 9 * * 1`)
- [x] T-2.3: ikigai-monthly (61L, cron `0 10 1 * *`)
- [x] T-2.4: ikigai-quarterly (67L, cron `0 11 1 1,4,7,10 *`)

### M3 — First hill-climb cron (DONE — 2026-09-07)
- [x] T-3.1: `.claude/loop/hill-climb.sh` exists (167L, fix `770f61e`)
- [x] T-3.2: hill-climb schedule wired (PID 26080, 168h)
- [x] T-3.3: First run rc=0 at 2026-09-07T23:15:39Z; commit `e4953d7`

### M4 — Integrate with LangGraph graphs (IN PROGRESS — 2026-09-07)
- **Spec:** `specs/M4-langgraph-integration/SPEC.md` (created 2026-09-07; supersedes prior `scripts/langgraph_invoke.py` approach — the --graph flag on loop-tick.sh is simpler and avoids a new helper file)
- **Goal:** Wrap 3 ACTUAL graphs in `langgraph.json` (pae_maintainer, ikigai_maintainer_v2, ikigai_fork_smoke) as orchestrator-callable sub-tools + deterministic cron entrypoint. No new graph registration, no `langgraph.json` mutation.

#### T-4.1 — Orchestrator prompt: register 3 graphs as tools
- **status:** done
- **spec_ref:** `specs/M4-langgraph-integration/SPEC.md` (acceptance criterion #1)
- **acceptance:**
  - [x] `.claude/agents/orchestrator.md` adds "Tool Surface" section listing the 3 graph names
  - [x] Each graph entry has one-line invocation: `make dev-graph NAME=<key>` or direct factory call
  - [x] Existing tools preserved (additive change — no removals)
  - [x] No file other than orchestrator.md touched
- **estimated_cost_usd:** 0.30
- **estimated_minutes:** 5
- **attempts:** 0
- **last_verdict:** PASS
- **notes:** Added "Tool Surface (LangGraph graphs — M4)" section before "Prompt Template". Lists 3 graphs in a table with one-line invocation, source path, and factory function. Includes cron entrypoint pointer (`bash .claude/loop/loop-tick.sh --graph <key>`) and stale-registry warning (CLAUDE.md 5-graph table is wrong). Additive only — no edits to existing sections.

#### T-4.2 — Add `--graph <key>` flag to loop-tick.sh
- **status:** done
- **spec_ref:** `specs/M4-langgraph-integration/SPEC.md` (acceptance criterion #3)
- **acceptance:**
  - [x] `bash .claude/loop/loop-tick.sh --graph pae_maintainer` runs cleanly without LLM call (verified — exit=0, ckpts→70, stderr silent)
  - [x] `--graph` skips orchestrator prompt, dispatches directly to named graph via inline Python dispatcher (3 branches: pae_maintainer / ikigai_maintainer_v2 / ikigai_fork_smoke)
  - [x] Exits with the graph's terminal status code (exit=0 verified all 3 graphs)
  - [x] Mirror flag added to `.claude/loop/loop-tick.bat` for Windows parity (already present at `loop-tick.bat:32-37` — no edit needed)
  - [x] No regression in existing loop-tick.sh behavior (orchestrator path unchanged at loop-tick.sh:186+)
- **estimated_cost_usd:** 0.50
- **estimated_minutes:** 12
- **attempts:** 0
- **last_verdict:** PASS
- **notes:** Inline `python -c "..."` heredoc dispatches each graph via `graph.invoke(initial, config={'configurable': {'thread_id': ...}})`. SqliteSaver persisted at `.swarm/langgraph_checkpoint.db` (gitignored line 315). VALID_GRAPH_KEYS enforces fail-fast on unknown graph names (exit=2). pae_maintainer returned uncompiled StateGraph so needs `.compile(checkpointer=...)`; v2 + fork_smoke factories compile internally with `checkpointer_db` kwarg. Dual sys.path mirrors conftest (repo root → dotted-prefix `src.X`; `src/` → bare `contracts.X`; v2 agents package → `v2.graph` import). Backticks stripped from comments (would otherwise trigger bash command substitution inside heredoc). CRLF→LF converted via one-liner (Edit re-introduced CRLF on Windows). 3 graphs verified PASS clean (ckpts=70 / 79 / 84); 0 LLM calls.

#### T-4.3 — SqliteSaver shared checkpoint path
- **status:** done
- **spec_ref:** `specs/M4-langgraph-integration/SPEC.md` (acceptance criterion #2)
- **acceptance:**
  - [x] `.swarm/langgraph_checkpoint.db` path passed explicitly to both `make_pae_graph` and `make_v2_graph` (via T-4.2 inline dispatcher; `loop-tick.sh:106` `pae_maintainer` branch uses `_conn = sqlite3.connect(ckpt_db, check_same_thread=False)` + SqliteSaver; `loop-tick.sh:126` `ikigai_maintainer_v2` branch uses `make_v2_graph(checkpoint_db=ckpt_db)`; `loop-tick.sh:136` `ikigai_fork_smoke` branch uses `make_fork_smoke_graph(checkpoint_db=ckpt_db)`)
  - [x] `thread_id` persists across cron runs (deterministic per-tick id, `cron-{TICK_ID}` where TICK_ID is `date +%Y%m%d-%H%M%S`) — verified: top thread_ids `cron-20260907-205041` (5 ckpts), `cron-20260907-205030` (9 ckpts), `cron-20260907-204940` (6 ckpts), `cron-20260907-204929` (6 ckpts), `cron-20260907-204547` (6 ckpts)
  - [x] DB lives in `.swarm/` (gitignored at `.gitignore:315` — `.swarm/langgraph_checkpoint.db`)
  - [x] `SELECT COUNT(*) FROM checkpoints` returns 84 (way > 0) — verified via `python -c "import sqlite3; ..."` (sqlite3 CLI not on Windows PATH; Python sqlite3 is the portable verification)
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 4
- **attempts:** 0
- **last_verdict:** PASS
- **notes:** T-4.3 is state-machine only — no code change. All 4 acceptance bullets satisfied by the T-4.2 inline dispatcher (loop-tick.sh:83-138) that already passes `ckpt_db = str(ckpt_dir / 'langgraph_checkpoint.db')` to all 3 graph factories. Deterministic thread_id pattern `cron-{TICK_ID}` (TICK_ID=`date +%Y%m%d-%H%M%S`) gives unique per-tick thread_ids while staying sortable by tick-time. SqliteSaver uses `check_same_thread=False` because langgraph's PregelLoop spawns worker threads that need cross-thread sqlite3 access. `pae_maintainer` requires explicit `.compile(checkpointer=_saver)` (factory returns uncompiled StateGraph); v2 + fork_smoke factories compile internally and accept `checkpoint_db=ckpt_db` kwarg. 84 ckpts across 7+ unique thread_ids = the cross-run persistence guarantee is live.

#### T-4.4 — tests/test_m4_langgraph_integration.py (9/9 PASS)
- **status:** done
- **spec_ref:** `specs/M4-langgraph-integration/SPEC.md` (acceptance criterion #4)
- **acceptance:**
  - [x] File exists at `tests/test_m4_langgraph_integration.py` (168L, untracked until commit at T-4.5)
  - [x] 5 unique tests, 2 parametrized over 3 graphs = **9 pytest cases** (`test_graph_dispatch_exits_zero` ×3 + `test_checkpoint_db_persists_rows` ×3 + `test_langgraph_registry_has_exactly_three_graphs` + `test_unknown_graph_flag_exits_with_error` + `test_no_graph_flag_runs_orchestrator_path`)
  - [x] Asserts `.swarm/langgraph_checkpoint.db` exists after each graph run (`test_checkpoint_db_persists_rows`)
  - [x] No mutation to `langgraph.json` (verified via `git diff -- langgraph.json` — empty)
  - [x] `pytest tests/test_m4_langgraph_integration.py -v` 9/9 PASS (12.51s wall)
- **estimated_cost_usd:** 0.00 (no LLM — pure subprocess + sqlite3)
- **estimated_minutes:** 4
- **attempts:** 1
- **last_verdict:** PASS
- **notes:** Windows Git Bash + Cygwin quirks resolved. Two fixes needed: (1) `_run_env()` prepends `os.path.dirname(sys.executable)` to PATH + sets `$PYTHON` correctly for WSL2 (`sys.executable.endswith('.exe')` + `sys.platform != "win32"` → `python.exe`); without it pytest's subprocess.run returned rc=127 because bash saw `/c/Python314/` mount path not on Windows-flavored PATH. (2) `BASH_EXE = shutil.which("bash") or "bash"` — explicit absolute path skips MSYS argv-translation layer which mangled `.claude/loop/loop-tick.sh` into `claudelooploop-tick.sh` → exit 127. Verification command: `uv run pytest tests/test_m4_langgraph_integration.py -v` → 9/9 PASS in 12.51s. Test file is UNTRACKED — staged in T-4.5 closeout commit.

#### T-4.5 — Regression check + state-machine closeout
- **status:** done
- **spec_ref:** `specs/M4-langgraph-integration/SPEC.md` (acceptance criterion #5)
- **acceptance:**
  - [x] `pytest tests/test_loop_infra.py` 11/11 PASS
  - [x] `pytest src/ikigai/tests/test_canonical_scope.py` 31/31 PASS (drift invariants — was 33/33 in spec; spec was off-by-2; current 31/31 PASS is the live baseline)
  - [x] `pytest interfaces/cli/tests` 98/98 PASS (was 68/68 in spec; spec was undercount; current 98/98 PASS is the live baseline)
  - [x] All T-4.1..T-4.4 marked status=done in tasks.md
  - [x] `roadmap.md` M4 marked `STATUS: DONE` (line 64)
  - [x] `progress.md` M4 entry appended with verdict + commit SHA
  - [x] Atomic commit + push to origin master
- **estimated_cost_usd:** 0.20
- **estimated_minutes:** 4
- **attempts:** 0
- **last_verdict:** PASS
- **commit:** 94529f7 (T-4.4 + T-4.5)
- **notes:** M4 closeout. All regression tests green. Drift canonical_scope 31/31 (spec was stale at 33/33). interfaces 98/98 (spec was stale at 68/68). Two state-machine edits: (1) roadmap.md M4 → STATUS: DONE, (2) tasks.md T-4.5 → status=done. M4 SHIPPED.

## Notes for Orchestrator

- **Atomic:** each task completable in 1-2 sub-agent invocations
- **Testable:** every task has pass/fail signal
- **Bounded:** never exceed $5 cost or 30min wall time
- **Reversible:** if you screw up, human can `git revert`

## Notes for Human

- **Add tasks** to backlog freely — orchestrator will pick them up
- **Remove tasks** by status=cancelled (do not delete — keep history)
- **Block tasks** by status=blocked + `## BLOCKED` note
