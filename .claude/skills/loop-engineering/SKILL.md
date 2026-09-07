---
name: loop-engineering
description: The discipline of designing the system that prompts, checks, remembers, and re-runs an AI agent — instead of a human doing it by hand. Use when you have a spec, a roadmap, and want the agent to keep advancing without your input. Triggers on keywords "loop", "loop engineering", "autonomous", "ralph", "long-running", "sub-agent orchestration", "SDD loop", "agentic loop".
version: 1.0.0
created: 2026-09-06
tier: production-ready
---

# Loop Engineering Skill (life-oss edition)

> **Adapted for life-oss.** This skill implements the loop engineering pattern on top of the existing `claude-flow v3` + Agent Teams + IKIGAi MCP infrastructure. **Do not install another orchestrator** — wire into what's here.

## When to invoke this skill

- ✅ You have a **roadmap** with sequenced milestones
- ✅ You have **specs** that define acceptance criteria
- ✅ You want the agent to **advance one milestone per tick** without prompting
- ✅ You have a **budget cap** and want to monitor cost
- ❌ Don't use for: ad-hoc one-off questions, refactors that need human judgment, anything requiring strong invariants that the agent might violate (Ronacher's warning)

## The 4 loops stacked (LangChain framework)

```
LOOP 4: Hill-Climbing (weekly — improves the harness itself)
  LOOP 3: Event-Driven (cron — triggers ticks)
    LOOP 2: Verification (sub-agent — judges work)
      LOOP 1: Agent (ReAct — does work)
```

## The 6 building blocks (Osmani framework)

| Block | life-oss implementation |
|---|---|
| 1. **Automations** (heartbeat) | `claude-flow daemon schedules` + custom `loop-tick.{sh,bat}` |
| 2. **Worktrees** | `git worktree` per sub-agent (see `scripts/worktree-helper.sh`) |
| 3. **Skills** | `.claude/skills/*` (this skill is one of 41) |
| 4. **Plugins/connectors** | IKIGAi MCP server (19 tools), `.mcp.json` |
| 5. **Sub-agents** | `.claude/agents/loop/{orchestrator,worker,verifier}.md` |
| 6. **Durable state** | `.claude/loop/{roadmap,tasks,progress,constitution}.md` + `.swarm/memory.db` |

## The 3 agents you have

| Agent | File | Role | Model |
|---|---|---|---|
| **orchestrator** | `.claude/agents/loop/orchestrator.md` | Strategy→Execute→Verify state machine. Reads state, picks next milestone, spawns worker + verifier. | claude-opus-4-8 (default) |
| **worker** | `.claude/agents/loop/worker.md` | Maker. Implements 1 task. Runs tests, commits, exits. | claude-sonnet-4-5 |
| **verifier** | `.claude/agents/loop/verifier.md` | Checker. Different model. Scores 1-5 on 5 dimensions. Returns JSON verdict. | claude-haiku-4-5 |

## The 5 files you maintain

| File | Owner | Update rule |
|---|---|---|
| `roadmap.md` | You (human) | High-level sequence. Add/remove milestones. |
| `tasks.md` | Orchestrator (auto) | Concrete tasks derived from roadmap. |
| `progress.md` | All (append-only) | One line per tick. Never edit past lines. |
| `constitution.md` | You (human, rare) | Project principles. Gates every milestone. |
| `specs/*/SPEC.md` | You (per milestone) | Acceptance criteria for each milestone. |

## The tick (one cycle of the loop)

```
[cron fires]
  → orchestrator reads state, picks next milestone
  → spawns worker in worktree
  → worker implements, tests, commits
  → spawns verifier in same worktree
  → verifier scores 1-5, returns JSON
  → orchestrator appends to progress.md
  → if PASS: roadmap.md marked done, next milestone unlocked
  → if FAIL × 2: write BLOCKED, notify human
  → if NEEDS_FIX: human jolt
  → tick ends
```

## How to invoke (3 ways)

