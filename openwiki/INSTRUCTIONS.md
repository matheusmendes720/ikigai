---
type: Repository guide
title: Repository Wiki Instructions
description: User-authored brief for the OpenWiki code-mode agent. Scopes coverage, sets the language policy, and enforces the repo's append-only rules.
tags: [documentation, repository, code-wiki, algorave, ikigai]
---

# Algorithmic Life OS — Wiki brief

A code wiki for **C:\Users\mathe\code_space\life-oss\life**. The wiki lives at
`./openwiki/` (OKF v0.2, Grounded Claims, Mermaid-validated). The OpenWiki
agent reads this file each run but never rewrites it.

## 1. Repository shape

Three subsystems, one ground truth (`README.md`):

| Subsystem | Location | Role |
|-----------|----------|------|
| `life/` (root) | CLI hub + daily/weekly handlers + 3 domain centrals | 🟡 Stable |
| `life-ops/operational/` | **PAV productivity kernel** (uv workspace, sole member `packages/core`) | 🟢 **Active** |
| `life-ops/life_tatics/` | Standalone time-block planner (Poetry) | 🟡 Stable |
| `life-ops/ikigai/` | IKIGAi meta-brain — Poetry, MCP, deepagents harness | 🟡 Stable |
| `vibe-ops/` | Cybernetic engine — Obsidian ↔ SQLite ↔ Taskwarrior | 🟡 Stable |
| `taskwarrior/` | TW binary + scripts + config | 🟢 Stable |
| `code-docs/{prd,brd,adr,ard}/` | Engineering specs | 🟡 Stable |
| `strategics/` | PT-BR strategy prose (frameworks, models) | 🟢 **Read-only** |
| `docs/`, `diagrams/` | Master reading index + Mermaid source | 🟢 Read-only |

The active development focus is `life-ops/operational/` (the PAV productivity
kernel) and `life-ops/ikigai/` (the meta-brain + MCP + deepagents harness).

## 2. Priorities for this wiki

Generate pages in this order. Skip nothing in `architecture/`, `concepts/`, or
`workflows/` — these are the load-bearing sections. Be concise elsewhere.

1. **`quickstart.md`** — Single task-routing entry point. Replace the navigation
   role currently played by `README.md`, `AGENTS.md`, `CLAUDE.md`,
   `ARCHITECTURE_INDEX.md`. Each common task ("add a routine", "trace a bug",
   "run the daily loop", "decompose a dream") gets one paragraph + the file
   paths to read.
2. **`architecture/`** — system-map.md (the three-layer CLI model + subsystem
   table), substrate-stack.md (toolchain per package), agents-and-graphs.md
   (the dual-graph fleet: 6 langgraph graphs + the deepagents harness + the
   orchestrator workflows), state-persistence.md (JSON flat files, SQLite,
   ChromaDB, Markdown vault), data-flow.md (target-sensor-adjuster).
3. **`concepts/`** — ikigai-vectors.md (5 vectors + meta-vector + 60/40
   geom/harmonic blend), q-he-formula.md (H(t), E, Q_HE composite),
   h1-h6-heuristics.md (six deterministic algorithms), regimes.md
   (PUSH/MAINTAIN/REDUCE/RECOVER + asymmetric hysteresis), phases.md
   (FUNDAÇÃO/BUSCA/HACKATHON/RECUPERAÇÃO/OVERCLOCK), ueid-system.md
   (`<CLUSTER>:<ENTITY>:<ID>` tri-key), policy-engine-fsm.md (4-state FSM with
   hardcoded constants), pomodoro-machine.md (8-state SM), time-horizons.md
   (SONHO 547d / PHASE 180d / TRIMESTRE 90d / ONDA 15d / CYCLE 45d / WEEKLY 7d),
   vault-frontmatter.md (Markdown SoT).
4. **`integrations/`** — obsidian-sqlite-taskwarrior.md (SyncEngine, idempotent
   `upstream_id` SHA-256), langgraph-dev.md (port 2024, 6-graph fleet),
   deepagents-harness.md (Python, ChatAnthropic + MiniMax base URL + 18 tools),
   mcp-gateway.md (8-tool stdio server), otel-observability.md (LangSmith +
   Langfuse via OTLP/HTTP, idempotent `init_tracing`).
5. **`operations/`** — pav-kernel.md (uv workspace, 74 pytest files, packages/core
   only), root-cli-hub.md (life/cli central-handler pattern), vibe-ops-commands.md
   (argparse + Typer surfaces), agentic-harness.md (orchestrator + engines),
   ci-quality-gates.md (matrix: operational-core + vibe-ops; ruff ALL + mypy
   --strict + pytest -m "not e2e"), daily-weekly-handlers.md (orchestration
   pattern), deployment.md (local/air-gapped, manual).
6. **`testing/`** — strategy.md (3-layer), operational-test-suite.md (74 files,
   markers: unit/integration/property/e2e/slow), ikigai-test-suite.md (11
   files), vibe-ops-test-suite.md, fixtures-and-mocks.md.
7. **`workflows/`** — pae-maintainer.md, ikigai-8-node-cycle.md
   (observe → score_vectors → heuristics → balance → decompose → plan → reflect
   → commit), operational-workflow-orchestrator.md (YAML + engines +
   scheduler), quarterly-replan.md, test-de-fogo.md, correction-protocol.md,
   dream-falsification.md, langgraph-dev-graph-fleet.md.

## 3. Append-only protected content — DO NOT MOVE OR REWRITE

