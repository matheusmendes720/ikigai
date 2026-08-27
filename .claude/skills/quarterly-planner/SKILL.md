---
name: quarterly-planner
description: Strategic planning via PAE-Maintainer agent. Generates quarterly plans, runs retrospective reviews, triggers swarm workflows on correction signals.
trigger_keywords:
  - "quarterly plan"
  - "retrospective"
  - "teste de fogo"
  - "kill switch"
  - "policy trail"
version: 1.0
---

# Quarterly Planner Skill

Strategic planning orchestrated via the **PAE-Maintainer** agent. This skill wraps:

- `pav plan run` — one full PAE cycle (observe -> plan || reflect -> balance -> commit)
- `pav plan status` — show last persisted state
- `pav plan balance` — show workload vs capacity

## Workflows Available

| Workflow | Trigger | Output |
|----------|---------|--------|
| `quarterly-replan.yml` | Q-end + verdict=FAIL | Auto-generate next Q plan |
| `test-de-fogo-rollup.yml` | Weekly + on_demand | 5-dim aggregate |
| `correction-protocol.yml` | Kill switch fired | Diagnose + recommend action |
| `dream-falsification.yml` | Sonho kill_switch_date < 7d | Evaluate falsifiability |

## Usage

```
# Run one PAE cycle
pav plan run --cycle-id 2026-Q3

# Check status
pav plan status --cycle-id 2026-Q3 --json

# Check balance
pav plan balance --cycle-id 2026-Q3
```

## When to Use Each Workflow

- **quarterly-replan**: At end of Q (every 90 days) when verdict != PASS
- **test-de-fogo-rollup**: Weekly on Friday afternoons (or on-demand)
- **correction-protocol**: When PAE-Maintainer terminates with kill_switch_triggered=True
- **dream-falsification**: When any Sonho kill_switch_date < 7 days from today

## Cross-references

- PAE-Maintainer agent: `vibe-ops/src/agents/pae_maintainer/`
- CLI bridge: `pav plan` (subcommand of `pav`)
- Templates: `vibe-ops/planning/_templates_periodos_v2/`
- Bases: `_bases/Quarterly-Plans.base`, `Active-Ondas.base`, `Cycle-Tracker.base`
