# Reports Index

> **Index of all deep-dive audit reports** for life-oss. Each report is
> a self-contained investigation that produces evidence (commands run, files
> read, counts) and actionable recommendations.
>
> Reports are organized by milestone. The user is the audience.

---

## Shipped Since M96 Audit

After the M96 gap analysis (only 4 of 26 taskdog tools wired), the user
chose **Option A (MCP-wire)** in M97a and shipped these milestones:

| Milestone | Commit | What it added |
|---|---|---|
| **M97b** | `873f0881` | `MultiServerMCPClient` wired into `_make_agent()` → deep-agent now has **38 tools** (12 IKIGAI + 26 MCP taskdog) |
| **M98** | `9b96e2b2` | `life v2 agent "<request>"` — one-shot deep-agent driver (JSON output + tool call trace) |
| **M99** | `be43accf` | `life v2 chat` — REPL driver + `_ensure_ikigai_src_on_path()` fix |
| **M100** | `1aeb1ec2` | `life taskdog *` — Typer sub-app exposing **all 26 MCP tools as direct CLI commands** (no LLM) |

**Net result**: every capability listed in M96 as missing is now reachable:
- Via LLM: `life v2 agent "cancel task #162"` or `life v2 chat`
- Via direct CLI: `life taskdog cancel-task --task-id 162`
- Via taskwarrior-style wrapper: `life task cancel 162`

---

## Active Reports

### M96 — Taskdog → Deep-Agent Tool Wiring Gap Report
**File**: [`M96-taskdog-deep-agent-gap-report.md`](M96-taskdog-deep-agent-gap-report.md)
**Date**: 2026-09-21
**Status**: ✅ RESOLVED via M97b + M98 + M99 + M100
**Severity**: HIGH — affects 85% of taskdog surface

**What's in it**:
- Audit of 3 layers of taskdog (CLI: 22 subcommands, REST: 36 endpoints, MCP: 26 tools)
- Current state (audit time): only 4 of 26 taskdog tools wired as LangChain `@tool` (15%)
- 22 missing capabilities listed (cancel/pause/decompose/dependency/update/etc.)
- 5 user-facing failure scenarios
- 3 proposed paths forward (MCP-wired, parameter expansion, status quo)
- Risk register + validation criteria for user

**Decision needed**: User picks one of:
- (A) Wire `taskdog-mcp` via `MultiServerMCPClient` to deep-agent (Option 2)
- (B) Extend `taskdog_create_task` with priority/tags/deadline params (Option 1)
- (C) Status quo — keep 4 tools, accept 85% surface gap

---

### M97 — Deep-Agent System Topology & Practical Usage Guide
**File**: [`M97-deep-agent-system-topology.md`](M97-deep-agent-system-topology.md)
**Date**: 2026-09-21
**Status**: PUBLISHED (descriptive, no decision needed)
**Purpose**: show user how to use the system TODAY + what each component does

**What's in it**:
- 5-layer topology diagram ASCII (User interfaces → Skills → v2 graph → Agents → Data)
- Layer-by-layer inspection (file paths, code paths, behaviors)
- 7 practical usage scenarios with status (works / partial / cannot)
- Honest limitations map (what deep-agent can / cannot do)
- Recommended next-steps prioritization (P0-P4)

**Reading path**:
- Read TL;DR first (5 min) → see what works today
- Then "Practical Usage Scenarios" (15 min) → understand your workflow options
- Then "What's Wired vs Not" → understand the gap from M96
- Skip the "Top-Level View" if you don't need architecture details

---

## How to Use This Index

1. **New to the system?** Read M97 from top to bottom (45 min).
2. **Deciding on M96 direction?** Read M96 + the "Practical Usage Scenarios" section in M97.
3. **Debugging a specific component?** Find the layer in M97's "Top-Level View" diagram, then drill into the relevant section.

---

## Report Conventions

Each report follows the same structure:
- **TL;DR**: 1-paragraph summary + decisive action
- **Context**: what triggered the report, what's the scope
- **Findings**: data with evidence (commands run, files read, counts)
- **Recommendations**: numbered, prioritized, with effort estimates
- **Cross-references**: links to other reports, source files, drift tests
- **Status**: DRAFT / READY FOR VALIDATION / PUBLISHED

---

## Adding a New Report

1. Create `reports/M{N}-{kebab-case-slug}.md`
2. Add a row to this index with file link + 1-line description
3. Reference the report from roadmap.md if it triggers a milestone
4. Update progress.md with the report's findings
