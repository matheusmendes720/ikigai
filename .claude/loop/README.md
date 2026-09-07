# Loop Engineering — life-oss Implementation

> **Status:** Bootstrap (M0 in progress)
> **Created:** 2026-09-06
> **Pattern:** Strategy→Execute→Verify state machine, 4 nested loops, 6 building blocks

## Quick Start

```bash
# 1. Dry run (shows what would happen)
bash .claude/loop/loop-tick.sh --dry-run

# Windows:
.claude\loop\loop-tick.bat --dry-run

# 2. First manual tick
bash .claude/loop/loop-tick.sh

# 3. Verify it worked
cat .claude/loop/progress.md

# 4. Schedule via claude-flow daemon (after 3-5 successful manual ticks)
bash .claude/helpers/daemon-manager.sh add \
  --name "loop-tick" \
  --interval "60m" \
  --command "bash .claude/loop/loop-tick.sh" \
  --cost-cap-usd 5
```

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│  LOOP 4: Hill-Climb (weekly)                                    │
│  └─ .claude/loop/hill-climb.sh — proposes AGENTS.md updates     │
│    ┌──────────────────────────────────────────────────────────┐ │
│    │  LOOP 3: Event-Driven (cron 60m)                          │ │
│    │  └─ claude-flow daemon → loop-tick.sh                     │ │
│    │    ┌────────────────────────────────────────────────────┐ │ │
│    │    │  LOOP 2: Verification (sub-agent)                  │ │ │
│    │    │  └─ .claude/agents/loop/verifier.md (haiku)         │ │ │
│    │    │    ┌──────────────────────────────────────────────┐ │ │ │
│    │    │    │  LOOP 1: Agent (ReAct)                       │ │ │ │
│    │    │    │  └─ .claude/agents/loop/worker.md (sonnet)   │ │ │ │
│    │    │    │     worktree + tests + commit                │ │ │ │
│    │    │    └──────────────────────────────────────────────┘ │ │ │
│    │    └────────────────────────────────────────────────────┘ │ │
│    └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘

       orchestrator (opus)  →  reads state, picks next task
                              ↑
       .claude/agents/loop/orchestrator.md
```

## Files in this directory

| File | Purpose | Owner |
|---|---|---|
| `roadmap.md` | Sequenced milestones (M0, M1, ...) | Human (high-level) |
| `tasks.md` | Atomic tasks per milestone | Orchestrator (auto) |
| `progress.md` | Append-only tick log | All (append only) |
| `constitution.md` | Project principles (gates every milestone) | Human (rare) |
| `loop-tick.sh` | Bash loop tick (Ralph-style) | Bash |
| `loop-tick.bat` | Windows wrapper for tick | cmd |
| `hill-climb.sh` | Weekly self-improvement (Loop 4) | Bash |
| `CURATED-TECHNIQUES.md` | The 35+ sources we synthesized | Reference |
| `README.md` | This file | You |

## Files in the parent directories

| File | Purpose |
|---|---|
| `../agents/loop/orchestrator.md` | The orchestrator agent (opus) |
| `../agents/loop/worker.md` | The worker sub-agent (sonnet) |
| `../agents/loop/verifier.md` | The verifier sub-agent (haiku) |
| `../skills/loop-engineering/SKILL.md` | The skill doc (auto-invoked) |
| `../../scripts/worktree-helper.sh` | Git worktree isolation |

## How a tick flows

```
[cron fires every 60min]
  ↓
bash .claude/loop/loop-tick.sh
  ↓
Invokes orchestrator with state-reading prompt
  ↓
Orchestrator reads constitution → roadmap → tasks → progress
  ↓
Picks next pending task from tasks.md
  ↓
Creates worktree via scripts/worktree-helper.sh create m-{id}
  ↓
Spawns worker (sonnet) in worktree
  ↓
Worker: implements, tests, commits, returns JSON status
  ↓
Spawns verifier (haiku) in same worktree
  ↓
Verifier: runs deterministic gates (pytest, ruff, mypy)
  ↓
If gates pass: scores 1-5 on 5 dimensions
  ↓
Returns JSON verdict {PASS|FAIL|NEEDS_FIX}
  ↓
Orchestrator appends to progress.md
  ↓
If PASS: marks milestone DONE in roadmap.md, creates next task
If FAIL × max: writes BLOCKED
If NEEDS_FIX: appends notes, next tick retries
  ↓
Tick exits
  ↓
[60min later, cron fires again]
```

## Safety Rails

1. **Hard cost cap:** $5/tick (configurable via `--cost-cap`)
2. **Hard runtime cap:** 30min/tick (configurable via `--max-runtime`)
3. **Daily cap:** $50/day (10x per-tick cap)
4. **Deterministic gates:** pytest, ruff, mypy must pass before LLM judge
5. **Different models:** worker=sonnet, verifier=haiku, orchestrator=opus
6. **Constitution gate:** every milestone checked against `constitution.md`
7. **Append-only progress.md:** never edit past lines
8. **No self-modify:** orchestrator cannot change constitution/AGENTS/CLAUDE
9. **Weekly hill-climb:** proposes improvements, no auto-merge
10. **Worktree isolation:** per sub-agent, auto-cleanup

## Inspiration / Provenance

This implementation synthesizes (in order of influence):

1. **snarktank/ralph** (21.7k⭐) — the completion-promise bash loop
2. **Addy Osmani "Loop Engineering"** (jun 2026) — the 6 building blocks
3. **LangChain "Art of Loop Engineering"** (jun 2026) — the 4 nested loops
4. **TheBotCompany** (arXiv:2603.25928) — Strategy→Execute→Verify state machine
5. **mikeyobrien/ralph-orchestrator** (3.1k⭐) — circuit breaker + spend cap
6. **ghuntley/how-to-ralph-wiggum** — 3 Phases, 2 Prompts, 1 Loop
7. **the-open-engine/zeroshot** (1.7k⭐) — executor-verifier split
8. **antopolskiy/kanban-md** (183⭐) — file-based state
9. **Addy Osmani "Agentic Code Review"** (jun 2026) — "tier by risk, not by author"
10. **Armin Ronacher "The Coming Loop"** (jun 2026) — risk framework

See `CURATED-TECHNIQUES.md` for the full curadoria with star counts and X traction.

## Existing infrastructure we wired into (not replaced)

- **claude-flow v3** — `.claude/settings.json:178-284` (Agent Teams, swarm, daemon schedules)
- **IKIGAi MCP server** — `.mcp.json` (19 tools: 12 IKIGAI + 7 fork)
- **3 LangGraph graphs** — `langgraph.json:6-10`
- **41 skills** — `.claude/skills/`
- **18 specialized agents** — `.claude/agents/`
- **`.swarm/memory.db`** — cross-session memory (172KB SQLite)
- **Daemon manager** — `.claude/helpers/daemon-manager.sh`
- **Hook handler** — `.claude/helpers/hook-handler.cjs`
- **3 SPEC.md files** — `specs/{agentic-markdown-system,period-reports-sync,vault-bidirectional-sync}/`

The loop engineering pattern is the **glue** that ties all of this together. It does NOT replace any of it.
