# Algorithmic Life OS — Wiki Home

> **Public-facing project documentation.** For local development guidance, see `CLAUDE.md`.

---

## Quick Links

| Topic | Where to find it |
|-------|-----------------|
| How the system works | [ARCHITECTURE_INDEX.md](ARCHITECTURE_INDEX.md) |
| Cluster 1 — Plan | [CLUSTER_PLAN.md](../CLUSTER_PLAN.md) |
| Cluster 2 — Project | [CLUSTER_PROJ.md](../CLUSTER_PROJ.md) |
| Cluster 3 — Study | [CLUSTER_STUDY.md](../CLUSTER_STUDY.md) |
| Engineering specs | [vibe-ops/planning/](vibe-ops/planning/) |
| Architecture decisions | [vibe-ops/architecture/](vibe-ops/architecture/) |
| ADRs | [vibe-ops/architecture/](vibe-ops/architecture/) |
| How to run the CLI | [README.md](../README.md) |
| Life-ops/operational | [life-ops/operational/README.md](../life-ops/operational/README.md) |

---

## Project Structure

```
life/                          ← root CLI hub (Typer)
life/centrals/                 task, knowledge, research
life/handlers/                 daily, weekly orchestration
life/plugins/                   plugin system

life-ops/operational/          ← ACTIVE development
  packages/core/               pure arithmetic business logic
  apps/cli/                   Typer CLI (pav, pav-os)
  apps/tui/                   Textual TUI (7 screens)
  tests/                      2518 tests

vibe-ops/                     cybernetic engine (R&D)
  src/cybernetics/            Target-Sensor-Adjuster loop
  src/pipeline/               policy, RAG, sync orchestrators
  src/models/                  Pydantic entities
  architecture/               ADRs
  planning/                   PRDs + BRDs

taskwarrior/                  TW binary + scripts (read-only integration)
strategics/                   PT-BR strategy frameworks
docs/                         master reading index
diagrams/                     Mermaid sources + PNG renders
```

---

## Subsystems

### life-ops/operational — PAV Productivity Kernel

Standalone uv workspace. Pure arithmetic algorithms, zero LLM/NLP.

- **CLI:** `pav`, `pav-os`, `operational` (all equivalent)
- **TUI:** 7 screens via `pav screen <name>`
- **Algorithms:** H(t) habit model, Q_HE composite score, 4-state PolicyEngine FSM, 8-state Pomodoro SM
- **Quality gates:** ruff ALL, mypy --strict, 2518 tests

See [`life-ops/operational/README.md`](../life-ops/operational/README.md)

### vibe-ops — Cybernetic Control Center

Target-Sensor-Adjuster loop: Ikigai → PolicyEngine → Obsidian ↔ SQLite ↔ Taskwarrior.

- **CLI:** `python src/main.py run-daily`, `python src/vibe_cli.py sync_file`
- **Rust TUI:** `cargo run` in `vibeops-tui/`
- **Append-only:** never delete or rewrite existing content

---

## Contributing

### Bug Reports
Use [the bug report template](../.github/ISSUE_TEMPLATE/bug_report.yml).
Include: command, expected vs actual behavior, reproduction steps, environment (WSL2/Ubuntu VPS/Windows).

### Feature Requests
Use [the feature request template](../.github/ISSUE_TEMPLATE/feature_request.yml).
Include: motivation, proposed CLI signature, acceptance criteria.

### Pull Requests
1. Branch from `main`
2. Run quality gates: `uv run ruff check && uv run mypy && uv run pytest`
3. Open PR with description linking the issue
4. Ensure CI passes

---

## Labels

| Label | Use for |
|-------|---------|
| `subsystem/operational` | life-ops/operational issues |
| `subsystem/vibe-ops` | vibe-ops issues |
| `subsystem/life-cli` | root CLI hub issues |
| `priority/critical` | Blocks all work |
| `process/sprint` | In current sprint |
| `process/backlog` | Not yet scheduled |

Full label reference: [`.github/labels.yml`](../.github/labels.yml)
