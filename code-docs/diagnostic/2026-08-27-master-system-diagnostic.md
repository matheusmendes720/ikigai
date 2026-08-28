> **[SUPERSEDED 2026-08-28 — see master-branch-carro-chefe-2026-08-28]**
> Cross-cutting diagnostic of pre-pivot state (77+ issues across PAV, IKIGAI,
> vibe-ops, MCP servers). Many issues are reframed under deep-agent canonical
> (CLI broken → not a defect; OTel gaps → MCP contract; dual CLAUDE.md →
> boundaries added). For current sprint sequencing, see the 4 Proposta ADR
> decision package (2026-08-28).

# Master System Diagnostic — 2026-08-27

> **Scope:** Cross-cutting diagnostic of all known issues across the Algorithmic
> Life OS subsystems. Aggregates findings from the IKIGAI backend deep-dive,
> system design report, PAV kernel state, external MCP servers, and known
> gaps. **No code changes** — diagnostic + planning only.
>
> **Date:** 2026-08-27
> **Author:** Architecture (Claude Code session 44aa707a)
> **Status:** 🟡 Draft — pending user review

---

## 0. Sumário Executivo

77 issues across 5 subsystems:

| Bucket | Count | Blocking? |
|--------|------:|:---------:|
| 🔴 **Critical** (system won't start) | 10 | Yes |
| 🟠 **High** (functional but wrong) | 30 | Yes (delays) |
| 🟡 **Medium** (edge-case bugs) | 24 | No (workarounds exist) |
| 🔵 **Info** (design notes) | 13 | No |
| **Total** | **77** | — |

**Top 3 critical findings (system cannot start today):**

1. **PAV CLI is broken** (`604d6af` deletion cascade) — `pav`, `pav-os`, `operational` console scripts all fail because editable-install `.pth` files still point at deleted `apps/cli/src`. **No tests run.**
2. **Schema split-brain** — canonical 24-col `plan_entities` table (defined in `sqlite_adapter.py:18-80`) is never written to; runtime 11-col table is written by every commit. **Drift is permanent.**
3. **dcode ↔ IKIGAI MCP disconnect** — `ikigai-maintainer-mcp` is not registered in any `.mcp.json`. dcode cannot call IKIGAI tools via MCP. Only path: `Bash → ikigai.bat agent|chat`.

**Recommended priority order** (sequenced; safe to follow):

```
P0  →  P1  →  P2  →  P3
 ↓      ↓      ↓      ↓
1-3    4-12  13-25  26-77
```

---

## 1. IKIGAI Meta-Brain Issues

**Source:** `life-ops/ikigai/docs/IKIGAI_BACKEND_DEEP_DIVE_REPORT.md` (commit `48abd81`, 411 lines, 2026-08-26)
**Tracked as:** Tasks #12-#15 in session task list
**Target branch:** `life-ops/life-mcp-observability-worktree` → `feat/mcp-observability`

### 1.1 CRITICAL (5) — System won't boot

| ID | Issue | Location | Fix suggestion |
|----|-------|----------|----------------|
| **C1** | Missing Python env at `/tmp/ikigai-test/` | `mcp_config.json:4`, `start_mcp_gateway.sh:35` | Replace hardcoded path with `poetry run python` |
| **C2** | `~/.ikigai/` directory does not exist | bootstrap | Add `mkdir -p ~/.ikigai/{plan_entities,checkpoints,vault}`; server.py creates parent dir before `sqlite3.connect` |
| **C3** | Missing Python deps (`frontmatter`, `langchain_core`) | bootstrap | Run `poetry install`; commit `poetry.lock` (currently missing) |
| **C4** | `_read_entity` name collision | `server.py:207-239` | Rename line 224's `_read_entity` → `_read_plan_entity_by_table` |
| **C5** | `_TASKDOG_CLI` Windows path on Linux host | `tools.py:910-912` | Use `sys.platform` check + env-var override |

**Acceptance:** `ikigai.bat mcp` boots successfully; all 8 MCP tools return non-empty responses; taskdog CLI works from harness.

### 1.2 HIGH (6) — Functional but wrong

| ID | Issue | Location | Fix suggestion |
|----|-------|----------|----------------|
| **H1** | tuiboard config relative path | local | (locally fixed; verify path is absolute) |
| **H2** | Vault root mismatch | `tools.py:21` vs `server.py:109` | Align both to `Path(__file__).parent.parent.parent / "data" / "matheus"` |
| **H3** | solverforge `calendar.db` never existed | runtime | Seed mock calendar OR document why empty is acceptable |
| **H4** | B1 Blocker divergence (vault says RESOLVED, interfaces OPEN) | vault + taskdog #10 + tuiboard | Either supply graduation years + close tasks, or revert vault record to OPEN |
| **H5** | Dual LangGraph instances | `server.py:317` + `tools.py:269` | Use singleton `graph()` from `ikigai_wrapper.py` in both |
| **H6** | API base URL — verify MiniMax/Anthropic compatibility | `deepagents_harness.py` env vars | Document credential routing; confirm `api.minimax.io/anthropic` accepts Anthropic-format requests |

### 1.3 MEDIUM (5) — Edge cases

| ID | Issue | Location | Fix suggestion |
|----|-------|----------|----------------|
| **M1** | taskdog tag truncation | `taskdog_list_tasks` CLI | Set `COLUMNS=200` + `LINES=50` in subprocess env |
| **M2** | taskdog port :8000 must be running | gateway | Document requirement for direct `mcp_config.json` users |
| **M3** | grep-based JSON-RPC test | `start_mcp_gateway.sh:243-248` | Replace with proper JSON parsing |
| **M4** | tuiboard empty `configPath` | `tools.py:747` | Either omit param or pass actual config dir |
| **M5** | SOLVERFORGE_ROOT WSL2 path inconsistency | `start_mcp_gateway.sh:31` | Use `/mnt/c/Users/mathe/...` pattern (match TUIBOARD_ROOT) |

### 1.4 INFO (3) — Review only

| ID | Issue | Location | Fix suggestion |
|----|-------|----------|----------------|
| **I1** | LangGraph singleton module state | `graph.py:163-170` | Acceptable for prod; document testing workaround |
| **I2** | Silent `except: pass` on plan_entity write | `server.py:367-368` | At minimum log; better: raise + return error in tool result |
| **I3** | `_read_entity` fallback reads wrong table | (depends on C4) | Verify after C4 fix lands |

**IKIGAI total: 5 + 6 + 5 + 3 = 19 issues**

---

## 2. System Architecture Issues

**Source:** System design report (transient plan-mode artifact, 22 findings)
**Origin:** 5 Explore agents in parallel, 2026-08-26
**Target branch:** varies (cross-cutting)

### 2.1 CRITICAL (3)

| ID | Issue | Subsystem | Fix suggestion |
|----|-------|-----------|----------------|
| **S-C1** | Plan-entities schema split-brain (24-col canonical vs 11-col runtime) | IKIGAI + vibe-ops | Reconcile to single schema; migrate runtime writers (`commit.py:58-118` + `server.py:347-357`) to canonical 24-col |
| **S-C2** | dcode not connected to IKIGAI MCP server | dcode | Add `ikigai-maintainer-mcp` entry to `~/.claude/.mcp.json` |
| **S-C3** | Taskdog NOT used via MCP — CLI subprocess used instead | IKIGAI | Wire `taskdog` FastMCP server into IKIGAI tool registry; remove CLI subprocess path |

### 2.2 HIGH (8)

| ID | Issue | Location | Fix suggestion |
|----|-------|----------|----------------|
| **S-H1** | IKIGAI MCP server is stdio-only — no HTTP+SSE | `server.py:534` | Add HTTP+SSE transport toggle (currently `stdio_server()` only) |
| **S-H2** | `_MCP_SESSION_CACHE` never invalidated | `tools.py:550` | Clear on `RuntimeError` / timeout / process exit |
| **S-H3** | No retry / backoff / reconnection logic anywhere | `src/agents/tools.py` | Add circuit-breaker pattern (already designed in observability sprint spec #01) |
| **S-H4** | `interrupt_on = {"write_file": True}` only — 6 mutation tools bypass HITL | `deepagents_harness.py` | Expand to gate `ikigai_checkpoint(set)`, `ikigai_plan_cycle`, `ikigai_sync_vault`, `solverforge_create_event`, `tuiboard_update_task`, `tuiboard_create_task`, `taskdog_create_task`, `taskdog_complete_task` |
| **S-H5** | Monolithic agent — no subagents | `deepagents_harness.py` | Decompose into specialized sub-agents (planner, executor, observer, reflector) |
| **S-H6** | `ikigai_sync_vault` split-brain (two destinations) | `tools.py:355` writes `~/.ikigai/vault/cycle-*.md` vs `server.py:451` writes `data/matheus/ikigai_state/cycle-*.md` | Pick ONE destination; update callers |
| **S-H7** | Paths hard-coded (no env-var override) | `tools.py:638-640, 729-733, 910-912` | Move to config file or env vars; fail loudly if missing |
| **S-H8** | MCP server does not call `init_tracing()` | `server.py` | Add observability boot at module load (mirror `deepagents_harness.py:29`) |

### 2.3 MEDIUM (7)

| ID | Issue | Location | Fix suggestion |
|----|-------|----------|----------------|
| **S-M1** | Empty `persistence/` dir (code lives in `propagation/`) | `src/ikigai/persistence/` | Either move code or remove the dir |
| **S-M2** | No migrations — `CREATE TABLE IF NOT EXISTS` only | `sqlite_adapter.py`, `commit.py` | Add schema version + migration runner |
| **S-M3** | Pydantic entities violate `frozen=True, extra="forbid"` invariant | `src/ikigai/entities/*.py` (most use `extra="allow"`, `frozen=False`) | Decide: relax CLAUDE.md invariant OR convert entities (15 files affected) |
| **S-M4** | Zero MCP integration tests in IKIGAI | `tests/` | Mock subprocess + spawn real servers + exercise JSON-RPC |
| **S-M5** | No Pydantic factories for tests | `tests/` | Add `make_goal()`, `make_dream()` etc. to reduce boilerplate |
| **S-M6** | No mock backends for MCP servers in tests | `tests/` | Use `unittest.mock` to stub `_mcp_call_v1` / `_taskdog_run` |
| **S-M7** | `ikigai_score` fallback reads wrong table when checkpoint empty | (depends on C4 + I3) | Verify after C4 lands |

### 2.4 INFO (4)

| ID | Issue | Location | Fix suggestion |
|----|-------|----------|----------------|
| **S-I1** | 3 integration patterns for 3 external servers (inconsistent) | `tools.py` | Standardize on stdio MCP for all 3 |
| **S-I2** | TUI mutation surface is ZERO (read-only by design) | `apps/tui/` | Document architectural choice; add `pav <cmd>` shortcuts in TUI notify |
| **S-I3** | PAV TUI is in sibling workspace (`life-pav-cli`), not `life-ops/ikigai` | topology | Document in ARCHITECTURE_INDEX.md |
| **S-I4** | No "Press r to retry" UX in TUI | `analytics_screen.py:318-322` | Add retry keybinding to error overlay |

**System architecture total: 3 + 8 + 7 + 4 = 22 issues**

---

## 3. PAV Kernel Restoration

**Source:** `life/CLAUDE.md §Pitfalls` + git history (`604d6af`)
**Status:** 🟡 CLI broken; tests in `tests/unit/cli/` fail until restoration
**Target branch:** depends on restoration strategy

| ID | Issue | Severity | Fix suggestion |
|----|-------|:--------:|----------------|
| **P1** | PAV CLI broken — `pav`, `pav-os`, `operational` all fail | 🔴 Critical | Restore `apps/cli/src/operational/cli/` from git history pre-`604d6af`; recreate editable-install `.pth` files |
| **P2** | `tests/tui/` and `tests/ui/` orphaned (source deleted) | 🟠 High | Either restore apps OR delete tests |
| **P3** | `_PersistentRepo` 15 singletons pointing at `~/.time-tasker/*.json` | 🟠 High | Move to `~/.life-operational/` or document env var |
| **P4** | `ikigai.bat` hardcodes `.venv\Scripts\python.exe` path | 🟠 High | Make venv path env-var configurable |
| **P5** | `scripts/verify_sprint.sh` exists but `uv run verify_sprint` fails | 🟠 High | Add wrapper or remove from docs |
| **P6** | `Makefile test` uses `poetry run pytest` but workspace is `uv` | 🟡 Medium | Update Makefile target to `cd life-ops/operational && uv run pytest` |
| **P7** | Stray 0-byte files at repo root (`2`, `0`, `4}`, `dict[str`, `ISO`, etc.) | 🟡 Medium | Add `.gitignore` patterns; bulk delete |
| **P8** | Two CLAUDE.md files (root + `life-ops/operational/`) describe overlapping scopes | 🔵 Info | Document which is authoritative per concern |

**PAV total: 1 + 4 + 2 + 1 = 8 issues**

---

## 4. External MCP Servers (3 repos)

**Source:** System design report §5 + observability sprint status
**Target branches:** 3 separate worktrees (already created)

### 4.1 tuiboard (`apps/kanban/tuiboard/` — TypeScript/Bun)

| ID | Issue | Severity | Fix suggestion |
|----|-------|:--------:|----------------|
| **TB-1** | Zero OTel instrumentation | 🟠 High | Dual OTLP/HTTP export (done in `feat/otel-tracing`, commit `2c39867`) — pending merge |
| **TB-2** | Hand-rolled JSON-RPC (no MCP SDK) | 🟠 High | Migrate to official MCP SDK or document the choice |
| **TB-3** | No retry/CB on stdin/stdout MCP calls | 🟠 High | Mirror observability sprint spec #01 |
| **TB-4** | 5 tools — `board.list`, `board.tasks.get/update/create/delete` | 🟡 Medium | Add `board.tasks.archive` for soft-delete (IKIGAI uses this pattern) |
| **TB-5** | No structured logging | 🟡 Medium | Add Bun-native JSON logger with trace_id correlation |
| **TB-6** | No version pinning in `package.json` | 🔵 Info | Pin MCP SDK, OpenTelemetry SDK |

### 4.2 taskdog (`apps/dev-tools/taskdog/` — Python FastMCP)

| ID | Issue | Severity | Fix suggestion |
|----|-------|:--------:|----------------|
| **TD-1** | Zero OTel instrumentation | 🟠 High | Dual OTLP/HTTP export (done in `feat/otel-tracing`, commit `600c92b9`) — pending merge |
| **TD-2** | CLI truncation issue (M1 above) | 🟠 High | Set `COLUMNS=200`, `LINES=50` in subprocess env |
| **TD-3** | HTTP server `:8000` must be running | 🟠 High | Auto-start on IKIGAI boot OR document |
| **TD-4** | Tag truncation in CLI output | 🟡 Medium | Same as TD-2 |
| **TD-5** | No CB / retry on server calls | 🟡 Medium | Mirror observability sprint spec #01 |
| **TD-6** | Config at `~/.config/taskdog/mcp.toml` (XDG) | 🔵 Info | Document env override |

### 4.3 solverforge-calendar (`apps/calendar/solverforge-calendar/` — Rust rmcp)

| ID | Issue | Severity | Fix suggestion |
|----|-------|:--------:|----------------|
| **SF-1** | Zero OTel instrumentation | 🟠 High | Dual OTLP/HTTP export (done in `feat/otel-tracing`, commits `cfbf12b`, `064b8c9`) — pending merge |
| **SF-2** | `calendar.db` never seeded | 🟠 High | Seed mock calendar (H3) OR document empty state |
| **SF-3** | WSL2 path inconsistency (M5 above) | 🟡 Medium | Standardize `/mnt/c/Users/mathe/...` |
| **SF-4** | HTTP+SSE transport stub but never enabled | 🟡 Medium | Wire feature flag for prod deployment |
| **SF-5** | 16 tools — `calendars_*`, `projects_*`, `events_*`, `dependencies_*`, `google_sync`, `upi_*` | 🔵 Info | Document tool taxonomy in IKIGAI README |
| **SF-6** | Build feature flag `[features] http = []` required | 🔵 Info | Already fixed in `1716b16` |

**External MCP total: 0 + 9 + 6 + 3 = 18 issues**

---

## 5. Known Gaps & Cross-Cutting Pitfalls

**Source:** `code-docs/00-INDEX.md §12` + `CLAUDE.md §Pitfalls` + `life/CLAUDE.md §Pitfalls`

| ID | Issue | Severity | Fix suggestion |
|----|-------|:--------:|----------------|
| **G1** | `code-docs/adr/README.md` does not exist | 🔴 Critical | Create stub README pointer |
| **G2** | IKIGAi vector count mismatch (root says 5, PRD-07 says 4) | 🟠 High | Promote PRD-07 to 5 vectors OR roll root docs to 4 — **user decision needed** |
| **G3** | ADRs in 3 separate places (no canonical surface) | 🟠 High | Build cross-link table in `code-docs/00-INDEX.md §7` |
| **G4** | `vibe-ops/specs/` carries deprecated v1 schemas | 🟠 High | Add `DEPRECATED` frontmatter to v1 files; point readers to v2 |
| **G5** | Operational docs count is approximate | 🟡 Medium | Enumerate from in-folder READMEs |
| **G6** | Stray 0-byte files at repo root (P7 above) | 🟡 Medium | Same as P7 |
| **G7** | Throwaway files at `life-ops/operational/` root (`output.txt`, `CheckResult`, `not`) | 🟡 Medium | `.gitignore` patterns + cleanup |
| **G8** | Two CLAUDE.md files (P8 above) | 🔵 Info | Same as P8 |
| **G9** | `ikigai.bat` venv path hardcoded (P4 above) | 🟡 Medium | Same as P4 |
| **G10** | `scripts/verify_sprint.sh` vs `uv run verify_sprint` mismatch (P5 above) | 🟡 Medium | Same as P5 |

**Cross-cutting total: 1 + 3 + 4 + 2 = 10 issues**

---

## 6. Pending Constructions (priority roadmap)

These are planned-but-not-implemented features. All are independent of the
issue backlog above but compete for engineering time.

| Priority | Construction | Status | Branch | Effort |
|:--------:|--------------|:------:|--------|--------|
| **A** | AI-native strategic model migration (PAV TUI/CLI deprecated → MCP contracts only) | 🟡 Planned | (new branch) | 8 weeks |
| **B** | HTTP+SSE transport for IKIGAI MCP server | 🟡 Spec exists | (new branch) | 1 week |
| **C** | Subagents decomposition (specialized: planner/executor/observer/reflector) | 🟡 Planned | (new branch) | 3 weeks |
| **D** | `@observed_tool` decorator on all 18 production tools | 🟡 Latent | follows S-H8 | 2 days |
| **E** | `interrupt_on` expansion (gate 6+ mutation tools) | 🟡 Planned | follows S-H4 | 1 week |
| **F** | Schema split-brain reconciliation (single canonical writer) | 🔴 Required | (new branch) | 2 weeks |
| **G** | dcode MCP registration (`ikigai-maintainer-mcp` in `.mcp.json`) | 🔴 Required | quick fix | 1 day |
| **H** | PAV CLI restoration (post-`604d6af`) | 🔴 Required | (recovery branch) | 1 week |
| **I** | Vector count reconciliation (5 vs 4) | 🟡 User-decision | (depends on G2) | 1 day |
| **J** | MCP integration tests (mock + real servers) | 🟡 Planned | follows S-M4 | 1 week |

---

## 7. Suggested Fix Sequence (P0 → P3)

### P0 (Days 1-3) — Unblock system boot

1. **C2** mkdir `~/.ikigai/` + bootstrap dirs
2. **C3** `poetry install` + commit `poetry.lock`
3. **C1** fix `mcp_config.json` + `start_mcp_gateway.sh` python paths
4. **G1** create `code-docs/adr/README.md`
5. **P1** restore PAV CLI from pre-`604d6af` snapshot

### P1 (Days 4-10) — Functional correctness

6. **C4** rename `_read_entity` collision
7. **C5** platform-aware `_TASKDOG_CLI`
8. **H2** vault root alignment
9. **H4** B1 blocker resolution (supply years OR revert)
10. **H5** singleton LangGraph in both call sites
11. **S-C1** schema split-brain (canonical 24-col everywhere)
12. **S-C2** dcode MCP registration
13. **G2** vector count decision (user)

### P2 (Days 11-20) — Reliability + observability

14. **H3** seed solverforge OR document empty
15. **S-H1** HTTP+SSE transport for IKIGAI MCP
16. **S-H2** invalidate `_MCP_SESSION_CACHE` on error
17. **S-H3** retry/CB pattern (observability sprint spec #01)
18. **S-H8** `init_tracing()` in MCP server module load
19. **TB-1, TD-1, SF-1** merge OTel feature branches (3 repos)
20. **S-H7** env-var override for hard-coded paths

### P3 (Days 21+) — Cleanup + advanced

21. **S-H4** `interrupt_on` expansion (HITL on 6+ tools)
22. **S-H5** subagents decomposition
23. **S-H6** unify `ikigai_sync_vault` destinations
24. **S-M2** schema migrations runner
25. **S-M3** decide Pydantic invariant + convert entities
26. **M1-M5** edge-case fixes
27. **G3-G10** documentation + cleanup

---

## 8. Verification Commands

```bash
# IKIGAI backend
cd "C:\Users\mathe\code_space\life-oss\life\life-ops\ikigai"
ls ~/.ikigai/                                              # verify C2
poetry install                                             # verify C3
python -m ikigai.cli.app health                           # verify C1
ikigai.bat mcp                                             # verify C4, C5

# PAV kernel
cd "C:\Users\mathe\code_space\life-oss\life\life-ops\operational"
uv run ruff check packages/core/src/                       # verify P1 baseline
uv run pytest --collect-only -q | tail -1                  # count tests

# External MCP servers
cd "C:\Users\mathe\code_space\apps\kanban\tuiboard"
git log --oneline feat/otel-tracing | head -5              # verify TB-1
cd "C:\Users\mathe\code_space\apps\dev-tools\taskdog"
git log --oneline feat/otel-tracing | head -5              # verify TD-1
cd "C:\Users\mathe\code_space\apps\calendar\solverforge-calendar"
git log --oneline feat/otel-tracing | head -5              # verify SF-1

# dcode connection
cat ~/.claude/.mcp.json | jq '.mcpServers | keys'          # verify S-C2

# Repo hygiene
ls "C:\Users\mathe\code_space\life-oss\life\" | head -20    # verify G6 (stray files)
```

---

## 9. Cross-Reference Map

```
IKIGAI backend (§1)
├── C1-C5 → Tasks #12 (in session task list)
├── H1-H6 → Tasks #13
├── M1-M5 → Tasks #14
└── I1-I3 → Tasks #15

System architecture (§2)
├── S-C1-C3 → blocked by §1 C4 + §3 P1
├── S-H1-H8 → depends on observability sprint merge
└── S-M1-M7 → cosmetic + test additions

PAV kernel (§3)
└── P1-P8 → recovery branch (pre-`604d6af` snapshot)

External MCP (§4)
├── TB-1 → merged in `feat/otel-tracing` (commit 2c39867)
├── TD-1 → merged in `feat/otel-tracing` (commit 600c92b9)
└── SF-1 → merged in `feat/otel-tracing` (commits cfbf12b, 064b8c9)

Known gaps (§5)
└── G1-G10 → §Pitfalls in CLAUDE.md + 00-INDEX.md §12

Pending constructions (§6)
├── A — AI-native strategic model migration
├── B-J — see individual cards
```

---

## 10. Maintenance Rules

When adding a new issue to this diagnostic:

1. **Append-only** — never delete an existing entry (even after resolution). Mark resolved issues with ✅ and link to fix commit.
2. **Severity legend** — Critical (system won't start) / High (functional but wrong) / Medium (edge case) / Info (design note)
3. **Cross-reference** — link to canonical source (file + line range)
4. **Fix suggestion** — every issue has a recommended resolution
5. **Target branch** — every issue names where the fix lands
6. **One ID per issue** — use the subsystem prefix (C/H/M/I, S-C/S-H/S-M/S-I, P, TB/TD/SF, G)
7. **Update counts in README** — bump totals
8. **Update Tasks list** — link to session TaskCreate ID when applicable

---

*Master Diagnostic — v1.0 — 2026-08-27 — diagnostic + planning only, no code changes this turn*
