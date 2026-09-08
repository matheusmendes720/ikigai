# Phase 8.x Usage — IKIGAI v2 Graph CLI Skills + LangGraph Studio

> **Phase 8.6–9.1 shipped state.** This guide documents the canonical user-facing
> surface: CLI skill commands, skill manifest structure, LangGraph Studio, CI matrix,
> and troubleshooting. For the pre-pivot PAV-era LangGraph guide, see `docs/LANGRAPH_DEV.md`.

---

## Quick Start

```bash
# Run daily reflection cycle (IKIGAI_FAKE_LLM=1 for $0 / no real LLM calls)
IKIGAI_FAKE_LLM=1 python -m interfaces.cli.main v2 daily --json

# Run weekly review
IKIGAI_FAKE_LLM=1 python -m interfaces.cli.main v2 cycle --dry-run

# Start LangGraph Studio (all 3 registered graphs)
make dev
# Opens at http://localhost:2024

# Run a specific graph
make dev-graph NAME=ikigai_maintainer_v2
```

---

## Skill Manifests

Four skill manifests live in `src/ikigai/src/agents/v2/skills/`:

| Skill | File | Trigger |
|-------|------|---------|
| Daily | `daily.md` | `cron: "57 8 * * *"` + `/ikigai-daily` slash |
| Weekly | `weekly.md` | `cron: "0 9 * * 1"` + `/ikigai-weekly` slash |
| Monthly | `monthly.md` | `cron: "0 10 1 * *"` + `/ikikigai-monthly` slash |
| Quarterly | `quarterly.md` | `cron: "0 11 1,4,7,10 *"` + `/ikigai-quarterly` slash |

### Frontmatter Fields

```yaml
---
name: ikigai-daily                    # skill identifier (matches filename)
description: Run IKIGAI v2 daily reflection cycle — surfaces PAV-written state
entry_point: surface_intentions      # first graph node to invoke
actor: user                           # who runs this: user | agent
triggers:
  - cron: "57 8 * * *"              # cron expression (local timezone)
  - slash: "/ikigai-daily"          # slash command in IKIGAI chat
inputs:                               # read paths (vault paths or fork tool calls)
  - vault: closing-2026/.../{date}.md
  - tool: taskdog_list_tasks(status="done", since=24h)
outputs: []                           # write paths (vault_write or fork tool calls)
---
```

| Field | Values | Meaning |
|-------|--------|---------|
| `entry_point` | `surface_intentions` / `observe` | First node in the v2 graph to invoke |
| `actor` | `user` / `agent` | `user` = direct CLI call; `agent` = triggered by scheduler or another node |
| `inputs` | `vault: …` / `tool: …` | `vault:` paths are read-only; `tool:` calls a fork adapter |
| `outputs` | `vault_write: …` / `taskdog_create_task: …` | Writes go through `vault_write` MCP tool (sole vault writer per ADR-012) |

---

## CLI Reference

All commands support `--json` for machine-readable output.

### Daily

```bash
python -m interfaces.cli.main v2 daily --date YYYY-MM-DD
# --date defaults to yesterday if omitted
```

Reads PAV-written `cycle_state/{date}.md` + yesterday's daily report.
Emits 3–5 pt-BR suggestions to stdout. Does **not** write vault or invoke taskdog.

### Weekly

```bash
python -m interfaces.cli.main v2 cycle --dry-run
```

Reads last 7 daily reports from `closing-2026/*/04-relatorios-diarios/`.
Writes weekly review to `vault/` via `vault_write`. Creates weekly priority tasks
via `taskdog_create_task`.

### Monthly

```bash
python -m interfaces.cli.main v2 cycle --dry-run && \
python -m interfaces.cli.main v2 score --date YYYY-MM-DD
```

Reads last 4 weekly reviews. Runs `v2_score` (passion vector observation) and
`v2_regime` (heuristics regime check). Writes monthly review via `vault_write`.
Read-only on fork adapters.

### Quarterly

```bash
python -m interfaces.cli.main v2 cycle --dry-run && \
python -m interfaces.cli.main v2 score --date YYYY-MM-DD && \
python -m interfaces.cli.main v2 regime --date YYYY-MM-DD
```

