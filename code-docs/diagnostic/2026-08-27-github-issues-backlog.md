> **[SUPERSEDED 2026-08-28 — see master-branch-carro-chefe-2026-08-28]**
> Pre-pivot backlog organized around IKIGAI / PAV / Observability sprint
> (16 issues, ~24.5d, Q1-Q4 risk). Many issues are reframed under deep-agent
> canonical; IKIGAI feature work is paused per ADR-007 (5+ SONHO logs gate).
> For current sprint sequencing, see the doc-migration plan.

# GitHub Issues Backlog — IKIGAI / PAV / Observability Sprint

> **Date:** 2026-08-27
> **Source-of-truth:** `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` (77+ issues across §1-§5) + `life-ops/ikigai/docs/IKIGAI_BACKEND_DEEP_DIVE_REPORT.md` (19 issues, all folded into §1).
> **Risk legend (Q1-Q4):** Q1 = high risk + high effort · Q2 = high risk + low effort · Q3 = low risk + high effort · Q4 = low risk + low effort.
> **Original prefixes** (C1-C5, S-H1, P1) are preserved inside each issue body for traceability to source docs.
> **Renumbering** is GitHub-friendly (IKIGAI-001, DOCS-001, PAV-001, …).

---

## §0 Sumário — 80 issues, by milestone

| Milestone | Count | Critical | High | Medium | Info | Effort (d) | Goal |
|-----------|------:|---------:|-----:|-------:|-----:|-----------:|------|
| **Sprint 1 — System Boot** | 16 | 8 | 8 | 0 | 0 | ~24.5d | Unblock boot, restore CLI, fix critical bugs |
| **Sprint 2 — Functional Correctness** | 12 | 0 | 4 | 7 | 1 | ~10.5d | Smaller bug fixes; complete functional surface |
| **Sprint 3 — Reliability + Observability** | 13 | 0 | 9 | 4 | 0 | ~16.0d | OpenTelemetry dual-export, retry/CB, HITL |
| **Sprint 4 — HITL + Advanced** | 25 | 0 | 6 | 9 | 10 | ~28.0d | Tests, refactors, advanced features |
| **Backlog** | 14 | 0 | 4 | 9 | 1 | ~16.5d | Cross-cutting, long-tail, deferred |
| **Total** | **80** | **8** | **31** | **29** | **12** | **~95.5d** | — |

### By subsystem
- **ikigai** (core): 39 (IKIGAI-001..039) — primary dev surface
- **pav**: 8 (PAV-001..008) — `life-ops/operational/` workspace
- **docs**: 6 (DOCS-001..006) — ADR discovery, index hygiene
- **ci**: 4 (CI-001..004) — pipeline + status checks
- **mcp-tuiboard**: 6 (TUIBOARD-001..006) — Rust/TS kanban
- **mcp-taskdog**: 4 (TASKDOG-001..004) — Python HTTP server
- **mcp-solverforge**: 5 (SOLVERFORGE-001..005) — Rust calendar
- **vibe-ops**: 2 (VIBEOPS-001..002) — conceptual + spec migrations
- **test**: 1 (TEST-001) — coverage ramp
- **refactor**: 2 (REFACTOR-001..002) — workspace hygiene
- **feature** (cross-cutting): 3 (FEAT-001..003) — pending constructions

### Severity distribution
- **critical** (8): all in Sprint 1 — block system boot or produce silent data loss
- **high** (31): functional correctness + observability gaps that surface to user
- **medium** (29): polish + refactors + test scaffolding
- **info** (12): docs + UX + worktree hygiene

---

## §1 Milestone: Sprint 1 — System Boot (16 issues, ~24.5d)

> **Goal:** the system boots end-to-end (`ikigai.bat mcp` → `tools/list` round-trip, PAV CLI responds). All critical/high bugs that block boot or produce silent data loss are closed.
> **Gate:** `uv run pytest -m "not e2e"` green, `ikigai.bat` exits 0, MCP server reachable from Claude Code registry.

### ISSUE-001: Replace hardcoded `/tmp/ikigai-test/bin/python` with `poetry run python`
**Labels:** severity:critical, subsystem:ikigai, type:bug, estimate:0.5d, risk:Q2
**Milestone:** Sprint 1
**Files:** `life-ops/ikigai/mcp_config.json:4`, `life-ops/ikigai/start_mcp_gateway.sh:35`
**Description:** The MCP gateway and `mcp_config.json` both point at a venv that never exists, so the IKIGAI server cannot start from either entry path. The literal `/tmp/ikigai-test/bin/python` is a leftover from a throwaway local test scaffold.
**Acceptance:**
- `ikigai.bat mcp` boots and connects to the MCP registry (`dcode` can list tools)
- `mcp_config.json` references `poetry run python` (or a checked-in `.venv` path)
- `start_mcp_gateway.sh` honors `$IKIGAI_PYTHON` env var with the new value as default

### ISSUE-002: Bootstrap `~/.ikigai/{plan_entities,checkpoints,vault}` directory tree
**Labels:** severity:critical, subsystem:ikigai, type:bug, estimate:0.5d, risk:Q2
**Milestone:** Sprint 1
**Files:** `src/mcp_server/server.py:95-96`, `src/agents/tools.py:20-21`
**Description:** Both files open SQLite / write paths under `~/.ikigai/` that does not exist; `ikigai_plan_cycle` currently swallows the failure (silent data loss). A first-run user gets "no such file or directory" with no recovery path.
**Acceptance:**
- `_bootstrap_ikigai_home()` runs at MCP server module load AND at harness startup
- `mkdir -p` covers `{plan_entities,checkpoints,vault,calendar.db-dir}`
- smoke test asserts `_bootstrap_ikigai_home()` is idempotent

### ISSUE-003: Run `poetry install` + commit `poetry.lock`
**Labels:** severity:critical, subsystem:ikigai, type:bug, estimate:0.5d, risk:Q2
**Milestone:** Sprint 1
**Files:** `life-ops/ikigai/pyproject.toml`, missing `poetry.lock`
**Description:** Cold-start imports of `frontmatter` and `langchain_core` fail because deps were never installed and `poetry.lock` is missing. `uv sync` consumers have no fallback either.
**Acceptance:**
- `poetry install` runs clean in `life-ops/ikigai/`; regenerated `poetry.lock` committed
- `requirements.txt` checked in as a `uv sync` fallback (regenerated from lock, not hand-edited)
- CI cold-cache job green

### ISSUE-004: Create `code-docs/adr/README.md` stub pointer
**Labels:** severity:critical, subsystem:docs, type:docs, estimate:0.5d, risk:Q4
**Milestone:** Sprint 1
**Files:** `code-docs/adr/` (directory exists, no README)
**Description:** ADR discovery (referenced from `code-docs/00-INDEX.md §7` and CLAUDE.md §Pitfalls) is dead — the folder has no README, no index. Cross-link work (G3) cannot start until this lands.
**Acceptance:**
- `code-docs/adr/README.md` exists, ~30 lines
- links to G3 cross-link work + canonical ADR surface
- ADR id convention (ADR-NNN) documented

### ISSUE-005: Restore PAV CLI from pre-`604d6af` snapshot + fix `.pth` editable installs
**Labels:** severity:critical, subsystem:pav, type:migration, estimate:5d, risk:Q1
**Milestone:** Sprint 1
**Files:** `life-ops/operational/apps/cli/` (deleted), `.venv/Lib/site-packages/*.pth`
**Description:** `pav`, `pav-os`, `operational` console scripts and `python -m operational` all fail because `604d6af` deleted `apps/cli/src/` while `.venv` `.pth` files still point at it. Tests in `tests/unit/cli/` fail.
**Acceptance:**
- `apps/cli/src/operational/cli/` restored from pre-`604d6af` git history
- `uv sync --reinstall` regenerates `.pth` files; `pav --help` exits 0
- `tests/unit/cli/` pytest collection errors gone

