# operational — Canonical Spec (Standalone Memory Machine)

> **Status:** Draft v0.1.0 — being filled as sprints progress.
> This is a Standalone Memory Machine: the spec is self-contained and can be read without external context.

---

## 1. Purpose

`operational` is a **standalone, local-only, single-user** CLI program that implements the **operational/cybernetic domain** of the Algorithmic Life OS workspace. It is derived from:

1. `vibe-ops/base/Produtividade Algorítmica Visual.md` (815K) — PAV canonical spec
2. `vibe-ops/planning/PRD-02-habit-tracker.md` — habit + Q_HE
3. `vibe-ops/planning/PRD-05-metrics-health.md` — metrics & health
4. `life-ops/planner/Points_of_premisses-task-habits.md` — math + histerese
5. `strategics/Modelagem Operacional.md` — 4 regimes, histerese

The program covers:

- **Routines** (manhã/tarde/noite) with rituals and transitions
- **Time blocks** (pomodoros, work sessions, breaks)
- **Journal log** (narrative entries with socratic questions)
- **Habits** (H(t), E_req, streak, weight, resistance)
- **Q_HE** (Quality Habit Effectiveness) calculation
- **Metrics** (SleepRecord, EnergyReading, DailyLog)
- **Consolidation** (daily/weekly scores)
- **Policy FSM** (PUSH/MAINTAIN/REDUCE/RECOVER with histerese)

## 2. Scope

### In Scope
- Pure arithmetic algorithms (no LLM, no NLP)
- Local SQLite storage (no cloud)
- Deterministic behavior (idempotent re-runs)
- CLI with `--json` output

### Out of Scope
- IKIGAi meta-brain (separate sub-project)
- Taskwarrior/Timewarrior integration (deferred)
- LLM/NLP features (deferred indefinitely)
- Multi-user authentication
- Cloud sync
- Real-time collaboration

## 3. Architecture

See `docs/ARCHITECTURE.md` for the full module diagram.

## 4. Roadmap

See `docs/ROADMAP.md` for the sprint-by-sprint breakdown.

## 5. Conventions

- **Python 3.11+** required
- **Pydantic v2 strict mode** for all entities
- **mypy --strict** for type checking
- **ruff** for linting and formatting
- **pre-commit** for gates
- **pytest** with markers (unit, integration, e2e, property)

## 6. Source Spec Mapping

| PAV Section | Module(s) | Status |
|:------------|:----------|:------:|
| §1 — Constants (22) | `constants.py` | 🔴 Sprint 1 |
| §2 — Variables (14) | `entities/metric.py` | 🔴 Sprint 2 |
| §3 — Periods (3) | `entities/routine.py` | 🔴 Sprint 2 |
| §4 — Decision Tree | `core/time_validator.py` | 🔴 Sprint 3 |
| §5 — Mermaid Flow | (reference) | — |
| §6 — Error Handling (10) | `exceptions.py` | 🔴 Sprint 1 |
| §7 — Sleep Calculation | `core/sleep_calculator.py` | 🔴 Sprint 3 |
| §8 — Scenarios (3) | `core/scenario_classifier.py` | 🔴 Sprint 3 |
| §9 — Pomodoro SM | `core/pomodoro_machine.py` | 🔴 Sprint 3 |
| §10 — Dashboard | (CLI output) | 🔴 Sprint 7 |

---

*operational — Standalone Memory Machine — 2026-06-07*
