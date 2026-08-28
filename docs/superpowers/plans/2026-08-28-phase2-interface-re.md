# Phase 2 — Interface Reverse-Engineering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce deep reverse-engineering documentation of 3 fork MCP servers + interfaces/cli + interfaces/tui to inform Phase 3 data mesh unification.

**Architecture:** Each fork gets its own RE doc (components, widgets, states, routes, MCP server, trade-offs). Cross-fork synthesis identifies opportunities for Phase 3 mesh unification. Output is 6 markdown files + 1 INDEX.

**Tech Stack:** Existing forks (tuiboard: TS/Bun, taskdog: Python/uv, solverforge-calendar: Rust/Cargo), interfaces/cli (Python/Typer), Claude Agent SDK for subagent dispatch.

## Global Constraints

- **Scope:** RE only — no code changes, no patches, no design decisions. Deliverables are documentation files.
- **Format:** 1 INDEX + 6 docs in `docs/diagnostics/2026-08-28-phase2-interface-re/`. Each doc ≤500 lines (CLAUDE.md rule).
- **Notation:** Match Phase 1 conventions — file:line citations verbatim, no editorial paraphrasing. Cross-reference Phase 1 audit at `docs/diagnostics/2026-08-28-phase1-audit/`.
- **Q2 scope compliance:** This is investigation. Do NOT propose fixes or design changes — those go to Phase 3 brainstorm.
- **Verification standard:** Each doc must have: (1) component map, (2) state diagram, (3) route table, (4) MCP tool inventory, (5) trade-offs section, (6) cross-references to Phase 1 audit.

---

## File Structure

```
docs/diagnostics/2026-08-28-phase2-interface-re/
├── 00-INDEX.md                    (~80L) — file map, headline findings, cross-refs to Phase 1
├── 01-fork-tuiboard.md           (~400L) — tuiboard RE: components, widgets, states, MCP server
├── 02-fork-taskdog.md            (~400L) — taskdog RE
├── 03-fork-solverforge-calendar.md (~400L) — solverforge-calendar RE
├── 04-interfaces-cli.md          (~200L) — interfaces/cli RE (Typer-based)
├── 05-interfaces-tui.md          (~150L) — interfaces/tui RE (README-only placeholder)
└── 06-synthesis-mesh-readiness.md (~300L) — cross-fork synthesis for Phase 3
```

**Responsibility split:**
- Fork docs (1-3) document independent systems. No cross-imports.
- interfaces/cli/tui docs (4-5) document native interface layer.
- Synthesis (6) consumes 1-5, identifies mesh design opportunities.

---

## Task 1: Fork tuiboard RE