### ISSUE-006: Rename `_read_entity` collision in `server.py:224`
**Labels:** severity:critical, subsystem:ikigai, type:bug, estimate:0.5d, risk:Q2
**Milestone:** Sprint 1
**Files:** `life-ops/ikigai/src/mcp_server/server.py:207, 224`
**Description:** Both line 207 and line 224 define `_read_entity`; the second definition silently shadows the first and ignores its `table` argument, so `ikigai_score`, `ikigai_regime`, `ikigai_phase`, `ikigai_corrections` return empty rows whenever the checkpoint DB is absent.
**Acceptance:**
- line 224 renamed to `_read_plan_entity_by_table`
- all 4 affected tool responses tested with a fixture DB
- shadow warning (if any) from `ruff` or `mypy` resolved

### ISSUE-007: Make `_TASKDOG_CLI` platform-aware (`win32` vs WSL2)
**Labels:** severity:critical, subsystem:ikigai, type:bug, estimate:0.5d, risk:Q2
**Milestone:** Sprint 1
**Files:** `life-ops/ikigai/src/agents/tools.py:910-912`
**Description:** Hardcodes a `taskdog.exe` Windows path that does not resolve on the WSL2 dev host; every taskdog tool returns "binary not found" on Linux. No env var override.
**Acceptance:**
- `sys.platform` switch picks Windows vs Linux variant
- `TASKDOG_CLI` env var override documented
- Linux variant points at `/mnt/c/Users/mathe/code_space/apps/dev-tools/taskdog/.venv/bin/taskdog`

### ISSUE-008: Reconcile `ikigai_sync_vault` destination — pick one vault root
**Labels:** severity:high, subsystem:ikigai, type:bug, estimate:1d, risk:Q2
**Milestone:** Sprint 1
**Files:** `src/agents/tools.py:355`, `src/mcp_server/server.py:451`
**Description:** `tools.py:355` writes cycle logs to `~/.ikigai/vault/cycle-*.md` while `server.py:451` writes to `data/matheus/ikigai_state/cycle-*.md`; the harness uses the wrong one, so agent-driven cycles never reach the canonical vault.
**Acceptance:**
- single chosen vault root (canonical `data/matheus/ikigai_state/`) used in both files
- callers (H2 in deep-dive) updated
- smoke test confirms `cycle-*.md` lands in the chosen location

### ISSUE-009: Resolve B1 graduation-year blocker (vault vs interfaces)
**Labels:** severity:high, subsystem:ikigai, type:bug, estimate:1d, risk:Q2
**Milestone:** Sprint 1
**Files:** `data/matheus/ikigai_state/b1-blocker-resolution.md`, taskdog `#10`, tuiboard `B1 hard block` column
**Description:** Vault claims B1 RESOLVED but taskdog `#10` and tuiboard `B1 hard block` both remain PENDING, so the CV score is held at 49/D-band by the H3 hard rule. State is internally contradictory.
**Acceptance:**
- either: supply 3 graduation years × 4 CVs and close taskdog `#10` + the tuiboard column
- or: revert vault record to OPEN
- H4 in deep-dive resolved; H3 hard rule no longer fires

### ISSUE-010: Unify the two LangGraph `make_ikigai_graph()` call sites
**Labels:** severity:high, subsystem:ikigai, type:refactor, estimate:1d, risk:Q2
**Milestone:** Sprint 1
**Files:** `server.py:317`, `tools.py:269`, `ikigai_wrapper.py`
**Description:** Both call sites compile their own `StateGraph` with separate `SqliteSaver` connections; checkpoints are technically shared via `~/.ikigai/ikigai_checkpoints.db` but concurrent invocation is fragile (double-lock, stale connection).
**Acceptance:**
- both call sites use the singleton `graph()` from `ikigai_wrapper.py`
- mirrors `langgraph.json` `ikigai_maintainer` entry
- H5 in deep-dive resolved; concurrency test green

### ISSUE-011: Reconcile plan-entities schema split-brain (24-col canonical vs 11-col runtime)
**Labels:** severity:critical, subsystem:ikigai, type:migration, estimate:5d, risk:Q1
**Milestone:** Sprint 1
**Files:** `sqlite_adapter.py:18-80`, `commit.py:58-118`, `server.py:347-357`
**Description:** Canonical 24-col schema in `sqlite_adapter.py` is never written to; `commit.py` and `server.py` always write to the 11-col runtime table, so writes diverge permanently. Read paths sometimes return 11-col, sometimes 24-col, depending on call site.
**Acceptance:**
- 24-col schema promoted to single writer path
- both call sites migrated; 11-col path deprecated
- one-shot backfill script run; legacy 11-col DBs migrated via `migrate_plan_entities.py` (already exists)
- S-C1 closed; runtime DB and adapter schema match

### ISSUE-012: Register `ikigai-maintainer-mcp` in `~/.claude/.mcp.json`
**Labels:** severity:critical, subsystem:ikigai, type:feature, estimate:0.5d, risk:Q2
**Milestone:** Sprint 1
**Files:** `~/.claude/.mcp.json`
**Description:** dcode cannot call IKIGAI tools via MCP because the server is absent from the Claude Code MCP registry, leaving only `Bash → ikigai.bat agent|chat` as a workaround. The MCP transport is the canonical surface.
**Acceptance:**
- `mcpServers.ikigai-maintainer-mcp` entry added, pointing at `poetry run python run_mcp_server.py` (post C1/C2/C3)
- `cat ~/.claude/.mcp.json | jq '.mcpServers | keys'` lists `ikigai-maintainer-mcp`
- dcode smoke test round-trips `tools/list`

### ISSUE-013: Wire `taskdog` FastMCP server into IKIGAI tool registry (drop CLI subprocess)
**Labels:** severity:critical, subsystem:ikigai, type:refactor, estimate:1d, risk:Q2
**Milestone:** Sprint 1
**Files:** `src/agents/tools.py` (subprocess path), `taskdog-mcp` (FastMCP)
**Description:** IKIGAI tools shell out to `taskdog.exe` via subprocess instead of using the FastMCP server; stdio clients bypass the MCP transport entirely. Inconsistent transport surface.
**Acceptance:**
- `taskdog-mcp` registration added to `tools.py`
- `_TASKDOG_CLI` subprocess path removed once FastMCP variant is wired
- S-C3 closed; all 3 external MCP servers use the same transport

### ISSUE-014: Verify MiniMax / Anthropic credential routing in `deepagents_harness.py:294-303`
**Labels:** severity:high, subsystem:ikigai, type:bug, estimate:1d, risk:Q2
**Milestone:** Sprint 1
**Files:** `src/agents/deepagents_harness.py:294-303`
**Description:** Harness defaults `ANTHROPIC_BASE_URL` to `https://api.minimax.io/anthropic` and `ANTHROPIC_MODEL` to `MiniMax-M2.7-highspeed`; if `MINIMAX_API_KEY` is unset it silently falls back to `ANTHROPIC_API_KEY`, producing a credential/model mismatch (Anthropic key, MiniMax model name).
**Acceptance:**
- routing documented in harness README
- MiniMax validated as accepting Anthropic-format requests
- startup warning fires when both keys are missing
- H6 in deep-dive resolved

### ISSUE-015: Decide IKIGAi vector count (5 vs 4) and propagate
**Labels:** severity:high, subsystem:docs, type:docs, estimate:1d, risk:Q4
**Milestone:** Sprint 1
**Files:** `code-docs/prd/PRD-07.md`, `IKIGAi.md`, `life-ops/planner/ikigai_planning/`, `vibe-ops/base/IKIGAi.md`
**Description:** Root docs describe 5 vectors (Passion/Skill/Market/Revenue/Course); PRD-07 describes 4. Blocks G3 cross-link work and any vector-weight decision. Decision deferred per ADR-006.
**Acceptance:**
- user decision: PRD-07 promoted to 5 OR root docs rolled to 4
- all 4 referenced docs updated atomically in one commit
- G2 closed

