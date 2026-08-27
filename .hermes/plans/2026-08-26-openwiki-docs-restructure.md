# Proposal — OpenWiki-driven docs restructure

**Date:** 2026-08-26
**Scope:** Repo-root + subsystem markdown consolidation, agent-maintained.
**Tool:** [OpenWiki](https://github.com/langchain-ai/openwiki) v0.2 (OKF, Grounded Claims, Mermaid validation).
**Status:** Proposal — **no files have been moved yet**. Append-only rules (vibe-ops/, strategics/, cluster docs) require the Refactor Protocol Approval Gate before any mutation there.

---

## 0. The problem in numbers

Verified by `find` against the working tree (excluding `.venv`, `.git`, `__pycache__`, worktrees, `.omo/drafts|evidence|mock-datasets`, `.pytest_cache`, `site-packages`):

| Class | Count | Notes |
|-------|------:|-------|
| `README.md` files | **34** | 1 root, 1 per package, many stale |
| `SPEC.md` files | **9** | root, `life-ops/`, `life-ops/operational/`, `life-ops/ikigai/`, `vibe-ops/`, `vibe-ops/specs/`, `taskwarrior/`, `specs/`, `code-docs/` |
| `*index*.md` / master index | **3+** | `ARCHITECTURE_INDEX.md` (root, 679 lines), `ÍNDICE PROGRESSIVO.md` (root + `docs/`), `00-INDEX.md` + `00-INDEX-specs.md` (`code-docs/`) |
| `CLAUDE.md` files | **2** | root + `life-ops/operational/` (deliberately divergent per `CLAUDE.md` header) |
| `AGENTS.md` files | **1** | root only (Codex-targeted) |
| `.md` files ≥ 1000 lines | **~15** | 33k-line `life-ops/ikigai/life.md` leads; `CLUSTER_PLAN.md` 1861, `PAV_INVENTORY.md` 1974 |
| Total `.md` surface | ~250 files | most unread by both humans and agents |

Three structural pains:
1. **No source of truth.** `README.md`, `CLAUDE.md`, `AGENTS.md`, `ARCHITECTURE_INDEX.md`, `CLUSTER_*` and per-package `README.md` describe overlapping subsystems with conflicting decisions (e.g. CLI entry points).
2. **Documents drift out of sync with code.** `AGENTS.md` had to be patched in this session because the `apps/cli`+`apps/tui` deletion (`604d6af`) wasn't reflected. There is no automated mechanism to flag that drift.
3. **Reading budget is unbounded.** No agent or human knows where to start. `ARCHITECTURE_INDEX.md` advertises itself as "master index — 50+ cross-refs" but doesn't link to `life-ops/operational/`, `code-docs/`, `.github/wiki/`, `taskwarrior/help/`, or `strategics/planning-with-files/docs/`.

## 1. Why OpenWiki

OpenWiki is a CLI (`npm install -g openwiki`) that:

- Walks the repo, plans a wiki, writes `openwiki/*.md` per page.
- Emits **OKF v0.2** — YAML frontmatter with `okf_version`, `type`, `title`, `description`, `tags`, `generated`, `verified`, `sources`, `status`, `stale_after`. ([spec](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md))
- Tracks **Grounded Claims** — every material proposition is tied to a versioned source pointer like `repo://src/server.ts#L40-L82`. When the source changes, the Claim goes stale and the owning page is queued for rewrite on `openwiki --update`.
- Validates every embedded **Mermaid** diagram; broken fences degrade to `text` blocks (not silently broken).
- Can run **inside** Codex/Claude Code/OpenCode as an MCP integration, or as a CI bot that opens a docs PR. ([examples/openwiki-update.yml](https://github.com/langchain-ai/openwiki/blob/main/examples/openwiki-update.yml))
- Maintains `AGENTS.md` and `CLAUDE.md` automatically — it only rewrites its own `<!-- OPENWIKI:START -->…<!-- OPENWIKI:END -->` block, leaving the rest of each file alone. **That single feature is the answer to the AGENTS.md drift problem we hit this session.**

For a repo this size and this messy, an agent-maintained wiki with Claims + a graph visualizer is the only thing that will keep up.

## 2. The proposed target layout

OpenWiki's documented output structure (verified against `langchain-ai/openwiki/openwiki/`):

```
openwiki/
├── index.md                       # okf_version: "0.2", root navigation
├── quickstart.md                  # ~12 KB task-routing page
├── INSTRUCTIONS.md                # USER-AUTHORED brief — openwiki never rewrites
├── .claims/                       # per-page Claims sidecars (git-tracked)
├── .last-update.json              # provenance + last successful run
├── architecture/                  # system shape, ADRs, topology
├── concepts/                      # domain entities, algorithms, regimes, heuristics
├── integrations/                  # how subsystems connect (Obsidian↔SQLite↔TW, MCP, langgraph)
├── operations/                    # runbooks, deployment, CI, daily/weekly handlers
├── testing/                       # test strategy, fixtures, mocks, e2e
└── workflows/                     # PAE cycle, IKIGAi cycle, orchestrator workflows
```

Plus the auto-managed pointer block injected into existing `AGENTS.md` + `CLAUDE.md`:

```markdown
<!-- OPENWIKI:START -->
The full agent-readable documentation lives at `./openwiki/` (OKF v0.2, Grounded
Claims). Start at `openwiki/index.md` → `openwiki/quickstart.md`. This block is
auto-rewritten by `openwiki --update`; do not edit it by hand.
<!-- OPENWIKI:END -->
```

## 3. Mapping current docs → openwiki buckets

### 3.1 User-authored content (stays put — append-only protected)

| Current location | Why it stays |
|---|---|
| `vibe-ops/strategics/`, `vibe-ops/specs/`, `vibe-ops/architecture/`, `vibe-ops/planning/`, `vibe-ops/vectors/`, `vibe-ops/base/`, `vibe-ops/context/`, `vibe-ops/doc/`, `vibe-ops/artifacts/` | **Append-only Rule** from AGENTS.md §"Important Rules" — no moves, only references from the wiki |
| `strategics/` (root) | **Append-only** cluster doc layer |
| `CLUSTER_PLAN.md`, `CLUSTER_PROJ.md`, `CLUSTER_STUDY.md`, `ARCHITECTURE_INDEX.md`, `CONCEPTUAL_MODEL.md`, `SYSTEMS_TOPOLOGY.md` (root) | **Strategic prose, append-only** (PT-BR ↔ EN split rule). Wiki points to them, doesn't replace them |
| `PAV_INVENTORY.md`, `session-ses_*.md`, `.omo/`, `.pi/`, `.atl/`, `agentic-md-research-langgraph.md` | Personal session/draft artifacts — out of scope |
| `LANGRAPH_DEV.md` | Reference doc for `make dev`; keep as-is, link from `openwiki/operations/langgraph-dev.md` |
| `.github/wiki/*` | Public-facing GitHub wiki; mirror with sync, don't replace |

### 3.2 Subsystem docs that get **referenced**, not moved

`vibe-ops/SPEC.md`, `vibe-ops/CHANGELOG.md`, `vibe-ops/architecture/ADR-001…006.md`, `vibe-ops/planning/PRD-01…07.md`, `vibe-ops/specs/*.md`, `life-ops/operational/SPEC.md`, `life-ops/ikigai/SPEC.md`, `life-ops/ikigai/MCP_GATEWAY.md`, `life-ops/ikigai/scripts/OBSERVABILITY.md`, `taskwarrior/SPEC.md` + `taskwarrior/docs/*` — these are the canonical engineering specs. The wiki's Claims cite them as `sources[]`. The wiki never replaces them.

### 3.3 Generated content that gets **centralized** (this is the consolidation)

OpenWiki republishes distilled, agent-readable views of these into `openwiki/`:

| Wiki bucket | Generated pages | Sources synthesized from |
|---|---|---|
| `openwiki/quickstart.md` | Single task-routing entry point (replaces the current navigation role of `README.md`, `AGENTS.md`, `CLAUDE.md`, `ARCHITECTURE_INDEX.md`) | README, AGENTS.md, CLAUDE.md, LANGRAPH_DEV.md, package READMEs |
| `openwiki/architecture/` | `system-map.md`, `substrate-stack.md`, `agents-and-graphs.md`, `state-persistence.md`, `data-flow.md` (each with Mermaid) | `ARCHITECTURE_INDEX.md`, `SYSTEMS_TOPOLOGY.md`, `CONCEPTUAL_MODEL.md`, `life-ops/operational/CLAUDE.md`, `vibe-ops/src/langgraph_entry.py`, `life-ops/ikigai/src/agents/ikigai_maintainer/graph.py` |
| `openwiki/concepts/` | `ikigai-vectors.md`, `q-he-formula.md`, `h1-h6-heuristics.md`, `regimes.md`, `phases.md`, `ueid-system.md`, `policy-engine-fsm.md`, `pomodoro-machine.md`, `vector-meta-blend.md`, `time-horizons.md`, `vault-frontmatter.md` | `life-ops/ikigai/SPEC.md`, `life-ops/operational/SPEC.md`, `vibe-ops/base/Produtividade Algorítmica Visual.md`, `vibe-ops/base/IKIGAi.md`, `vibe-ops/vectors/*.md` |
| `openwiki/integrations/` | `obsidian-sqlite-taskwarrior.md`, `langgraph-dev.md`, `deepagents-harness.md`, `mcp-gateway.md`, `otel-observability.md` | `vibe-ops/src/middleware/sync_engine.py`, `vibe-ops/src/langgraph_entry.py`, `life-ops/ikigai/src/agents/deepagents_harness.py`, `life-ops/ikigai/src/mcp_server/server.py`, `life-ops/ikigai/src/observability/otel_init.py`, `langgraph.json`, `life-ops/ikigai/MCP_GATEWAY.md`, `LANGRAPH_DEV.md`, `life-ops/ikigai/scripts/OBSERVABILITY.md` |
| `openwiki/operations/` | `pav-kernel.md`, `root-cli-hub.md`, `vibe-ops-commands.md`, `agentic-harness.md`, `ci-quality-gates.md`, `daily-weekly-handlers.md`, `langgraph-dev.md`, `deployment.md` | `life-ops/operational/CLAUDE.md`, `cli/`, `handlers/`, `centrals/`, `vibe-ops/src/main.py`, `vibe-ops/src/vibe_cli.py`, `Makefile`, `.github/workflows/ci.yml`, `LANGRAPH_DEV.md`, `docs/DEPLOY.md` |
| `openwiki/testing/` | `strategy.md`, `operational-test-suite.md`, `ikigai-test-suite.md`, `vibe-ops-test-suite.md`, `fixtures-and-mocks.md` | `AGENTS.md` § Testing Strategy, `life-ops/operational/pytest.ini`, `life-ops/operational/ruff.toml`, `life-ops/ikigai/tests/`, `vibe-ops/tests/`, `Makefile` |
| `openwiki/workflows/` | `pae-maintainer.md`, `ikigai-8-node-cycle.md`, `operational-workflow-orchestrator.md`, `pae-quarterly-replan.md`, `test-de-fogo.md`, `correction-protocol.md`, `dream-falsification.md`, `langgraph-dev-graph-fleet.md` | `vibe-ops/src/langgraph_entry.py` (6 graphs), `life-ops/ikigai/src/agents/ikigai_maintainer/{graph,nodes/*}.py`, `life-ops/operational/agents/orchestrator/`, `LANGRAPH_DEV.md` |

### 3.4 Files that get **superseded** at the root

The auto-injected `<!-- OPENWIKI:START -->…<!-- OPENWIKI:END -->` pointer block in `AGENTS.md` and `CLAUDE.md` does the redirection. We do **not** delete the body of those files — that is your authored content — but the navigation role they currently play ("where do I start?") is taken over by `openwiki/quickstart.md`.

**Open question for you:** do we also delete the now-redundant `README.md` and `ARCHITECTURE_INDEX.md` at root, or keep them as historical anchors with a one-line pointer to `openwiki/`? Default recommendation: **keep both with a redirect banner** for one release, then delete in the next. `ARCHITECTURE_INDEX.md` is genuinely useful as a human-readable cross-link catalog even after the wiki exists.

## 4. The migration playbook

### Phase 0 — OpenWiki install + plan (no file moves)
```sh
npm install -g openwiki              # Node 22+, requires internet for provider
openwiki --init                      # walk provider/key/model wizard; writes openwiki/
# Review the plan + first ~10 generated pages before letting it finish
```

OpenWiki writes `openwiki/INSTRUCTIONS.md` itself — that's where you override defaults (e.g. "skip `vibe-ops/context/`, focus on subsystem architecture, write PT-BR for architecture pages"). **Author this file yourself** before re-running; OpenWiki reads it but never rewrites it.

### Phase 1 — First-pass wiki (`openwiki --init --print`)
- Run with `--print` (one-shot, exits on success) for a CI-shaped first pass.
- Skim the generated pages against the append-only protected content — every disputed claim should end up as a Claim citing the original `sources:`.
- Commit `openwiki/`, `openwiki/INSTRUCTIONS.md`, the rewrites of `AGENTS.md` + `CLAUDE.md` (only the `OPENWIKI:START/END` block), and `.github/workflows/openwiki-update.yml`.

### Phase 2 — CI bot (scheduled docs PR)
Add `.github/workflows/openwiki-update.yml` (templated from [openwiki/examples](https://github.com/langchain-ai/openwiki/blob/main/examples/openwiki-update.yml)) on `cron: "0 8 * * *"` (daily 08:00 UTC = midnight PST). The bot opens a PR titled `docs: update OpenWiki` containing whatever drifted. You merge it; wiki stays current.

### Phase 3 — Optional: agent-driven integration
```sh
openwiki integrations install claude   # or codex / opencode
```
This gives the existing coding agent (Hermes here, or Codex/Claude Code/OpenCode) the ability to answer "update this repository's OpenWiki for changes since its last successful run" using its own authenticated model and tools. OpenWiki still owns the durable page queue and Claims persistence.

### Phase 4 — Visualizer as public docs site
```sh
openwiki visualize openwiki --export docs/openwiki-visualizer
```
Commit the export, enable GitHub Pages on `docs/` → live, searchable docs site at `matheusmendes720.github.io/ikigai/`. This replaces the current `.github/wiki/*` Markdown wiki as the human-facing surface (the GitHub wiki stays as a low-effort mirror if you want it).

## 5. What OpenWiki does **not** solve (be honest)

1. **PT-BR ↔ EN split.** OpenWiki is English-default. For the `strategics/` corpus and the constitutional prose, the wiki should **link** to PT-BR sources, not rewrite them. OKF v0.2 supports `lang: pt-BR` as a producer-extension field — put it on those pages.
2. **The 33,897-line `life-ops/ikigai/life.md`.** That's a personal knowledge dump, not source-of-truth engineering. Exclude it from `INSTRUCTIONS.md` scope.
3. **Two CLAUDE.md / divergent ROOT files.** OpenWiki will generate one canonical view; the per-subsystem CLAUDE.md can stay. We do **not** delete your authored files.
4. **Workspace mixing (operational is uv, ikigai is Poetry).** OpenWiki documents this; it doesn't unify the toolchain.
5. **The "Operational CLI is broken" pitfall** we just hit. Claims would catch this on the next `openwiki --update`, but only if `tests/unit/cli/` failure is wired into the run (suggest adding `uv run pytest tests/unit/cli` to a `precommit` so Claims can detect the drift).
6. **First-run cost.** `openwiki --init` is a real LLM run across the whole repo. Budget it: ~10–30 minutes for a repo this size, ~$2–10 of inference depending on provider. After that, `--update` only diffs.

## 6. Decisions you need to make before we start

1. **Approval gate for the append-only moves.** Per AGENTS.md §"Important Rules" → "Refactor Protocol", anything that touches `vibe-ops/`, `strategics/`, or cluster docs needs an explicit "go" from you. **My recommendation:** don't move any of those files at all. The wiki points to them; the wiki never relocates them. This sidesteps the protocol.
2. **Provider.** OpenWiki supports 13 providers (OpenAI, Anthropic, Bedrock, Gemini, OpenRouter, GitHub Copilot, …). Pick one — or use GitHub Copilot since you're already on a `gh`-authenticated box and don't want a separate billing line.
3. **LangSmith tracing.** If `OPENWIKI_LANGSMITH_API_KEY` is set, OpenWiki will also pull runtime traces for the projects you choose. Given your recent OpenTelemetry wiring (`20f1e72`), turning this on gives you docs that reflect actual runtime behaviour. Two env vars.
4. **Public visualizer?** `openwiki visualize … --export docs/openwiki-visualizer` is the easiest path to a real docs site. Costs one CI minute on Pages.
5. **How aggressive should `--update` be?** Default: opens a docs PR on every change. Tighter: only on changes to source under `src/` / `packages/`, not docs themselves.

## 7. What I'll do after approval

If you say go, the sequence is:

1. Install OpenWiki; write `openwiki/INSTRUCTIONS.md` together (you set the brief, I draft).
2. Run `openwiki --init --print`; review the first batch of pages.
3. Hand-curate the `architecture/` + `integrations/` pages for accuracy (Claims pointing to real files).
4. Wire `.github/workflows/openwiki-update.yml` on a daily cron.
5. Open the first wiki bootstrap PR. **No content moves in `vibe-ops/`, `strategics/`, or the cluster docs.** Only additive: new `openwiki/` tree + the auto-managed `OPENWIKI:START/END` blocks in `AGENTS.md` + `CLAUDE.md`.

If you don't want to move yet, the minimum that fixes today's drift is step (5)'s PR restricted to the `OPENWIKI:START/END` blocks + `openwiki/INSTRUCTIONS.md` + `openwiki/index.md` + `openwiki/quickstart.md`. That alone gives every coding agent (Hermes, Codex, Claude Code) a single, machine-trustable entry point that will auto-update on every CI run.

---

## Appendix — files inventoried for this proposal

Skipped (out of scope): `.venv/**`, `.git/**`, `__pycache__/**`, `site-packages/**`, `.pytest_cache/**`, `.mypy_cache/**`, `.ruff_cache/**`, `*.egg-info`, `worktrees/**`, `life-ops/life-mcp-observability-worktree/**`, `.hypothesis/**`, `.langgraph_api/**`, `.claude/worktrees/**`, `.omo/{drafts,evidence,mock-datasets,ikigai/closing-2026}/**`, `.atl/**`, `.pi/**`, `.claude-flow/**`.

Counted: ~250 `.md` files. **34** `README.md`, **9** `SPEC.md`, **15+** ≥1000-line `.md`. Full list available via the `find` commands in §0.
