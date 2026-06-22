# Table of Contents

## Getting Started
- [Setup & Installation](Getting-Started) — clone, install, first commands
- [CLI Reference](CLI-Reference) — all `pav` and `life` commands

## Architecture
- [System Overview](../ARCHITECTURE_INDEX.md) — master index of all layers
- [PAV Kernel](../life-ops/operational/README.md) — algorithms, entities, state machines
- [Cybernetic Loop](../vibe-ops/src/cybernetics/daily_loop.py) — Target-Sensor-Adjuster
- [Policy Engine](../vibe-ops/src/pipeline/policy_engine.py) — 4-state FSM

## Clusters
- [Cluster 1: Plan](../CLUSTER_PLAN.md) — routines, time blocks, pomodoro
- [Cluster 2: Project](../CLUSTER_PROJ.md) — PMO ↔ Taskwarrior
- [Cluster 3: Study](../CLUSTER_STUDY.md) — PKM, cognitive prerequisites

## Engineering
- [ADRs](../vibe-ops/architecture/) — Architecture Decision Records
- [PRDs](../vibe-ops/planning/) — Product Requirements Documents
- [Spec Index](../vibe-ops/specs/) — schemas and technical specs
- [operational ADRs](../life-ops/operational/docs/adr/) — sprint documentation

## Contributing
- [Bug Reports](../.github/ISSUE_TEMPLATE/bug_report.yml)
- [Feature Requests](../.github/ISSUE_TEMPLATE/feature_request.yml)
- [Pull Request Guide](../.github/PULL_REQUEST_TEMPLATE.md)
- [CI/CD Pipeline](../.github/workflows/ci.yml)

## Operations
- [Deployment — WSL2 & Ubuntu VPS](Deployment-WSL2-Ubuntu-VPS) — cloud agent setup
- [Git Worktree Guide](Git-Worktree-Guide) — multi-agent parallel development
- [Sprint Health](../.github/scripts/issue_metrics.py) — `python .github/scripts/issue_metrics.py --sprint-health`