### ISSUE-016: Confirm tuiboard config uses absolute `boards[].path`
**Labels:** severity:high, subsystem:ikigai, type:bug, estimate:0.5d, risk:Q4
**Milestone:** Sprint 1
**Files:** `~/.tuiboard/config.yaml`, tuiboard config generator template
**Description:** Original config used a relative `../BYD-Camacari-CV.md` that broke `board_list`. Local fix landed; this issue hardens the config generator so a regeneration cannot reintroduce the bug.
**Acceptance:**
- generator-side assertion added: all `boards[].path` values must be absolute
- CI fails on a regression to relative paths
- H1 in deep-dive resolved

---

## §2 Milestone: Sprint 2 — Functional Correctness (12 issues, ~10.5d)

> **Goal:** smaller functional gaps closed, transport options added, error handling tightened. After Sprint 2, every documented IKIGAI tool returns correct output for a known-good fixture.
> **Gate:** `tests/mcp` smoke green, manual MCP round-trip OK for all 18 production tools.

### ISSUE-017: Add HTTP+SSE transport toggle to IKIGAI MCP server
**Labels:** severity:high, subsystem:ikigai, type:feature, estimate:2d, risk:Q1
**Milestone:** Sprint 2
**Files:** `src/mcp_server/server.py:534`
**Description:** Only registers `stdio_server()` so the gateway is locked to stdio. Production deployments need HTTP+SSE for browser/remote clients.
**Acceptance:**
- `--transport http` CLI flag + `IKIGAI_MCP_TRANSPORT` env var
- smoke test round-trips `tools/list` over both transports
- S-H1 closed

### ISSUE-018: Invalidate `_MCP_SESSION_CACHE` on error / timeout / process exit
**Labels:** severity:high, subsystem:ikigai, type:bug, estimate:1d, risk:Q2
**Milestone:** Sprint 2
**Files:** `src/agents/tools.py:550`
**Description:** `_MCP_SESSION_CACHE` is never cleared; a stale broken pipe or timed-out subprocess leaks into subsequent calls, producing 100% failure rate after first hiccup.
**Acceptance:**
- invalidation on `RuntimeError`, `TimeoutError`, explicit `_session.exited`
- mirrors observability sprint spec #01
- S-H2 closed; fault-injection test green

### ISSUE-019: Add retry + circuit-breaker pattern to all MCP call paths
**Labels:** severity:high, subsystem:ikigai, type:feature, estimate:2d, risk:Q2
**Milestone:** Sprint 2
**Files:** `src/agents/tools.py` (`_mcp_call_v1`, `_taskdog_run`)
**Description:** No retry / backoff / reconnection anywhere; a single transient hiccup surfaces to the user. CB-outer / retry-inner pattern already designed in observability sprint spec #01.
**Acceptance:**
- 3 attempts, exponential backoff, half-open after 30s
- S-H3 closed; fault-injection test green

### ISSUE-020: Replace hard-coded paths with env-var / config-file overrides
**Labels:** severity:high, subsystem:ikigai, type:refactor, estimate:1d, risk:Q2
**Milestone:** Sprint 2
**Files:** `tools.py:638-640, 729-733, 910-912`, `start_mcp_gateway.sh`
**Description:** Hard-coded vault roots, calendar paths, CLI paths with no env override. Local-dev users can't point at staging vaults without editing source.
**Acceptance:**
- `ikigai_config.yaml` (or `IKIGAI_*` env vars) introduced
- missing values fail loudly (no silent defaults)
- S-H7 closed

### ISSUE-021: Empty `persistence/` dir — move code in or delete
**Labels:** severity:medium, subsystem:ikigai, type:refactor, estimate:0.5d, risk:Q4
**Milestone:** Sprint 2
**Files:** `src/ikigai/persistence/` (empty), `src/ikigai/propagation/` (canonical)
**Description:** `src/ikigai/persistence/` is empty; canonical persistence code lives in `propagation/`. Pick one location; clean up imports.
**Acceptance:**
- either move propagation → persistence, or delete the empty dir
- imports updated everywhere
- S-M1 closed

### ISSUE-022: Set `COLUMNS=200 LINES=50` in taskdog subprocess env
**Labels:** severity:medium, subsystem:ikigai, type:bug, estimate:0.5d, risk:Q4
**Milestone:** Sprint 2
**Files:** `src/agents/tools.py` (every taskdog subprocess invocation)
**Description:** `taskdog list` truncates the `ikigai` tag to `ikiga…` in narrow terminals (Windows default 80 cols). Wrap every subprocess call with explicit `COLUMNS`/`LINES`.
**Acceptance:**
- `env={**os.environ, "COLUMNS": "200", "LINES": "50"}` applied
- M1 in deep-dive / TD-2 / TD-4 closed
- manual check: `taskdog list --tag ikigai` shows full tag

### ISSUE-023: Document / auto-start taskdog HTTP server on port :8000
**Labels:** severity:medium, subsystem:ikigai, type:docs, estimate:0.5d, risk:Q4
**Milestone:** Sprint 2
**Files:** `README.md`, harness boot path
**Description:** Direct `mcp_config.json` users hit `connection refused` if `taskdog` server on :8000 isn't running. Either auto-start (preferred) or document the requirement.
**Acceptance:**
- auto-start on IKIGAI boot when port :8000 is closed
- README documents the alternative manual-start path
- M2 closed

### ISSUE-024: Replace grep-based JSON-RPC test in `start_mcp_gateway.sh:243-248`
**Labels:** severity:medium, subsystem:ikigai, type:test, estimate:0.5d, risk:Q4
**Milestone:** Sprint 2
**Files:** `start_mcp_gateway.sh:243-248`
**Description:** `test_all` greps stdout for `ikigai-maintainer`; silently breaks if the log format changes. Parse JSON-RPC response with `jq` instead.
**Acceptance:**
- `jq` parses response; asserts `result` is non-empty
- M3 closed

### ISSUE-025: Fix empty `configPath: ""` in `tools.py:747`
**Labels:** severity:medium, subsystem:ikigai, type:bug, estimate:0.5d, risk:Q4
**Milestone:** Sprint 2
**Files:** `src/agents/tools.py:747`
**Description:** `_mcp_call_v1(_TUIBOARD_MCP_CMD, "board_list", {"configPath": ""})` may cause tuiboard to ignore default config search paths.
**Acceptance:**
- either omit the key entirely OR pass absolute config dir
- M4 closed

### ISSUE-026: Standardize `SOLVERFORGE_ROOT` to `/mnt/c/Users/mathe/...`
**Labels:** severity:medium, subsystem:ikigai, type:bug, estimate:0.5d, risk:Q4
**Milestone:** Sprint 2
**Files:** `start_mcp_gateway.sh:31`
**Description:** Uses `$HOME/code_space/...` (Linux home) but code lives at `/mnt/c/Users/mathe/code_space/...` on WSL2. Inconsistent with `TUIBOARD_ROOT`.
**Acceptance:**
- `/mnt/c/...` pattern applied; matches `TUIBOARD_ROOT`
- M5 / SF-3 closed

### ISSUE-027: Verify `ikigai_score` fallback table after C4 fix lands
**Labels:** severity:medium, subsystem:ikigai, type:bug, estimate:0.5d, risk:Q2
**Milestone:** Sprint 2
**Files:** `src/mcp_server/server.py` (`ikigai_score` fallback path)
**Description:** `_read_entity` fallback reads `plan_entities` but upsert writes `ikigai_vectors` instead of `passion`/`skill`. After C4, audit the fallback and align column names.
**Acceptance:**
- fallback query aligned to canonical schema
- S-M7 closed

