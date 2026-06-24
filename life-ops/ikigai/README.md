# IKIGAi — Meta-Brain of the Algorithmic Life OS

> **Standalone, local-first, deterministic IKIGAi meta-brain.**
> Single source of truth: **Markdown frontmatter**. All external apps consume markdown.

## Quick Start

```bash
poetry install
poetry run ikigai --help
poetry run ikigai vector list --json
poetry run ikigai plan dream list --json
poetry run ikigai sync
```

## Architecture

- **Canonical SoT**: Markdown vault with YAML frontmatter (`ueid`, `entity_type`, `slug`, etc.)
- **Internal mirror**: SQLite (append-only, DB-triggered)
- **Optional**: ChromaDB for semantic search
- **Fractal regime**: Global → Cluster → Vector → SubVector (per-level hysteresis)
- **5 vectors**: passion, skill, market, revenue, course (5th is external/obligation)
- **Deterministic**: All heuristics are pure arithmetic (no LLM, no NLP)

## Module Layout

```
src/ikigai/
├── types.py          UEID (tri-key), ScoreValue (with unit), Path
├── enums.py          EntityType, VectorType, RegimeType, Phase, StatusType, ScoreUnit
├── exceptions.py     11 PAV error codes + custom
├── entities/
│   ├── base.py       PlanEntity (polymorphic, fractal-friendly)
│   ├── vector.py     IKIGAiVectorEntity, VectorScorePoint
│   ├── profile.py    IKIGAiProfile (5-vector snapshot)
│   ├── skill.py      SkillNode
│   ├── opportunity.py OpportunitySignal
│   ├── plan/         Dream → Goal → Objective → Project → Task → Deliverable
│   └── ops/          Routine, TimeBlock, Ritual, Pomodoro
├── core/
│   ├── scoring/      5-vector scoring, hybrid meta-vetor (geo + harmonic), Q_HE, RICE
│   └── heuristics/   regime, phase_pivot, UCB, opportunity_fit, skill_velocity, cross_priority
├── state_machines/   8 state machines (Dream through Habit)
├── propagation/      markdown_db (canonical), sqlite_adapter, triagem
├── persistence/      markdown_vault, sqlite_repo, chroma_repo
├── override/         RegimeOverride with recommendation_score
└── cli/              Typer (--json everywhere)
```

## Design Decisions (locked)

See `SPEC.md` for the full canonical specification. All 16 architectural questions resolved.

## Status

🟡 **MVP** — Entities, scoring, heuristics, markdown DB, SQLite mirror, state machines, CLI, 250+ tests.