**Files:**
- Create: `docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md`
- Read: `C:\Users\mathe\code_space\life-oss\interfaces\tuiboard\` (113 source files)

**Interfaces:**
- Consumes: Phase 1 audit §4 (mcp-gateway wires `board_*` to tuiboard)
- Produces: tuiboard component map, MCP tool inventory, state diagram, route table, trade-offs

- [ ] **Step 1: Read Phase 1 audit §4 + fork directory structure**

```bash
cd /c/Users/mathe/code_space/life-oss/interfaces/tuiboard
ls -la
cat package.json | head -50
```

Expected: tuiboard v0.8.4, dependencies `@opentui/solid`, `solid-js`, `zod`, `chokidar`, `@opentelemetry/sdk-node`. MCP entry: `bin/tuiboard.ts` (TUI), `bin/tuiboard-mcp.ts` (MCP server).

- [ ] **Step 2: Dispatch subagent — tuiboard component map**

Dispatch a `general-purpose` subagent with prompt: "Read all source files under `C:/Users/mathe/code_space/life-oss/interfaces/tuiboard/src/` (TS/Solid). Produce a component map: for each component, document name, file path, props, state, events. List all widgets (buttons, modals, lists, etc). Identify the state store (likely Solid signals/stores). Return findings as a structured report."

Expected output: ~30-50 component entries with file:line citations.

- [ ] **Step 3: Dispatch subagent — tuiboard MCP server**

Dispatch a `general-purpose` subagent with prompt: "Read `C:/Users/mathe/code_space/life-oss/interfaces/tuiboard/bin/tuiboard-mcp.ts` and all files it imports. Document: every MCP tool exposed (name, params, return schema), every JSON-RPC handler, transport details (stdio), error handling. Compare to Phase 1 gateway config: `gateways.yaml:4` routes `board_*` prefix here. List all `board_*` tools expected by gateway but check if tuiboard exposes them. Return findings as a structured report."

Expected output: complete MCP tool inventory + gateway-routing match matrix.

- [ ] **Step 4: Dispatch subagent — tuiboard state + persistence**

Dispatch a `general-purpose` subagent with prompt: "Read state management files in tuiboard (signals, stores, persistence layer). Document: state shape, persistence backend (likely in-memory or localStorage/file), state transitions, undo/redo if any, observability hooks (OTel spans). Return findings as a structured report."

Expected output: state shape + transition diagram + persistence story.

- [ ] **Step 5: Write RE doc**

Write `docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md` with sections:
- Component map (table: name, file, props, state)
- Widget inventory
- State diagram
- MCP tool inventory (table: tool name, params, returns, gateway prefix)
- Gateway routing match matrix
- Persistence story
- Trade-offs (file paths, dependency choices, observability gaps)
- Cross-references to Phase 1 audit (`04-sequencing.md` Step 0, `05-open-questions.md` OQ-8 MCP transports)

Target: ~400 lines.

- [ ] **Step 6: Verify doc has all 6 required sections**

Run: `grep -E "^## (Component map|Widget inventory|State diagram|MCP tool inventory|Trade-offs|Cross-references)" 01-fork-tuiboard.md`
Expected: 6 matches.

- [ ] **Step 7: Commit**

```bash
cd /c/Users/mathe/code_space/life-oss/life
git add docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md
git commit -m "docs(phase2): reverse-engineer fork tuiboard"
```

---

## Task 2: Fork taskdog RE

**Files:**
- Create: `docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md`
- Read: `C:\Users\mathe\code_space\life-oss\interfaces\taskdog\` (5 packages, 2,101 source files)

**Interfaces:**
- Consumes: Phase 1 audit §4 (gateway wires `taskdog_*`, `list_tasks`, `get_task`, etc. to taskdog)
- Produces: taskdog RE doc (5 packages: core, client, server, ui, mcp)

- [ ] **Step 1: Read Phase 1 audit §4 + 5-package structure**

```bash
cd /c/Users/mathe/code_space/life-oss/interfaces/taskdog
find . -name "pyproject.toml" -not -path "*/.venv/*" -not -path "*/node_modules/*"
```

Expected: 5 packages (taskdog-core, taskdog-client, taskdog-server, taskdog-ui, taskdog-mcp), each with own pyproject.toml.

- [ ] **Step 2: Dispatch subagent — taskdog core models + persistence**

Dispatch subagent: "Read `taskdog-core/` source files. Document: every entity model, database schema (likely SQLite or Postgres), migrations, repository pattern. Cross-reference Phase 1 audit §4: gateway config wires `taskdog_*` tools; identify which taskdog-core classes back those tools. Return findings."

- [ ] **Step 3: Dispatch subagent — taskdog MCP server**

Dispatch subagent: "Read `taskdog-mcp/` source files. Document: every MCP tool exposed (name, params, return schema), JSON-RPC handlers, transport (stdio per `pyproject.toml`), error handling. Compare to Phase 1 gateway config: `gateways.yaml:9` routes `taskdog_*` + `list_tasks`/`get_task`/`create_task` here. List ALL tools gateway expects vs what taskdog exposes. Note: gateway expects `taskdog_*` prefix but taskdog tools may be unprefixed. Identify prefix-mismatch if any."

- [ ] **Step 4: Dispatch subagent — taskdog client + UI**

Dispatch subagent: "Read `taskdog-client/` (HTTP API client) and `taskdog-ui/` (likely Textual or similar). Document: client API surface, UI components, event handling. Note OTel integration (per Phase 1 audit: `opentelemetry-api/sdk/exporter-otlp-proto-http` listed in deps)."

- [ ] **Step 5: Write RE doc**

Write `02-fork-taskdog.md` with sections:
- Package map (5 packages with roles)
- Core entity models (Phase 1 UEID-format relevance — `contracts/..._...` vs `ikigai` formats)
- Database schema + migrations
- MCP tool inventory (gateway prefix match matrix)
- Client API surface
- UI components (if any)
- OTel instrumentation
- Trade-offs (per-package coupling, prefix mismatch, observability depth)
- Cross-references to Phase 1 (`05-open-questions.md` OQ-1 storage topology, OQ-7 UEID join key, OQ-8 MCP transports)

Target: ~400 lines.

- [ ] **Step 6: Verify doc has all 6 required sections**

Run: `grep -E "^## (Package map|Core entity|MCP tool inventory|Trade-offs|Cross-references)" 02-fork-taskdog.md`

- [ ] **Step 7: Commit**

```bash
git add docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md
git commit -m "docs(phase2): reverse-engineer fork taskdog"
```

---

## Task 3: Fork solverforge-calendar RE

**Files:**
- Create: `docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md`
- Read: `C:\Users\mathe\code_space\life-oss\interfaces\solverforge-calendar\` (60 Rust source files)

**Interfaces:**
- Consumes: Phase 1 audit §4 (gateway wires `calendars_*`, `events_*`, `projects_*`, `dependencies_*`, `google_*`, `upi_*` to solverforge-calendar)
- Produces: solverforge-calendar RE doc (Rust, ratatui, google-calendar3, rrule)

- [ ] **Step 1: Read Phase 1 audit §4 + Cargo workspace**

```bash
cd /c/Users/mathe/code_space/life-oss/interfaces/solverforge-calendar
cat Cargo.toml | head -80
ls src/
ls src/bin/
```

Expected: ratatui 0.29, rmcp 3.1 (MCP), google-calendar3 7.0, keyring 3, rrule 0.14. MCP bin: `src/bin/solverforge-calendar-mcp.rs`.

- [ ] **Step 2: Dispatch subagent — solverforge-calendar modules + data**

Dispatch subagent: "Read `solverforge-calendar/src/` Rust modules. Document: module map, domain entities (events, calendars, projects, dependencies), persistence (rusqlite 0.38 — find the schema), google-calendar3 integration surface, rrule usage, keyring usage (likely OAuth token storage). Cross-reference Phase 1 audit: gateway config routes 6 prefixes here (`calendars_*`, `events_*`, `projects_*`, `dependencies_*`, `google_*`, `upi_*`)."

- [ ] **Step 3: Dispatch subagent — solverforge-calendar MCP server**

Dispatch subagent: "Read `src/bin/solverforge-calendar-mcp.rs` and its imports. Document: every MCP tool exposed (rmcp framework), JSON-RPC handlers, transport, error handling. Compare to gateway config: list 6 expected prefixes vs actual exposed tools. Identify prefix-mismatches (gateway expects `upi_*` but is that exposed?)."

- [ ] **Step 4: Dispatch subagent — solverforge-calendar TUI**

Dispatch subagent: "Read TUI source (ratatui-based). Document: TUI widgets, state management, keybindings, event handling. Note: this fork is the default gateway backend per `gateways.yaml:14`."

- [ ] **Step 5: Write RE doc**

Write `03-fork-solverforge-calendar.md` with sections:
- Module map (Rust crate structure)
- Domain entities + rusqlite schema
- google-calendar3 integration surface
- MCP tool inventory (6-prefix match matrix)
- TUI widgets + keybindings
- rrule + keyring usage
- Trade-offs (Google API coupling, prefix sprawl, observability)
- Cross-references to Phase 1 (`05-open-questions.md` OQ-5 federation vs single source)

Target: ~400 lines.

- [ ] **Step 6: Verify doc has all 6 required sections**

Run: `grep -E "^## (Module map|Domain entities|MCP tool inventory|Trade-offs|Cross-references)" 03-fork-solverforge-calendar.md`

- [ ] **Step 7: Commit**

```bash
git add docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md
git commit -m "docs(phase2): reverse-engineer fork solverforge-calendar"
```

---

## Task 4: interfaces/cli RE

**Files:**
- Create: `docs/diagnostics/2026-08-28-phase2-interface-re/04-interfaces-cli.md`
- Read: `C:\Users\mathe\code_space\life-oss\life\interfaces\cli\` (1 source file, ~206 lines)

**Interfaces:**
- Consumes: Phase 1 audit §4 (interfaces/cli/read_tasks.py, pyproject.toml with broken `life-tasks` script)
- Produces: interfaces/cli RE doc (Typer-based, reads `data/tasks.jsonl`)

- [ ] **Step 1: Read Phase 1 audit §4 + interfaces/cli structure**

```bash
cd /c/Users/mathe/code_space/life-oss/life/interfaces/cli
cat pyproject.toml
ls -la
cat read_tasks.py
```

Expected: `life-interface-cli` v0.1.0, deps `typer>=0.12`, `rich>=13.7`. Single file `read_tasks.py` with 3 commands (`list`, `done`, `stats`). Reads `data/tasks.jsonl` (MISSING per B-04).

- [ ] **Step 2: Dispatch subagent — interfaces/cli deep dive**

Dispatch subagent: "Read `interfaces/cli/read_tasks.py` (206 lines, Typer-based). Document: command signatures, JSON output format, filter logic, paths resolved. Cross-reference Phase 1 audit findings: B-04 (tasks.jsonl MISSING), critic gap #8 (`life-tasks` script broken — no `__init__.py`). Document the chain: `interfaces/cli/read_tasks.py:27-29 _tasks_path()`, line 105 `done` command, line 144 `data/feedback.jsonl` write. Identify: where would this CLI receive tasks from? (Answer: via `data/tasks.jsonl` produced by `vibe-ops/src/pipeline/daily_consolidator.py` — but producer is never invoked per B-04.) Return findings."

- [ ] **Step 3: Write RE doc**

Write `04-interfaces-cli.md` with sections:
- Command inventory (table: command, args, output, deps)
- JSON output format (sample for each command)
- Filter logic (by-horizon, by-done, by-limit)
- Data path (`data/tasks.jsonl` → reader, `data/feedback.jsonl` → writer)
- Broken script entry (`life-tasks`) per critic gap #8
- Producer-consumer gap (per B-04)
- Trade-offs (CLI vs TUI vs native, Typer vs Click, install drift)
- Cross-references to Phase 1 (`01-verified.md` B-04, `02-critic-gaps.md` #8, `04-sequencing.md` Step 0 PR-1)

Target: ~200 lines.

- [ ] **Step 4: Verify doc has all 6 required sections**

Run: `grep -E "^## (Command inventory|JSON output|Data path|Trade-offs|Cross-references)" 04-interfaces-cli.md`

- [ ] **Step 5: Commit**

```bash
git add docs/diagnostics/2026-08-28-phase2-interface-re/04-interfaces-cli.md
git commit -m "docs(phase2): reverse-engineer interfaces/cli"
```

---

## Task 5: interfaces/tui RE

**Files:**
- Create: `docs/diagnostics/2026-08-28-phase2-interface-re/05-interfaces-tui.md`
- Read: `C:\Users\mathe\code_space\life-oss\life\interfaces\tui\` (README-only)

**Interfaces:**
- Consumes: Phase 1 audit §4 (interfaces/tui = README-only placeholder per audit)
- Produces: gap analysis doc

- [ ] **Step 1: Read Phase 1 audit §4 + interfaces/tui README**

```bash
cd /c/Users/mathe/code_space/life-oss/life/interfaces/tui
cat README.md
ls -la
```

Expected: README-only (44 lines per audit). No pyproject.toml, no code, no entry point. README describes planned Textual TUIs (`daily-view`, `kanban`, `calendar`).

- [ ] **Step 2: Dispatch subagent — gap analysis**

Dispatch subagent: "Read `interfaces/tui/README.md` (44 lines). Document: what is planned (3 TUIs), what is missing (Textual deps, code, entry points, CI matrix per Phase 1 §6). Identify what would be needed to build each of the 3 planned TUIs. Return findings."

- [ ] **Step 3: Write RE doc**

Write `05-interfaces-tui.md` with sections:
- README summary (planned TUIs)
- Gap inventory (no code, no deps, no entry, no CI)
- Build requirements per planned TUI (Textual deps, layout, widgets)
- Trade-offs (TUI vs CLI vs web, Textual vs Ratatui vs custom)
- Cross-references to Phase 1 (`02-critic-gaps.md` empty `tests/tui/`)

Target: ~150 lines.

- [ ] **Step 4: Verify doc has all 6 required sections**

Run: `grep -E "^## (README summary|Gap inventory|Trade-offs|Cross-references)" 05-interfaces-tui.md`

- [ ] **Step 5: Commit**

```bash
git add docs/diagnostics/2026-08-28-phase2-interface-re/05-interfaces-tui.md
git commit -m "docs(phase2): reverse-engineer interfaces/tui (gap analysis)"
```

---

## Task 6: Cross-fork synthesis (mesh-readiness)

**Files:**
- Create: `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md`
- Create: `docs/diagnostics/2026-08-28-phase2-interface-re/00-INDEX.md`
- Read: tasks 1-5 outputs

**Interfaces:**
- Consumes: Tasks 1-5 RE docs
- Produces: Phase 3 mesh-readiness synthesis (opportunities, trade-offs, design inputs)

- [ ] **Step 1: Read all 5 RE outputs**

Read `01-fork-tuiboard.md`, `02-fork-taskdog.md`, `03-fork-solverforge-calendar.md`, `04-interfaces-cli.md`, `05-interfaces-tui.md`. Extract: MCP tool inventories, data paths, state shapes, OTel instrumentation, persistence backends, prefix conventions.

- [ ] **Step 2: Dispatch subagent — cross-fork comparison**

Dispatch subagent: "Compare the 3 forks' MCP tool inventories, data paths, persistence backends, prefix conventions, OTel instrumentation. Build a comparison matrix. Identify: (1) tool-name collisions or near-collisions, (2) shared data shapes, (3) prefix mismatch patterns, (4) observability gaps, (5) where data mesh could unify, (6) where federation makes more sense. Return findings as a structured report with comparison tables."

- [ ] **Step 3: Dispatch subagent — Phase 3 design input**

Dispatch subagent: "Based on the 3-fork comparison, produce a Phase 3 mesh-readiness assessment. For each of the 10 open questions in Phase 1 audit (`05-open-questions.md`), identify what new evidence the Phase 2 RE findings provide. Don't resolve the questions — just enrich them with Phase 2 evidence. Return findings."

- [ ] **Step 4: Write synthesis doc**

Write `06-synthesis-mesh-readiness.md` with sections:
- Cross-fork comparison matrix (tools, paths, backends, prefixes, OTel)
- Tool collision analysis
- Shared data shape candidates
- Phase 3 readiness per OQ (table: OQ-N, original question, new evidence from Phase 2)
- Trade-offs (mesh vs federation per fork)
- Cross-references to Phase 1 audit + 5 RE docs

Target: ~300 lines.

- [ ] **Step 5: Write INDEX**

Write `00-INDEX.md`:
- Header (date, scope, inputs from Phase 1, outputs to Phase 3)
- File map (1-line description per file)
- Headline findings (one line each: tuiboard/taskdog/solverforge/cli/tui state, mesh-readiness verdict)
- Cross-references

Target: ~80 lines.

- [ ] **Step 6: Verify all 7 docs have required sections**

Run: `for f in docs/diagnostics/2026-08-28-phase2-interface-re/*.md; do echo "$f"; grep -E "^## (Trade-offs|Cross-references)" "$f" || echo "MISSING"; done`
Expected: every file has Trade-offs + Cross-references sections.

- [ ] **Step 7: Final commit**

```bash
git add docs/diagnostics/2026-08-28-phase2-interface-re/
git commit -m "docs(phase2): cross-fork synthesis + INDEX for mesh-readiness"
```

---

## Self-Review Checklist

After writing this plan (already done inline):

- ✅ **Spec coverage:** All 6 deliverables mapped to tasks. Each task has its own doc output.
- ✅ **Placeholder scan:** No TBD/TODO. Every step has concrete action + expected output.
- ✅ **Type consistency:** Section names consistent across all 6 docs (`Trade-offs`, `Cross-references` always present).
- ✅ **File structure:** 7 files (INDEX + 6 docs) all under 500L target. No overlap in responsibility.
- ✅ **Notation:** `file:line` citations preserved from Phase 1; OQ-1..OQ-10 cross-referenced; PR-1..PR-5 distinguished from P0/P1/P2 severity.

---

## Total effort (rough)

- Task 1 (tuiboard): 1-2 days
- Task 2 (taskdog): 1-2 days
- Task 3 (solverforge-calendar): 1-2 days
- Task 4 (interfaces/cli): 0.5 day
- Task 5 (interfaces/tui): 0.5 day
- Task 6 (synthesis + INDEX): 1 day

**Total: ~5-7 days** (with subagent dispatch, can parallelize Tasks 1-3)

## Parallelization strategy

Tasks 1, 2, 3 are independent (3 different forks, different languages). Dispatch all 3 in one round (using Workflow tool with `parallel()`) for ~3-4× speedup. Tasks 4-5 are smaller and can be subagent-dispatched concurrently with Tasks 1-3. Task 6 depends on all previous tasks; run last.

## What's intentionally NOT in scope (per Q2 compliance)

- No design decisions (storage topology, contracts naming, UEID, MCP transports — all carry to Phase 3)
- No code changes (RE only — read, document, no patches)
- No Phase 3 brainstorming — Task 6 enriches OQs with Phase 2 evidence but doesn't resolve them