### ISSUE-028: Replace silent `except: pass` on `plan_entity` write
**Labels:** severity:info, subsystem:ikigai, type:bug, estimate:0.5d, risk:Q4
**Milestone:** Sprint 2
**Files:** `src/mcp_server/server.py:367-368`
**Description:** Swallows all exceptions during `plan_entities.db` upsert; schema mismatch / permission errors silently lose cycle data.
**Acceptance:**
- `logger.exception(...)` at minimum
- better: raise and return `ToolResult(error=...)`
- I2 closed

---

## §3 Milestone: Sprint 3 — Reliability + Observability (13 issues, ~16.0d)

> **Goal:** dual OTLP/HTTP export to LangSmith + Langfuse works in all 4 repos; retry/CB on every MCP call path; HITL gating expanded.
> **Gate:** observability sprint Spec 02 + Spec 03 green; all `feat/otel-tracing` branches mergeable.

### ISSUE-029: Expand `interrupt_on` to gate 6+ mutation tools (HITL)
**Labels:** severity:high, subsystem:ikigai, type:feature, estimate:2d, risk:Q1
**Milestone:** Sprint 3
**Files:** `src/agents/deepagents_harness.py`
**Description:** Currently only `interrupt_on = {"write_file": True}`; `ikigai_checkpoint(set)`, `ikigai_plan_cycle`, `ikigai_sync_vault`, `solverforge_create_event`, `tuiboard_update_task`/`create_task`, `taskdog_create_task`/`complete_task` all bypass HITL.
**Acceptance:**
- explicit `interrupt_on` entries for each of the 6+ mutation tools
- manual smoke test: tool fires → user approves → tool runs
- S-H4 closed

### ISSUE-030: Decompose monolithic agent into specialized sub-agents
**Labels:** severity:high, subsystem:ikigai, type:refactor, estimate:5d, risk:Q1
**Milestone:** Sprint 3
**Files:** `src/agents/deepagents_harness.py`
**Description:** One monolithic agent with no subagents — limits parallelism and reflection. Split into planner / executor / observer / reflector with explicit handoff tools and shared scratchpad.
**Acceptance:**
- 4 sub-agents instantiated, each with a system prompt
- handoff tools wired (no raw message passing)
- shared scratchpad uses the canonical store
- S-H5 closed

### ISSUE-031: Call `init_tracing()` from MCP server module load
**Labels:** severity:high, subsystem:ikigai, type:feature, estimate:0.5d, risk:Q2
**Milestone:** Sprint 3
**Files:** `src/mcp_server/server.py`
**Description:** `server.py` does not initialize OpenTelemetry, so all MCP server spans are missing from LangSmith/Langfuse. Add `init_tracing()` at module load, gated on `OTEL_ENABLED=true`.
**Acceptance:**
- `init_tracing()` invoked at top of `server.py` (mirror `deepagents_harness.py:29`)
- `OTEL_ENABLED=false` short-circuits cleanly
- S-H8 closed

### ISSUE-032: Add `@observed_tool` decorator to all 18 production tools
**Labels:** severity:medium, subsystem:ikigai, type:feature, estimate:2d, risk:Q3
**Milestone:** Sprint 3
**Files:** `src/agents/tools.py` (all `@tool` decorators)
**Description:** Production tools have no per-tool span coverage even after `init_tracing()` lands. Span attributes must include `tool.name`, `tool.args_hash`, `tool.latency_ms`.
**Acceptance:**
- every `@tool` decorated with `@observed_tool`
- spans visible in LangSmith UI for at least 3 representative tools
- latent from S-H8 closed

### ISSUE-033: TUIBOARD-001 — Merge `feat/otel-tracing` branch (commit `2c39867`)
**Labels:** severity:high, subsystem:mcp-tuiboard, type:migration, estimate:1d, risk:Q2
**Milestone:** Sprint 3
**Files:** `apps/kanban/tuiboard/feat/otel-tracing`
**Description:** Dual OTLP/HTTP export to LangSmith + Langfuse is done on `feat/otel-tracing` but unmerged. Gated by observability sprint Spec 03 + Spec 02.
**Acceptance:**
- rebase on main, smoke test, merge
- TB-1 closed
- dual export visible in both backends

### ISSUE-034: TUIBOARD-002 — Migrate tuiboard JSON-RPC to official MCP SDK
**Labels:** severity:high, subsystem:mcp-tuiboard, type:refactor, estimate:2d, risk:Q1
**Milestone:** Sprint 3
**Files:** `apps/kanban/tuiboard/mcp/tuiboard-mcp.ts`
**Description:** Hand-rolled JSON-RPC over stdin/stdout; missing reconnection, ping, and capability negotiation.
**Acceptance:**
- migrated to official MCP TypeScript SDK
- reconnection + ping + capability negotiation all exercised in smoke test
- TB-2 closed

### ISSUE-035: TUIBOARD-003 — Add retry + circuit-breaker to stdin/stdout MCP calls
**Labels:** severity:high, subsystem:mcp-tuiboard, type:feature, estimate:1d, risk:Q2
**Milestone:** Sprint 3
**Files:** `apps/kanban/tuiboard/mcp/tuiboard-mcp.ts`
**Description:** No retry/CB; transient failures bubble to the user. Mirror observability sprint spec #01 with `p-retry` or hand-rolled backoff.
**Acceptance:**
- CB-outer / retry-inner pattern, 3 attempts, exp backoff, half-open after 30s
- TB-3 closed

### ISSUE-036: TASKDOG-001 — Merge `feat/otel-tracing` branch (commit `600c92b9`)
**Labels:** severity:high, subsystem:mcp-taskdog, type:migration, estimate:1d, risk:Q2
**Milestone:** Sprint 3
**Files:** `apps/dev-tools/taskdog/feat/otel-tracing`
**Description:** Dual OTLP/HTTP export is done on `feat/otel-tracing` but unmerged. Gated by Spec 03 + Spec 02.
**Acceptance:**
- rebase, smoke-test, merge
- TD-1 closed; dual export visible in both backends

### ISSUE-037: TASKDOG-002 — Document `:8000` server auto-start requirement
**Labels:** severity:high, subsystem:mcp-taskdog, type:docs, estimate:0.5d, risk:Q4
**Milestone:** Sprint 3
**Files:** `mcp_config.json` README, taskdog boot path
**Description:** `taskdog-mcp` connects to `http://localhost:8000`; if the server isn't running all MCP tools fail. Either auto-start on IKIGAI boot OR document the requirement.
**Acceptance:**
- auto-start added to IKIGAI boot OR requirement documented in `mcp_config.json` users' README
- TD-3 closed

### ISSUE-038: TASKDOG-003 — Add CB + retry to taskdog HTTP server calls
**Labels:** severity:medium, subsystem:mcp-taskdog, type:feature, estimate:1d, risk:Q2
**Milestone:** Sprint 3
**Files:** `apps/dev-tools/taskdog/server.py`
**Description:** No circuit-breaker / retry on server calls. Mirror observability sprint spec #01 with `tenacity`.
**Acceptance:**
- CB-outer / retry-inner; 3 attempts; exp backoff; half-open after 30s
- TD-5 closed; fault-injection test green

### ISSUE-039: SOLVERFORGE-001 — Merge `feat/otel-tracing` branch (commits `cfbf12b`, `064b8c9`)
**Labels:** severity:high, subsystem:mcp-solverforge, type:migration, estimate:1d, risk:Q2
**Milestone:** Sprint 3
**Files:** `apps/calendar/solverforge-calendar/feat/otel-tracing`
**Description:** Dual OTLP/HTTP export is done on `feat/otel-tracing` but unmerged. Rebase on `feat/rust-build-fix` (HTTP feature flag), smoke-test, merge.
**Acceptance:**
- rebase, smoke-test, merge
- SF-1 closed; dual export visible in both backends

