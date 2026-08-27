# IKIGAi Planning — Meta-Brain Documentation

> **IKIGAi as the meta-brain (propositive-superior) of the Algorithmic Life OS.**
>
> This directory contains 4 drilldown docs that formalize how IKIGAi:
> 1. Defines the 4 canonical vectors (passion/skill/market/revenue) + 5th contextual (course)
> 2. Sets the **North Star Metrics** that govern all other sub-systems
> 3. Propagates data across contracts, databases, and frontmatter docs
> 4. Drives **meta-heuristics** for regime, phase, and prioritization decisions

## Index

| Doc | Purpose | Audience |
|---|---|---|
| [`ikigai_4_vectors.md`](ikigai_4_vectors.md) | The 4 canonical vectors + 5th contextual (course) — drilldown of conceptual model into executable specs | Coding agents implementing entities |
| [`ikigai_north_star_metrics.md`](ikigai_north_star_metrics.md) | The 22 constants that govern the entire system (windows, pomodoros, λ, ρ, WAVE/CYCLE/PHASE, Q_HE target) | All agents (north star reference) |
| [`ikigai_propagation.md`](ikigai_propagation.md) | How IKIGAi data flows across YAML/Pydantic/SQLite/TW UDAs/Obsidian frontmatter | Architects + integrators |
| [`ikigai_meta_heuristics.md`](ikigai_meta_heuristics.md) | Deterministic decision algorithms (regime, phase pivot, vector weight recalibration) | Coding agents implementing policy |

## Relationship to Other Docs

**Conceptual (origin):**
- [`vibe-ops/base/IKIGAi.md`](../../vibe-ops/base/IKIGAi.md) (90K, 4 vectors + Hypervisor concept)
- [`vibe-ops/vectors/`](../../vibe-ops/vectors/) (4 rich operational vectors: passion, skill, market, revenue)

**Specification (entities):**
- [`vibe-ops/planning/PRD-07-ikigai-vectors.md`](../../vibe-ops/planning/PRD-07-ikigai-vectors.md) (311 lines, Pydantic entities + score algorithms)
- [`vibe-ops/specs/prd-ikigai-vectors.md`](../../vibe-ops/specs/prd-ikigai-vectors.md) (mirror)

**Implementation (current GAP):**
- [`vibe-ops/src/models/ikigai_entities.py`](../../vibe-ops/src/models/ikigai_entities.py) (**GAP: 18 lines**, only 4 fields)
- [`vibe-ops/src/pipeline/ikigai_scorer.py`](../../vibe-ops/src/pipeline/ikigai_scorer.py) (**GAP: 46 lines**, **DIVERGES** from conceptual — uses `study/dev/health/global` instead of `passion/skill/market/revenue`)

**Cluster docs (consumers):**
- [`CONCEPTUAL_MODEL.md`](../../CONCEPTUAL_MODEL.md) §3 (5 vectors, meta-vetor, regime)
- [`CLUSTER_PLAN.md`](../../CLUSTER_PLAN.md) (Cluster 1, 1861 lines) — uses IKIGAi for daily regime
- [`CLUSTER_PROJ.md`](../../CLUSTER_PROJ.md) — uses IKIGAi for project ROI weight
- [`CLUSTER_STUDY.md`](../../CLUSTER_STUDY.md) — uses IKIGAi for skill vector scoring

## Status

🟡 **DRAFT** — Sprint 1 of Q3 2026 will implement entities + scorer based on these docs.

The 4 drilldown docs are **AI-native**: a coding agent should be able to implement the Sprint 1 deliverables (rebuild `ikigai_scorer.py`, expand `ikigai_entities.py`) reading only these 4 files + the conceptual `IKIGAi.md`.

## Key Decisions (from user)

1. **NO LLM** in the daily/weekly pipeline (LLM only for AI Harness suggestions)
2. **NO NLP, NO embeddings** for daily reports
3. **Only arithmetic + algebraic functions** (H(t), E(t), Q_HE, R_n)
4. **Append-only** to existing files
5. **IKIGAi planning lives here** in `life-ops/planner/ikigai_planning/`

---

*README.md — v1.0 — 2026-06-05 — IKIGAi Planning Documentation Set*
