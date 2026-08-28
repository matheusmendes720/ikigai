> **[SUPERSEDED 2026-08-28 — see master-branch-carro-chefe-2026-08-28]**
> This document describes the pre-2026-08-26 PAV TUI/CLI era when 6 LangGraph
> graphs (PAE-maintainer + 4 swarm) were registered as canonical. PAV is now
> desativado; canonical flows are owned by deep-agent over forks-prontas widgets.

# LangGraph Dev - Single-Project Agentic Flows

> **Status:** Active · **Config:** `langgraph.json` · **Entry point:** `vibe-ops/src/langgraph_entry.py`

This project serves all 5 agentic flows (1 PAE-Maintainer + 4 swarm workflows) under a single `langgraph dev` server.

## Quick Start

```bash
# 1. Install langgraph CLI + dependencies
make install

# 2. Run all 5 graphs on port 2024
make dev

# 3. Open in browser
# Studio at http://localhost:2024
# API at http://localhost:2024/docs
```

## 5 Registered Graphs

| Graph ID | Wraps | Trigger | Use Case |
|----------|-------|---------|----------|
| `pae_maintainer` | `vibe-ops/src/agents/pae_maintainer/graph.py:run_pae_cycle` | curl POST or studio | Full PAE cycle (observe→plan→reflect→balance→commit) |
| `quarterly_replan` | `.claude/skills/quarterly-planner/workflows/quarterly-replan.yml` | Friday 6pm or on-demand | End-of-quarter replanning when verdict != PASS |
| `test_de_fogo_rollup` | `.../test-de-fogo-rollup.yml` | on-demand | 5-dimension Test de Fogo aggregation |
| `correction_protocol` | `.../correction-protocol.yml` | on kill_switch | Diagnose + recommend action when OVERLOAD |
| `dream_falsification` | `.../dream-falsification.yml` | daily 9am on Sonho<7d to switch | Evaluate FalsifiableHypothesis verdicts |

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  langgraph dev (port 2024)                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │  HTTP API + Studio                                │   │
│  └──────────────────────────────────────────────────┘   │
│                       │                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │  langgraph.json  (5 graph entries)                │   │
│  └──────────────────────────────────────────────────┘   │
│                       │                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │  langgraph_entry.py  (5 factory functions)       │   │
│  │  - Thin adapter layer                             │   │
│  │  - Uses langgraph SDK ONLY for graph structure    │   │
│  │  - All business logic in custom Python            │   │
│  └──────────────────────────────────────────────────┘   │
│                       │                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Existing custom graphs (preserved):              │   │
│  │  - pae_maintainer.graph (state + nodes + graph)  │   │
│  │  - 4 YAML workflows in .claude/skills/...        │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

## Key Design Decision

**Thin adapter pattern**: The langgraph SDK is used only as a wrapper/glue layer. All business logic stays in the existing custom Python graphs (`pae_maintainer/graph.py`, the YAML workflows). This:

- Preserves the existing plan guardrail "no langgraph SDK in core logic"
- Reuses all existing tests (250+)
- Allows incremental migration to langgraph semantics
- Keeps both worlds working: custom runtime (autonomy) + langgraph dev (visibility)

## Update Routes

| Component | Path | Notes |
|-----------|------|-------|
| Central engine policy | `strategics/00-ÍNDICE-PROGRESSIVO.md` | Routes to langgraph.json |
| Planning engine clone | `strategics/planning-with-files/` | git pull for new versions |
| PAE-Maintainer agent | `vibe-ops/src/agents/pae_maintainer/` | Custom graph, no SDK |
| LangGraph dev wrapper | `vibe-ops/src/langgraph_entry.py` | Thin adapter |
| LangGraph config | `langgraph.json` | 5 graphs registered |
| Makefile | `Makefile` | `make dev` / `make test` / `make status` |
| Swarm workflows | `.claude/skills/quarterly-planner/workflows/*.yml` | 4 YAMLs loaded by dispatcher |

## Update Policy

```bash
# Periodic updates
make install-langgraph    # upgrade langgraph CLI
cd strategics/planning-with-files && git pull    # sync engine
git pull  # sync langgraph.json and entry points
```

## Testing

```bash
# All tests (250+ IKIGAi + new graph tests)
make test

# Manual smoke test
make dev  # in one terminal
curl -X POST http://localhost:2024/threads/runs \
  -H "Content-Type: application/json" \
  -d '{"graph_id": "pae_maintainer", "input": {"cycle_id": "manual-test"}}'
```

## See Also

- `strategics/00-ÍNDICE-PROGRESSIVO.md` - Central engine index
- `strategics/planning-with-files/` - Canonical planning engine clone
- `.omo/plans/agentic-markdown-system.md` - Plan that created the underlying flows
- `.omo/drafts/ikigai-as-dom-on-planning-engine.md` - IKIGAi data structure mapping
- `.claude/skills/quarterly-planner/SKILL.md` - Skill that defines the 4 workflows