### ISSUE-040: SOLVERFORGE-002 — Seed `calendar.db` with mock calendar OR document empty state
**Labels:** severity:high, subsystem:mcp-solverforge, type:feature, estimate:1d, risk:Q2
**Milestone:** Sprint 3
**Files:** `~/.ikigai/vault/calendar.db`, MCP server bootstrap
**Description:** `~/.ikigai/vault/calendar.db` does not exist; `solverforge_create_event` and friends hit a missing DB. Seed 7 days of mock events OR document why empty is acceptable and surface a clear "no calendar" error.
**Acceptance:**
- either: 7 days of mock events seeded; OR clear "no calendar" error surfaced
- H3 / SF-2 closed

### ISSUE-041: SOLVERFORGE-003 — Wire HTTP+SSE transport behind feature flag
**Labels:** severity:medium, subsystem:mcp-solverforge, type:feature, estimate:1d, risk:Q3
**Milestone:** Sprint 3
**Files:** `apps/calendar/solverforge-calendar/Cargo.toml`, server entry point
**Description:** HTTP+SSE transport is stubbed but never enabled. Add `IKIGAI_SOLVERFORGE_HTTP=1` env var + Cargo feature flag (`[features] http = ["axum"]`).
**Acceptance:**
- env var + Cargo feature flag both wired
- prod deployments can flip it on
- SF-4 closed

---

## §4 Milestone: Sprint 4 — HITL + Advanced (25 issues, ~28.0d)

> **Goal:** test scaffolding, factories, mocks, refactors, advanced features — the "long tail" of work that makes the system maintainable.
> **Gate:** test coverage ≥ 60% on `tools.py`; all Pydantic invariants enforced; tuiboard archive flow works.

### ISSUE-042: Add schema version + migration runner for `plan_entities`
**Labels:** severity:medium, subsystem:ikigai, type:feature, estimate:2d, risk:Q3
**Milestone:** Sprint 4
**Files:** `sqlite_adapter.py`, `commit.py`
**Description:** `CREATE TABLE IF NOT EXISTS` only; any schema evolution requires manual SQL. Add `schema_version` table + `migrations/` runner applying numbered SQL files in order.
**Acceptance:**
- `schema_version` table tracks applied migrations
- numbered `.sql` files in `migrations/` applied in order
- S-M2 closed

### ISSUE-043: Decide Pydantic invariant (`frozen=True, extra="forbid"`) across entities
**Labels:** severity:medium, subsystem:ikigai, type:refactor, estimate:5d, risk:Q1
**Milestone:** Sprint 4
**Files:** 15 entity files under `src/ikigai/entities/`, `CLAUDE.md §Global Conventions`
**Description:** Most `entities/*.py` use `extra="allow"` / `frozen=False`, violating the CLAUDE.md invariant. Either relax the invariant OR convert all 15 files in one sweep.
**Acceptance:**
- user decision on which side wins
- either: CLAUDE.md relaxed (with rationale) OR 15 entities converted (with tests)
- S-M3 closed

### ISSUE-044: Add MCP integration tests (mock + real servers)
**Labels:** severity:medium, subsystem:ikigai, type:test, estimate:2d, risk:Q3
**Milestone:** Sprint 4
**Files:** `tests/mcp/` (new directory)
**Description:** IKIGAI has zero MCP integration tests today. Add `tests/mcp/` suite that mocks subprocess for unit tests and spawns the real `ikigai-maintainer-mcp` / `taskdog-mcp` / `tuiboard-mcp` servers for e2e JSON-RPC round-trips.
**Acceptance:**
- mock suite: ≥ 80% of `tools.py` paths covered
- real-server suite: at least 1 happy-path + 1 error-path per tool
- S-M4 closed

### ISSUE-045: Add Pydantic test factories (`make_goal`, `make_dream`, …)
**Labels:** severity:medium, subsystem:ikigai, type:test, estimate:1d, risk:Q4
**Milestone:** Sprint 4
**Files:** `tests/factories.py` (new)
**Description:** Tests repeat boilerplate Pydantic instantiation. Add `tests/factories.py` with `make_goal`, `make_dream`, `make_objective`, `make_project`, `make_deliverable`.
**Acceptance:**
- factories produce valid, fully-populated fixtures
- existing tests refactored to use them
- S-M5 closed

### ISSUE-046: Add mock backends for MCP servers in test suite
**Labels:** severity:medium, subsystem:ikigai, type:test, estimate:1d, risk:Q4
**Milestone:** Sprint 4
**Files:** `tests/mocks/mcp.py` (new)
**Description:** Tests need `unittest.mock` stubs for `_mcp_call_v1` / `_taskdog_run` so they can run offline. Add `tests/mocks/mcp.py` exposing `MockTaskdogServer`, `MockTuiboardServer`, `MockSolverforgeServer`.
**Acceptance:**
- 3 mock backends implemented
- offline test run green
- S-M6 closed

### ISSUE-047: Document LangGraph singleton testing workaround
**Labels:** severity:info, subsystem:ikigai, type:docs, estimate:0.5d, risk:Q4
**Milestone:** Sprint 4
**Files:** `src/ikigai/graph.py:163-170`, test conftest
**Description:** Module-level `_graph_instance` makes testing and hot-reload impossible. Acceptable for prod; document a `reset_graph_singleton()` helper.
**Acceptance:**
- helper exported; conftest uses it
- I1 closed

### ISSUE-048: Standardize on stdio MCP for all 3 external servers
**Labels:** severity:info, subsystem:ikigai, type:refactor, estimate:2d, risk:Q3
**Milestone:** Sprint 4
**Files:** `src/agents/tools.py` (3 call sites)
**Description:** Three different integration patterns live (stdio, HTTP, CLI subprocess). Pick stdio MCP as canonical; rewrite all three.
**Acceptance:**
- all 3 call sites use stdio MCP
- S-I1 closed

### ISSUE-049: Document TUI mutation surface = 0 architectural choice
**Labels:** severity:info, subsystem:docs, type:docs, estimate:0.5d, risk:Q4
**Milestone:** Sprint 4
**Files:** `TUI.md`, TUI notification strings
**Description:** `apps/tui/` is read-only by design; users hit a wall when they need to mutate. Document the choice; add `pav <cmd>` shortcut hints to TUI notifications.
**Acceptance:**
- TUI.md section added
- notification strings include the `pav <cmd>` hint
- S-I2 closed

### ISSUE-050: Document PAV TUI lives in sibling `life-pav-cli` workspace
**Labels:** severity:info, subsystem:docs, type:docs, estimate:0.5d, risk:Q4
**Milestone:** Sprint 4
**Files:** `ARCHITECTURE_INDEX.md`
**Description:** PAV TUI source is in `life-pav-cli`, not `life-ops/ikigai`; breaks newcomers' mental model. One-paragraph note added.
**Acceptance:**
- `ARCHITECTURE_INDEX.md` updated
- S-I3 closed

### ISSUE-051: Add "Press r to retry" UX in TUI error overlay
**Labels:** severity:info, subsystem:ikigai, type:feature, estimate:0.5d, risk:Q4
**Milestone:** Sprint 4
**Files:** `apps/tui/.../analytics_screen.py:318-322`, TUI help
**Description:** Error overlay shows but no retry affordance. Bind `r` to retry the last fetch; document in TUI help.
**Acceptance:**
- `r` keybinding wired
- TUI help text updated
- S-I4 closed

### ISSUE-052: TUIBOARD-004 — Add `board.tasks.archive` soft-delete tool
**Labels:** severity:medium, subsystem:mcp-tuiboard, type:feature, estimate:0.5d, risk:Q4
**Milestone:** Sprint 4
**Files:** `apps/kanban/tuiboard/src/`
**Description:** IKIGAI uses soft-delete via `archive` but tuiboard exposes only `delete`. Add `board.tasks.archive` and route IKIGAI's archive flow through it.
**Acceptance:**
- new tool exposed over MCP
- IKIGAI archive flow uses it
- TB-4 closed