Reads last 3 monthly + 13 weekly reviews. Runs full `v2_cycle` (8-node graph).
Writes quarterly review via `vault_write`. Creates quarterly OKR tasks.

---

## LangGraph Studio

`make dev` starts the LangGraph dev server on port 2024. Three graphs are registered in `langgraph.json`:

| Graph ID | Entry | Purpose |
|----------|-------|---------|
| `pae_maintainer` | `vibe-ops/src/langgraph_entry.py:make_pae_graph` | PAE cycle (vibe-ops, pre-v2) |
| `ikigai_maintainer_v2` | `src/ikigai/src/agents/v2/graph.py:make_v2_graph` | 9-node v2 planner-only graph |
| `ikigai_fork_smoke` | `src/ikigai/src/agents/v2/fork_smoke_graph.py:make_fork_smoke_graph` | Fork adapter smoke tests |

Open http://localhost:2024 in your browser to explore graphs, inspect state, and replay steps.

---

## CI Matrix

Five jobs in `.github/workflows/ci.yml`:

| Job | Trigger | What it runs |
|-----|---------|--------------|
| `code-review-checks` | PR only | `mypy --strict` on changed files + test suite review |
| `quality-gates` | every push/PR | `ruff` + `ruff format --check` + `mypy` + `pytest -m "not e2e"` across 8 packages; v2-nodes entry also runs `IKIGAI_FAKE_LLM=1 pytest -m "not integration"` |
| `mcp-gateway-contract` | needs quality-gates | `python scripts/mcp_inspect.py` — enumerates 15 tools + 6 resources via stdio handshake |
| `review-queue-worker-contract` | needs quality-gates | `pytest interfaces/cli/tests/test_review_queue_worker.py` |
| `v2-nodes-smoke` | every push/PR | 9 parallel test paths with `IKIGAI_FAKE_LLM=1`, `--confcutdir=.` for dual-module identity |

Key env vars for CI:
- `IKIGAI_FAKE_LLM=1` — forces fake LLM stubs, $0 cost, fast CI
- `PYTHONPATH=../..` — needed when running from `src/ikigai/` subdirectory

---

## Troubleshooting

### Fake LLM mode

All Phase 8.x tests run with `IKIGAI_FAKE_LLM=1`. This stubs LLM calls and is
required for CI to stay at $0 cost:

```bash
IKIGAI_FAKE_LLM=1 python -m interfaces.cli.main v2 daily --json
```

### Dual-module identity (`--confcutdir=.`)

Tests in `src/ikigai/` must use `--confcutdir=.` because the repo has two
import styles (`from src.X` and `from X`) that resolve to different `sys.modules`
entries:

```bash
uv run pytest --confcutdir=. interfaces/cli/tests/test_v2_skill_dispatch.py -m "not integration"
```

Without `--confcutdir=.`, pytest resolves imports from the outer `life/` root,
and patches to `src.X` in tests silently no-op.

### LangGraph Studio not loading

```bash
# Install langgraph CLI
make install

# Or upgrade only langgraph
make install-langgraph

# Check registered graphs
make status
```

### v2 node tests failing

```bash
# Smoke test a single graph
make dev-graph NAME=ikigai_maintainer_v2

# Run just the v2 skill dispatch tests
IKIGAI_FAKE_LLM=1 uv run pytest --confcutdir=. \
  interfaces/cli/tests/test_v2_skill_dispatch.py \
  -m "not integration" -k "daily" --tb=line
```

### Skill manifest not found

Manifests live in `src/ikigai/src/agents/v2/skills/`. Verify the file exists:

```bash
ls src/ikigai/src/agents/v2/skills/
# daily.md  meta_plan.md  monthly.md  quarterly.md  weekly.md
```

---

## See Also

- `docs/LANGRAPH_DEV.md` — pre-pivot PAV-era LangGraph guide (SUPERSEDED)
- `src/ikigai/src/agents/v2/skills/` — skill manifest source files
- `src/ikigai/src/agents/v2/graph.py` — `make_v2_graph` factory (9-node v2 graph)
- `src/contracts/` — canonical Pydantic v2 contracts
- `sys_ikigai/security/kill_switch.py` — pause/resume the cybernetic engine
