# vibe-ops/ ADRs — Cybernetic Engine

Architecture Decision Records for the cybernetic engine (`vibe-ops/`).

## Live Specs

The canonical source is at `vibe-ops/architecture/`. These files are the ground truth:

| File | Subject |
|------|---------|
| `vibe-ops/architecture/ADR-001-data-flow-topology.md` | Multi-cluster data flow topology |
| `vibe-ops/architecture/ADR-002-mesh-contracts-state-machines.md` | Contracts and state machine specs |
| `vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md` | IKIGAi as meta-brain architecture |
| `vibe-ops/architecture/ADR-004-hybrid-rag-strategy.md` | Hybrid RAG indexing strategy |
| `vibe-ops/architecture/ADR-005-data-mesh-topology.md` | Data mesh topology |
| `vibe-ops/architecture/README.md` | Architecture index |

## Related

- `vibe-ops/planning/` — PRDs and BRDs
- `vibe-ops/src/cybernetics/daily_loop.py` — Target-Sensor-Adjuster loop
- `vibe-ops/src/pipeline/policy_engine.py` — PolicyEngine FSM
- `vibe-ops/src/middleware/sync_engine.py` — SyncEngine (Obsidian ↔ SQLite ↔ Taskwarrior)