### ISSUE-053: TUIBOARD-005 — Add Bun-native structured logger with `trace_id` correlation
**Labels:** severity:medium, subsystem:mcp-tuiboard, type:feature, estimate:0.5d, risk:Q4
**Milestone:** Sprint 4
**Files:** `apps/kanban/tuiboard/src/logger.ts`
**Description:** No structured logging; span/trace correlation with LangSmith impossible. Add `console.json` style logging with `trace_id` from the active OTel context.
**Acceptance:**
- structured logs visible in JSON format
- `trace_id` correlates with LangSmith span IDs
- TB-5 closed

### ISSUE-054: TUIBOARD-006 — Pin MCP SDK and OpenTelemetry SDK in `package.json`
**Labels:** severity:info, subsystem:mcp-tuiboard, type:docs, estimate:0.5d, risk:Q4
**Milestone:** Sprint 4
**Files:** `apps/kanban/tuiboard/package.json`
**Description:** No version pinning; reproducibility + supply-chain risk. Add exact versions for `@modelcontextprotocol/sdk` and `@opentelemetry/*`.
**Acceptance:**
- exact versions pinned; lockfile regenerated
- TB-6 closed

### ISSUE-055: TASKDOG-004 — Document `~/.config/taskdog/mcp.toml` env override
**Labels:** severity:info, subsystem:mcp-taskdog, type:docs, estimate:0.5d, risk:Q4
**Milestone:** Sprint 4
**Files:** `apps/dev-tools/taskdog/README.md`
**Description:** Config location is XDG (`~/.config/taskdog/mcp.toml`) — differs from IKIGAI's `~/.ikigai/` convention. Document `TASKDOG_CONFIG` env override.
**Acceptance:**
- README updated
- TD-6 closed

### ISSUE-056: SOLVERFORGE-004 — Document 16-tool taxonomy in IKIGAI README
**Labels:** severity:info, subsystem:docs, type:docs, estimate:0.5d, risk:Q4
**Milestone:** Sprint 4
**Files:** `life-ops/ikigai/README.md`
**Description:** `calendars_*`, `projects_*`, `events_*`, `dependencies_*`, `google_sync`, `upi_*` undocumented in IKIGAI. Add tool-reference table.
**Acceptance:**
- 16-tool reference table in README
- SF-5 closed

### ISSUE-057: SOLVERFORGE-005 — Confirm `[features] http = []` fix is on main (commit `1716b16`)
**Labels:** severity:info, subsystem:mcp-solverforge, type:migration, estimate:0.5d, risk:Q4
**Milestone:** Sprint 4
**Files:** `apps/calendar/solverforge-calendar/Cargo.toml`
**Description:** Build requires the `http` feature flag to be declared even when empty. Verify commit `1716b16` is on main; otherwise cherry-pick.
**Acceptance:**
- commit verified or cherry-picked
- SF-6 closed

### ISSUE-058: PAV-002 — Decide fate of orphaned `tests/tui/` and `tests/ui/`
**Labels:** severity:high, subsystem:pav, type:refactor, estimate:1d, risk:Q2
**Milestone:** Sprint 4
**Files:** `life-ops/operational/tests/tui/`, `tests/ui/`
**Description:** Survive but their source (`apps/tui/`) was deleted in `604d6af`; they collect errors / skip. Either restore the apps (overlaps PAV-001) or delete orphan dirs + update CI matrix.
**Acceptance:**
- either restore source OR delete dirs + remove from CI
- P2 closed

### ISSUE-059: PAV-003 — Move `_PersistentRepo` singletons off `~/.time-tasker/*.json`
**Labels:** severity:high, subsystem:pav, type:refactor, estimate:1d, risk:Q2
**Milestone:** Sprint 4
**Files:** 15 `_PersistentRepo` singleton sites in `life-ops/operational/packages/core/src/`
**Description:** 15 singletons write to `~/.time-tasker/*.json` — not the canonical `~/.life-operational/` location.
**Acceptance:**
- either move the files OR document the env var
- P3 closed

### ISSUE-060: PAV-004 — Make `ikigai.bat` venv path configurable
**Labels:** severity:high, subsystem:pav, type:bug, estimate:0.5d, risk:Q4
**Milestone:** Sprint 4
**Files:** `ikigai.bat`
**Description:** Hardcodes `.venv\Scripts\python.exe`; if venv is recreated with a different name/location the .bat fails silently. Replace with `%IKIGAI_PYTHON%` env var.
**Acceptance:**
- `%IKIGAI_PYTHON%` env var with current path as fallback
- P4 closed

### ISSUE-061: PAV-005 — Reconcile `scripts/verify_sprint.sh` vs `uv run verify_sprint`
**Labels:** severity:high, subsystem:pav, type:docs, estimate:0.5d, risk:Q4
**Milestone:** Sprint 4
**Files:** `scripts/verify_sprint.sh`, `pyproject.toml`, docs
**Description:** Only `.sh` exists; `uv run verify_sprint` fails. Either add `pyproject.toml` script entry OR remove the `uv run verify_sprint` line from docs.
**Acceptance:**
- one side removed or the .sh is wired through `pyproject.toml`
- P5 closed

### ISSUE-062: PAV-006 — Update `Makefile test` target to use uv (not poetry)
**Labels:** severity:medium, subsystem:pav, type:bug, estimate:0.5d, risk:Q4
**Milestone:** Sprint 4
**Files:** `Makefile` (`test` target)
**Description:** Uses `poetry run pytest` for `life-ops/operational/` which is actually a `uv` workspace. Replace with `cd life-ops/operational && uv run pytest`.
**Acceptance:**
- Makefile updated; manual test green
- P6 closed