These directories are append-only per the project's `AGENTS.md` §"Important
Rules" and `CLAUDE.md` §"Global Conventions". The wiki cites them as
`sources:` on Claims. **Never delete, prune, move, or rewrite any file
under these paths.**

- `vibe-ops/` (entire directory — `base/`, `context/`, `doc/`, `planning/`,
  `specs/`, `architecture/`, `vectors/`, `artifacts/`, `src/`, `tests/`)
- `strategics/` (entire root directory, including `planning-with-files/`)
- `CLUSTER_PLAN.md`, `CLUSTER_PROJ.md`, `CLUSTER_STUDY.md`,
  `CONCEPTUAL_MODEL.md`, `SYSTEMS_TOPOLOGY.md`, `ARCHITECTURE_INDEX.md`
  (root level)
- `vibe-ops/SPEC.md`, `vibe-ops/CHANGELOG.md`,
  `life-ops/operational/SPEC.md`, `life-ops/ikigai/SPEC.md`,
  `taskwarrior/SPEC.md`

**Refactor protocol.** If any wiki page would benefit from reorganizing these
sources, surface the proposal in `proposals:` and stop. Do not move anything
under the protected paths without an explicit user "go" message.

## 4. Language policy

| Bucket | Language |
|--------|----------|
| `architecture/`, `integrations/`, `operations/`, `testing/`, `workflows/`, `quickstart.md`, `index.md` | **English** (default) |
| `concepts/` page bodies | **English** — concept names stay in their original Portuguese when defined in the constitutional layer (e.g. "Phase: FUNDAÇÃO / BUSCA / HACKATHON / RECUPERAÇÃO / OVERCLOCK") |
| Citation of PT-BR sources | link with original filename + a one-line English gloss |

Add `lang: pt-BR` as a producer-extension frontmatter field when the page
body is primarily Portuguese. OpenWiki's OKF v0.2 preserves extension fields
across updates.

## 5. Source-evidence discipline

- **Every material proposition needs a Claim** with a `repo://path#Lstart-Lend`
  pointer. Look at the actual file. Don't cite from memory.
- If a Claim can't be sourced from the working tree (e.g. a number cited in a
  summary doc that doesn't appear in code), tag it `needs_verification` in
  the Claim and surface it in the page body with a "?" marker.
- Prefer the live `src/` code over `.md` summaries when they disagree.
  Specifically, if `CLAUDE.md` / `AGENTS.md` / `README.md` contradicts
  `src/operational/...` or `src/ikigai/...`, **trust the code**.
- Code paths use forward slashes (this repo is cross-platform Windows +
  Linux). UPI/UEID format strings stay as-is.

## 6. Mermaid diagram conventions

- Use `flowchart TD` for control flow, `sequenceDiagram` for runtime traces,
  `stateDiagram-v2` for state machines, `erDiagram` for data models,
  `graph LR` for dependency graphs.
- Every diagram that fails validation degrades to a `text` fence with a
  one-line explanation (OpenWiki handles this automatically). Re-validate
  on each `--update`.
- Embed diagrams **inside** the concept page that explains them, not as
  standalone files. Source Mermaid stays under `diagrams/` for the human-
  facing `docs/` site.

## 7. What to skip (out of scope)

- Personal artifacts: `session-ses_*.md`, `.omo/`, `.pi/`, `.atl/`,
  `agentic-md-research-langgraph.md`, `.claude/**/worktrees/**`,
  `life-ops/life-mcp-observability-worktree/**`.
- Vendored/external: `strategics/planning-with-files/**` (it's a cloned
  third-party repo — `README.md` is fine as a backlink target only).
- Stray 0-byte crash artifacts at the repo root (`2`, `0`, `4}`, `dict[str`,
  `ISO`, `Existing`, `Path`, `Total`, …) — ignore them.
- The 33,897-line `life-ops/ikigai/life.md` — personal knowledge dump, do
  not try to ingest or summarize it.

## 8. Known drift to flag on first run

The wiki's first `--update` should surface these as stale Claims (verified
against the working tree on 2026-08-26):

1. **Operational CLI is currently broken.** Commit `604d6af` deleted the
   `apps/cli/` and `apps/tui/` source trees. The editable installs and
   `python -m operational` still point to the deleted paths. Console scripts
   `operational`, `pav`, `pav-os` fail. 3 test files under
   `tests/unit/cli/` are expected to fail until the CLI is restored.
2. **Test count is 74, not 72.** Older `AGENTS.md` and README files cite 72.
3. **CI matrix is 2 packages** (`operational-core`, `vibe-ops`), not the
   3-package matrix some older docs describe.
4. **Two CLAUDE.md files exist** (root + `life-ops/operational/`) and they
   describe different (both currently valid) views of the workspace.

## 9. Update cadence

- `architecture/`, `integrations/`, `workflows/`, `operations/`: update on
  every `--update` (scheduled daily 08:00 UTC).
- `concepts/`: update only when a Claim's evidence version goes stale.
- `testing/`: update only when test counts, markers, or fixtures change.
- `quickstart.md`, `index.md`: auto-maintained.

## 10. Provenance + trust

- Every wiki page gets `generated: { by: openwiki/0.4.2, at: <iso> }` on
  first creation.
- Pages advance their `verified:` stamp only after a successful page
  submission reconciles a non-empty complete Claims set.
- Broken Mermaid fences degrade to `text` blocks (see §6). Don't try to
  paper over them with prose — surface them.

---

If the agent encounters anything ambiguous that isn't covered here, default
to: cite the source, link to the canonical doc, and surface the question
in `proposals:` rather than guessing.
