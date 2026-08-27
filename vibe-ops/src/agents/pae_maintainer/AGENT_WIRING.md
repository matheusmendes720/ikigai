# PAE-Maintainer Agent Wiring

> **Source:** T14 of agentic-markdown-system plan
> **Wires 4 agent specs from `.claude/agents/` into the workflow system**

## Overview

The PAE-Maintainer agent and its 4 swarm workflows invoke 4 specialized
agent specs from `.claude/agents/`. This document explains which
spec is used by which workflow node, and the rationale.

## Wired Agent Specs

### 1. mesh-coordinator
- **Source:** `.claude/agents/swarm/mesh-coordinator.md`
- **Pattern:** P2P gossip + pBFT consensus
- **Used in:** `correction-protocol.yml` (kill switch diagnosis)
- **Why:** When PAE-Maintainer terminates with kill_switch, multiple
  parallel diagnosis agents vote on root cause. Mesh pattern gives
  fault tolerance and parallel coverage.
- **Invoked at:** `correct_protocol.diagnose_failure` node

### 2. hierarchical-coordinator
- **Source:** `.claude/agents/swarm/hierarchical-coordinator.md`
- **Pattern:** Queen-worker with hyperbolic attention
- **Used in:** `quarterly-replan.yml` (next Q planning)
- **Why:** Hierarchical planning works well for Q-level tasks:
  - Queen: high-level objective generation
  - Workers: detailed execution per Onda
- **Invoked at:** `quarterly_replan.generate_objectives` node

### 3. adaptive-coordinator
- **Source:** `.claude/agents/swarm/adaptive-coordinator.md`
- **Pattern:** Dynamic topology based on workload
- **Used in:** `test-de-fogo-rollup.yml` (5-dim rollup)
- **Why:** Rollup involves multiple parallel queries (5 dimensions);
  adaptive topology decides star vs mesh vs ring based on contention.
- **Invoked at:** `test_de_fogo.compute_aggregate` node

### 4. quorum-manager
- **Source:** `.claude/agents/consensus/quorum-manager.md`
- **Pattern:** Quorum-based consensus
- **Used in:** `dream-falsification.yml` (sonho verdict)
- **Why:** Dream falsification requires deterministic verdict from
  multiple evaluators. Quorum ensures no single agent decides.
- **Invoked at:** `dream_falsification.evaluate_evidence` node

## Invocation Pattern

Each workflow node has a `type: agent` directive that references
one of the 4 specs via the swarm-orchestration skill. The skill
handles the actual dispatch; this document just records the
mapping for future maintainers.

```yaml
# Example workflow node referencing mesh-coordinator
nodes:
  - id: diagnose_failure
    type: agent
    role: failure-diagnostician
    spec: .claude/agents/swarm/mesh-coordinator.md
    prompt: |
      Diagnose root cause: ${state.kill_switch_reason}
```

## Cross-references

- Swarm orchestration: `.claude/skills/swarm-orchestration/SKILL.md`
- 4 workflows: `.claude/skills/quarterly-planner/workflows/`
- PAE-Maintainer agent: `vibe-ops/src/agents/pae_maintainer/`
- 18 other agent specs (NOT wired in v1): see `.claude/agents/` index

## Future Work (v2)

- Wire remaining 14 agent specs
- Add MCP tool bridge for claude-flow
- Implement consensus protocol stubs (quorum/gossip/raft)
- Auto-discovery from `.claude/agents/` (no manual wiring)