### 1. Manual tick (always do first)
```bash
# bash
bash .claude/loop/loop-tick.sh

# Windows
.claude\loop\loop-tick.bat
```

### 2. Scheduled tick (after 3-5 successful manual ticks)
```bash
# Add to claude-flow daemon schedules
bash .claude/helpers/daemon-manager.sh add \
  --name "loop-tick" \
  --interval "60m" \
  --command "bash .claude/loop/loop-tick.sh" \
  --cost-cap-usd "5"
```

### 3. One-shot cron
```bash
# In claude-flow
npx claude-flow cron once \
  --name "loop-tick-now" \
  --command "bash .claude/loop/loop-tick.sh" \
  --at "+0m"
```

## Safety rails (NON-NEGOTIABLE)

1. **Hard cost cap:** `--cost-cap-usd 5` per tick
2. **Hard iteration cap:** `--max-iterations 8` per tick
3. **Hard timeout:** `--max-runtime-min 30` per tick
4. **Deterministic gates BEFORE LLM judge:** tests + lint + types must pass first
5. **Human jolt for NEEDS_FIX:** notify channel (Telegram/Feishu/email)
6. **Weekly hill-climb:** review traces, propose AGENTS.md updates, no auto-merge
7. **Constitution gate:** every milestone checked against `constitution.md` principles
8. **Append-only progress.md:** never edit past lines (git tracks history)
9. **No defensive code for impossible states:** (Ronacher's warning, enforced in verifier rubric)
10. **Reviewer is different model:** verifier uses haiku, worker uses sonnet, orchestrator uses opus

## Verifier rubric (JSON output)

```json
{
  "verdict": "PASS|FAIL|NEEDS_FIX",
  "scores": {
    "correctness": 1-5,   // meets spec acceptance criteria
    "minimality": 1-5,    // diff is small and focused
    "coherence": 1-5,     // follows existing patterns
    "safety": 1-5,        // no defensive code for impossible states
    "reversibility": 1-5  // easy to roll back
  },
  "deterministic_gates": {
    "tests": "pass|fail",
    "lint": "pass|fail",
    "types": "pass|fail"
  },
  "notes": "specific, actionable, ≤500 chars",
  "blockers": ["list of must-fix items if FAIL"]
}
```

**Threshold for PASS:** all deterministic gates pass AND average score ≥ 4.0 AND no score < 3.

## Failure modes & responses

| Failure | Response |
|---|---|
| Worker can't complete in budget | FAIL × 1 → retry with feedback; FAIL × 2 → BLOCKED + human |
| Verifier says FAIL but you disagree | NEEDS_FIX → human decides, write resolution to `progress.md` |
| Tick exceeds 30 min | Hard kill; mark in progress.md as OVERRUN; next tick continues |
| Cost spike (>$5) | Hard kill; alarm in progress.md; reduce `--cost-cap-usd` to $2 for next tick |
| Constitution violation | FAIL immediately; orchestrator writes CONSTITUTION_VIOLATION to progress.md |
| Spec ambiguous | NEEDS_FIX → human writes clarification to `specs/*/SPEC.md` |

## Provenance

This skill synthesizes the canonical loop engineering references (Sep 2026):

- **Addy Osmani, "Loop Engineering"** (jun 2026) — 6 building blocks
- **LangChain, "The Art of Loop Engineering"** (jun 2026) — 4 nested loops
- **TheBotCompany** (arXiv:2603.25928, mar 2026) — Strategy→Execute→Verify state machine
- **Armin Ronacher, "The Coming Loop"** (jun 2026) — risk framework
- **snarktank/ralph** (21.7k⭐) — completion promise pattern
- **mikeyobrien/ralph-orchestrator** (3.1k⭐) — circuit breaker + spend cap
- **ghuntley/how-to-ralph-wiggum** — 3 Phases, 2 Prompts, 1 Loop
- **zeroshot** (1.7k⭐) — executor-verifier split
- **kanban-md** (183⭐) — file-based state

See `.claude/loop/CURATED-TECHNIQUES.md` for the full curadoria with star counts and X traction.