### ISSUE-063: PAV-007 — Gitignore + bulk-delete stray 0-byte files at repo root
**Labels:** severity:medium, subsystem:pav, type:refactor, estimate:0.5d, risk:Q4
**Milestone:** Sprint 4
**Files:** `.gitignore`, repo root
**Description:** Stray 0-byte files (`2`, `0`, `4}`, `dict[str`, `ISO`, `None`, `String`, `bool`, `new`, `int`, `str`, `date`) are untracked crash/typo artifacts.
**Acceptance:**
- `.gitignore` patterns added matching `^[A-Za-z0-9_}\[`$]+$` for small files at root
- existing strays bulk-deleted
- P7 / G6 closed

### ISSUE-064: PAV-008 — Document which of the two CLAUDE.md files is authoritative
**Labels:** severity:info, subsystem:docs, type:docs, estimate:0.5d, risk:Q4
**Milestone:** Sprint 4
**Files:** root `CLAUDE.md`, `life-ops/operational/CLAUDE.md`
**Description:** Two files describe overlapping scopes. Add header to each that says "this file is authoritative for X, defer to other for Y".
**Acceptance:**
- both headers updated
- P8 / G8 closed

### ISSUE-065: CI-001 — Add `mypy src/` to CI matrix for IKIGAI workspace
**Labels:** severity:high, subsystem:ci, type:feature, estimate:0.5d, risk:Q2
**Milestone:** Sprint 4
**Files:** `.github/workflows/ci.yml`
**Description:** `mypy` is run for `life/` CI but IKIGAI workspace lacks strict typing gates. Add `mypy life-ops/ikigai/src/` to the matrix.
**Acceptance:**
- CI matrix entry added
- latent from Sprint-3 schema split-brain fix (ISSUE-011)
- CI-001 closed

### ISSUE-066: FEAT-001 — AI-native strategic model migration (PAV TUI/CLI → MCP contracts)
**Labels:** severity:medium, subsystem:feature, type:migration, estimate:5d, risk:Q1
**Milestone:** Sprint 4
**Files:** `life-ops/operational/`, `life-ops/ikigai/`
**Description:** PAV TUI/CLI deprecated for deletion; workspace becomes strategic template with AI-native MCP contracts only, served by deepagents LangGraph harness. 8-week effort, no bespoke UI; from pending construction A.
**Acceptance:**
- workspace reduced to MCP contracts + LangGraph harness
- no bespoke UI code in `life-ops/operational/`
- FEAT-001 closed; ADR captured

---

## §5 Milestone: Backlog (14 issues, ~16.5d)

> **Goal:** long-tail, cross-cutting, deferred. Tracked for visibility; not gated by any sprint.
> **Promote criteria:** when the team has bandwidth, or when an issue becomes a blocker for Sprint N+1 work.

### ISSUE-067: DOCS-003 — Build ADR cross-link table in `code-docs/00-INDEX.md §7`
**Labels:** severity:high, subsystem:docs, type:docs, estimate:1d, risk:Q4
**Milestone:** Backlog
**Files:** `code-docs/00-INDEX.md`
**Description:** ADRs scattered across 3 locations with no canonical surface. Add `§7 Architecture Decision Records` table listing every ADR id, title, status, link.
**Acceptance:**
- §7 table added; every ADR enumerated
- G3 closed

### ISSUE-068: DOCS-004 — Mark `vibe-ops/specs/` v1 schemas DEPRECATED
**Labels:** severity:high, subsystem:docs, type:docs, estimate:0.5d, risk:Q4
**Milestone:** Backlog
**Files:** `vibe-ops/specs/` (v1 files)
**Description:** Deprecated v1 schemas sit next to v2. Add `DEPRECATED: see v2` frontmatter to every v1 file + banner at directory top.
**Acceptance:**
- frontmatter added to all v1 files
- directory banner added
- G4 closed

### ISSUE-069: DOCS-005 — Enumerate operational docs from in-folder READMEs
**Labels:** severity:medium, subsystem:docs, type:docs, estimate:0.5d, risk:Q4
**Milestone:** Backlog
**Files:** `code-docs/00-INDEX.md`, `life-ops/operational/**/README.md`
**Description:** "Operational docs count" is approximate. Walk every `**/README.md` under `life-ops/operational/` and produce exact count + last-updated column.
**Acceptance:**
- exact count surfaced in `00-INDEX.md`
- G5 closed

### ISSUE-070: DOCS-006 — Gitignore + cleanup `life-ops/operational/` throwaway files
**Labels:** severity:medium, subsystem:docs, type:refactor, estimate:0.5d, risk:Q4
**Milestone:** Backlog
**Files:** `.gitignore`, `life-ops/operational/`
**Description:** `output.txt`, `CheckResult`, `not`, etc. at `life-ops/operational/` root are not source.
**Acceptance:**
- `.gitignore` patterns added
- throwaway files bulk-deleted
- G7 closed

### ISSUE-071: CI-002 — Add MCP integration test job to CI matrix
**Labels:** severity:high, subsystem:ci, type:feature, estimate:2d, risk:Q3
**Milestone:** Backlog
**Files:** `.github/workflows/ci.yml`, `docker-compose.yml` (new)
**Description:** No CI job exercises MCP integration tests. Add a job running `uv run pytest tests/mcp -m integration` against a docker-compose stack of `taskdog` + `tuiboard` + `solverforge` mocks.
**Acceptance:**
- CI job added; docker-compose mocks live
- CI-002 closed; follows from S-M4 (ISSUE-044)

### ISSUE-072: CI-003 — Gate merges on observability-sprint Spec 02 + Spec 03
**Labels:** severity:medium, subsystem:ci, type:feature, estimate:1d, risk:Q3
**Milestone:** Backlog
**Files:** `.github/workflows/openwiki-update.yml`
**Description:** `feat/otel-tracing` branches in 3 repos are mergeable only after Spec 02 (server-side reliability) + Spec 03 (smoke test) land. Add required-status check `observability-smoke`.
**Acceptance:**
- required-status check wired
- from §1 §7 priority roadmap
- CI-003 closed

### ISSUE-073: CI-004 — Pre-commit hook to block new stray files at repo root
**Labels:** severity:medium, subsystem:ci, type:feature, estimate:0.5d, risk:Q4
**Milestone:** Backlog
**Files:** `.pre-commit-config.yaml`
**Description:** Recurring `2`, `4}`, `dict[str` typos at root. Add pre-commit `check-no-stray-root-files` hook mirroring ISSUE-063.
**Acceptance:**
- hook blocks offending files
- P7 follow-up closed
- CI-004 closed

### ISSUE-074: FEAT-002 — HTTP+SSE transport for IKIGAI MCP server
**Labels:** severity:medium, subsystem:feature, type:feature, estimate:2d, risk:Q3
**Milestone:** Backlog
**Files:** `src/mcp_server/server.py`, deploy docs
**Description:** After ISSUE-017 ships, ship production HTTP+SSE transport config (TLS, auth token, rate-limit) + deployment guide.
**Acceptance:**
- TLS, auth, rate-limit all wired
- deployment guide published
- FEAT-002 closed

### ISSUE-075: FEAT-003 — Subagent decomposition (planner / executor / observer / reflector)
**Labels:** severity:medium, subsystem:feature, type:refactor, estimate:5d, risk:Q1
**Milestone:** Backlog
**Files:** `src/agents/deepagents_harness.py`, sub-agent modules
**Description:** After ISSUE-030 lands, ship the four specialized sub-agents with explicit handoff tools + shared scratchpad. From pending construction C.
**Acceptance:**
- 4 sub-agents fully exercised in production scenarios
- handoff latency measured; scratchpad read/write tested
- FEAT-003 closed

### ISSUE-076: TEST-001 — Add full MCP integration test coverage for IKIGAI tools
**Labels:** severity:medium, subsystem:test, type:test, estimate:2d, risk:Q3
**Milestone:** Backlog
**Files:** `tests/mcp/`
**Description:** Beyond ISSUE-044 (scaffolding), reach ≥ 80% coverage for the 18 production tools with both happy-path and error-path JSON-RPC scenarios.
**Acceptance:**
- coverage report ≥ 80%
- long-tail follow-up closed

### ISSUE-077: REFACTOR-001 — Decide Pydantic invariant: relax or convert
**Labels:** severity:medium, subsystem:refactor, type:refactor, estimate:5d, risk:Q1
**Milestone:** Backlog
**Files:** 15 entity files, `CLAUDE.md`
**Description:** Carry out whichever side of the ISSUE-043 decision is taken (relax `CLAUDE.md §Global Conventions` OR convert 15 entity files).
**Acceptance:**
- decision from ISSUE-043 executed
- REFACTOR-001 closed

### ISSUE-078: REFACTOR-002 — Dissolve observability-sprint worktree after merge
**Labels:** severity:info, subsystem:refactor, type:migration, estimate:0.5d, risk:Q4
**Milestone:** Backlog
**Files:** `life-mcp-observability-worktree/`
**Description:** Worktree was created for the sprint; once Sprint-3 merges land, dissolve it. `git worktree remove` + delete branch.
**Acceptance:**
- worktree removed; branch deleted
- from observability docs spec #04
- REFACTOR-002 closed

### ISSUE-079: VIBEOPS-001 — Migrate deprecated `vibe-ops/specs/` v1 → v2 cross-reference
**Labels:** severity:medium, subsystem:vibe-ops, type:migration, estimate:2d, risk:Q3
**Milestone:** Backlog
**Files:** `vibe-ops/specs/`, runtime callers
**Description:** Once ISSUE-068 marks v1 DEPRECATED, add v2 cross-reference links + one-time migration table for any runtime code still reading v1 paths.
**Acceptance:**
- v2 cross-refs added
- runtime migration table complete
- VIBEOPS-001 closed

### ISSUE-080: VIBEOPS-002 — Reconcile IKIGAi vector count in `vibe-ops/base/IKIGAi.md`
**Labels:** severity:medium, subsystem:vibe-ops, type:docs, estimate:0.5d, risk:Q4
**Milestone:** Backlog
**Files:** `vibe-ops/base/IKIGAi.md`, other conceptual docs
**Description:** Carries the conceptual 5-vector model. Once ISSUE-015 picks a side, align this file (and any other conceptual doc) to the chosen number.
**Acceptance:**
- aligned to ISSUE-015 decision
- G2 follow-up closed

---

## §6 Label Schema

GitHub labels are organized as `<group>:<value>` so they group cleanly in the Issues UI.

### Severity (4)
| Label | Definition |
|-------|-----------|
| `severity:critical` | Blocks system boot or causes silent data loss; must fix before merge to main |
| `severity:high` | Functional break or significant reliability gap; fix within current sprint |
| `severity:medium` | Polish, refactor, or test scaffolding; fix within the sprint it's filed in |
| `severity:info` | Docs, UX, worktree hygiene; no functional impact; backlog-eligible |

### Subsystem (11)
| Label | Scope |
|-------|-------|
| `subsystem:ikigai` | `life-ops/ikigai/` — MCP server, agents, tools, harness |
| `subsystem:pav` | `life-ops/operational/` — productivity kernel |
| `subsystem:docs` | `code-docs/`, READMEs, cross-link tables |
| `subsystem:ci` | `.github/workflows/`, pre-commit hooks, status checks |
| `subsystem:mcp-tuiboard` | `apps/kanban/tuiboard/` |
| `subsystem:mcp-taskdog` | `apps/dev-tools/taskdog/` |
| `subsystem:mcp-solverforge` | `apps/calendar/solverforge-calendar/` |
| `subsystem:vibe-ops` | `vibe-ops/` cybernetic engine |
| `subsystem:test` | test scaffolding, coverage |
| `subsystem:refactor` | workspace hygiene (worktree dissolve, .gitignore) |
| `subsystem:feature` | cross-cutting feature work (FEAT-001..003) |

### Type (6)
| Label | Definition |
|-------|-----------|
| `type:bug` | Defect — incorrect behavior |
| `type:refactor` | Code restructure with no behavior change |
| `type:feature` | New functionality |
| `type:docs` | Documentation only |
| `type:test` | Test scaffolding or coverage |
| `type:migration` | Schema, dependency, or large code reshuffle |

### Estimate (5)
| Label | Range |
|-------|-------|
| `estimate:0.5d` | ≤ half a day |
| `estimate:1d` | half–1 day |
| `estimate:2d` | 1–2 days |
| `estimate:5d` | 2–5 days |
| `estimate:large` | ≥ 5 days (rare; usually broken into smaller issues) |

### Risk (4)
| Label | Definition |
|-------|-----------|
| `risk:Q1` | High risk + high effort (large surface, multi-subsystem) |
| `risk:Q2` | High risk + low effort (small surface, can land fast) |
| `risk:Q3` | Low risk + high effort (big refactor, low blast radius) |
| `risk:Q4` | Low risk + low effort (trivially safe) |

---

## §7 Milestone Criteria

### Sprint 1 — System Boot
- **Definition of done:** `ikigai.bat mcp` boots; `pav --help` exits 0; all 8 critical issues closed; dcode can round-trip `tools/list`.
- **Roll-back plan:** all changes additive or gated behind a flag; revertible via `git revert`.
- **Acceptance evidence:** CI green; smoke test artifact in `logs/sprint-1/`.

### Sprint 2 — Functional Correctness
- **Definition of done:** all 12 issues closed; manual smoke test confirms every documented IKIGAI tool returns correct output for a known-good fixture.
- **Acceptance evidence:** `tests/mcp` smoke run; manual checklist signed off.

### Sprint 3 — Reliability + Observability
- **Definition of done:** all 13 issues closed; dual OTLP/HTTP export verified in LangSmith + Langfuse; CB-outer/retry-inner pattern applied to all MCP call paths; HITL gating expanded.
- **Acceptance evidence:** observability sprint Spec 02 + Spec 03 green; all `feat/otel-tracing` branches merged.

### Sprint 4 — HITL + Advanced
- **Definition of done:** all 25 issues closed; test coverage ≥ 60% on `tools.py`; Pydantic invariant enforced (or relaxed with rationale); tuiboard archive flow wired.
- **Acceptance evidence:** coverage report; ADR captured for any invariant relaxation.

### Backlog
- **Promotion criteria:** bandwidth becomes available, or the issue becomes a blocker for Sprint N+1 work, or it accumulates 3+ 👍 reactions.
- **Review cadence:** monthly; items idle > 90 days are closed as `not_planned`.

---

## §8 Cross-References

### Source documents
- `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` — 77+ issues across §1-§5
- `life-ops/ikigai/docs/IKIGAI_BACKEND_DEEP_DIVE_REPORT.md` — 19 issues (all folded into Sprint 1)
- `code-docs/diagnostic/2026-08-27-issue-dependencies.md` — dependency graph between issues
- `code-docs/diagnostic/2026-08-27-risk-effort-matrix.md` — Q1-Q4 risk/effort placement
- `life-ops/ikigai/docs/observability/0{1..4}-*.md` — observability sprint specs

### Issue dependency clusters
| Cluster | Issues | Why grouped |
|---------|--------|-------------|
| Boot unblock | 001-005 | All critical; all block Sprint 1 from starting |
| Schema split-brain | 011, 042 | 011 migrates; 042 adds version runner |
| Observability | 031, 032, 033, 036, 039 | init_tracing + per-tool spans + 3 merges |
| Retry/CB | 019, 035, 038 | One pattern applied to 3 call sites |
| HITL | 029, 030 | Both expand human-in-the-loop surface |
| Subagents | 030, 075 | Decomposition + production hardening |
| HTTP+SSE | 017, 074 | Toggle in 017; production config in 074 |
| CLAUDE.md invariants | 015, 043, 077, 080 | One decision (5 vs 4 vectors, Pydantic strict) propagates to 4 issues |
| Stray-file hygiene | 063, 073 | 063 fixes current; 073 prevents future |
| Worktree dissolve | 078 | Last step of observability sprint |

### Subsystem dependency matrix
| from \ to | ikigai | pav | docs | ci | mcp-tuiboard | mcp-taskdog | mcp-solverforge |
|-----------|:------:|:---:|:----:|:--:|:------------:|:-----------:|:---------------:|
| **ikigai** | — | ISSUE-005 | ISSUE-004,015 | ISSUE-065 | ISSUE-033-35 | ISSUE-036-38 | ISSUE-039-41 |
| **pav** | ISSUE-013 | — | ISSUE-064 | ISSUE-062 | — | — | — |
| **docs** | — | — | — | — | — | — | — |
| **ci** | ISSUE-065 | ISSUE-062 | — | — | — | — | — |
| **mcp-tuiboard** | — | — | — | — | — | — | — |
| **mcp-taskdog** | ISSUE-013 | — | — | — | — | — | — |
| **mcp-solverforge** | — | — | ISSUE-056 | — | — | — | — |

### Label → Sprint quick map
| Sprint | # issues | Avg effort | Dominant severity | Dominant subsystem |
|--------|---------:|-----------:|-------------------|---------------------|
| 1 | 16 | ~1.5d | critical/high | ikigai + pav |
| 2 | 12 | ~0.9d | high/medium | ikigai |
| 3 | 13 | ~1.2d | high | ikigai + mcp-* |
| 4 | 25 | ~1.1d | medium/info | ikigai + pav + docs |
| Backlog | 14 | ~1.2d | medium | docs + ci + feature |

### Effort envelope
- **Critical-path to boot:** ISSUE-005 (PAV CLI restore, 5d) — single longest task in Sprint 1
- **Critical-path to observability:** ISSUE-034 (TUIBOARD SDK migration, 2d) — gates dual export
- **Critical-path to advanced:** ISSUE-043 + ISSUE-077 (Pydantic invariant, 5d each) — must be sequenced, not parallelized

---

*Algorithmic Life OS — GitHub Issues Backlog — 2026-08-27*
*Renumbered for GitHub-friendliness; original prefixes (C1-C5, S-H1, P1, TB-, TD-, SF-, M, H, I, G) preserved in each issue body for traceability.*
