---
title: "Structure Audit — life/ — 2026-08-28"
date: 2026-08-28
workflow: w13rdhwpp (45 agents, 2.5M tokens, ~27 min)
---

# Structure Audit — `life/` — 2026-08-28

Multi-angle structural audit of `life-oss/life` with adversarial verification.
Methodology: 3 parallel scans → 40 initial findings → 40 adversarial verifications
(each with skeptic agents attempting refutation) → doc cross-reference pass →
synthesis.

**Token cost:** ~2.5M tokens, ~1055 tool calls
**Session:** `5abe0d4a-04e2-43c6-aa22-bd7f3c3baf63`

> **Note on architecture reframe:** User pivot (2026-08-28, evening) refined the
> morning "command palette" framing. Master branch is now canonical as
> **deep-agent (carro-chefe) doing bidirectional sync between forks-prontas
> widgets (tuiboard / taskdog / solverforge-calendar) ↔ vault local
> `.db.markdown`**. PAV is **desativado** (active stop, not deferred). IKIGAi
> is in design; PAV is NOT being revived as a separate backend. Several "HIGH"
> findings (CLI dual-layout, dual `langgraph.json`, plugins) lose priority
> under this lens — see "Reframe under deep-agent canonical architecture" at
> the bottom.

---

## Executive Summary

**40 findings survived adversarial verification** (0 CRITICAL, 8 HIGH, 4 MEDIUM, 14 LOW, 13 REFUTED).

The biggest sources of risk:

1. **49+ committed zero-byte / shell-quote garbage files** (root + `src/operational/` + `src/ikigai/~/.ikigai/`).
2. **Wide doc drift** between `CLAUDE.md`, `AGENTS.md`, `.gitignore`, and on-disk state (40 cross-ref issues F01–F40).
3. **CI step broken since 2026-06-03**: `verify_mesh` script path mismatch.
4. **24 MB of committed PAV-medic binaries** (`.exe`) inflating every clone.

**Safe-action-first execution order:**

1. `git rm` tracked zero-bytes
2. gitignore future zero-byte patterns
3. Untrack committed `__pycache__/*.pyc` (note: this was *refuted* by verify — see LOW below)
4. Fix broken CI `verify_mesh` step + rename
5. gitignore PAV medic binaries
6. Reconcile CLI dual-layout **[DOWNGRADED — see reframe]**
7. [GATED] Doc drift patches (require explicit user "go" per Refactor Protocol)

---

## CRITICAL findings

*(none)*

---

## HIGH findings

| ID | Path | Evidence | Safe Action |
|----|------|----------|-------------|
| `VFY-CLAUDE-GITIGNORE-001` | `.claude/settings.json` | Tracked team config (hooks, statusLine, permissions). NOT to be gitignored. | KEEP tracked. |
| `verify-mesh-root-misplacement` | `verify_mesh.py`, `verify_mesh_v2.py` (root) | 920B+1602B target `vibe-ops/src/models` (DocBackend, PriorityMatrix, etc.) — NOT the Phase 3 v1 `src/mesh`. CI line 135 `cd vibe-ops && uv run python verify_mesh.py` broken since 2026-06-03 (file not in `vibe-ops/`). | Edit `.github/workflows/ci.yml:135` to drop `cd vibe-ops &&`. Rename `verify_mesh*.py → vibe-ops/verify_vibeops_models{,_v2}.py`. Add new `src/mesh/verify_mesh.py` for Phase 3 v1. Update 10 doc refs. |
| `.codex-.hermes-adversarial-verify` | `.codex/hooks.json` (138 lines, LIVE) | Wires PreToolUse/PostToolUse via `.claude/helpers/hook-handler.cjs`. `.hermes/plans/` is benign scratch. | KEEP `.codex/`. Add README.md. |
| `verify-medic-claim-2026-08-28` | `src/operational/medic/` (24.8 MB, first-party Go) | `module github.com/life-oss/medic`. Bloat = 2 committed `.exe` (medic.exe 14.3 MB + bin/medic.exe 10.1 MB). | gitignore `*.exe` + `bin/` at medic root. Update `src/operational/CLAUDE.md` to mention medic. **[DEFERRED — user pending]** |
| `operational-zero-byte-files` | `src/operational/` root (14 tracked zero-byte files) | Files: `'`, `1\``, `3`, `4.0\``, `6.0`, `60`, `None`, `Path`, `Severity\`,-`, `TimeSeriesSlice`, `env-var`, `tuple[date`, `tuple[str`. Plus 0-byte `docs/architecture/09-INTERFACE-TUI.md`. | `git rm` all 14 + delete `fix_quotes.py`. |
| `verify-agents-dual-package` | `src/ikigai/langgraph.json` | ikigai_maintainer registered in BOTH root `langgraph.json` AND `src/ikigai/langgraph.json`. **[DOWNGRADED — see reframe]** | One langgraph.json per backend = OK. |
| `verify-plugins-live-2026-08-28` | `life/plugins/` | Code wired into `cli/cli.py:17,221,237`, but `DEFAULT_PLUGIN_DIRS` has a double-prefix bug; `config/life.yaml` missing; no `__main__.py`. `load_plugins()` returns `[]` with defaults. **[DOWNGRADED — see reframe: legacy CLI surface]** | Document as legacy. |
| `CLI-DUAL-LAYOUT-2026-08-28` | `cli/cli.py` vs `interfaces/cli/read_tasks.py` | AGENTS.md L92-93 advertises `life mesh show` / `life task add` but exist ONLY in `interfaces/cli/read_tasks.py:245,259`. `data/tasks.jsonl` + `data/feedback.jsonl` missing. **[DOWNGRADED — see reframe: expected under palette model]** | Edit AGENTS.md to redirect. |

---

## MEDIUM findings

| ID | Path | Evidence | Safe Action |
|----|------|----------|-------------|
| `verify-root-unstaged-2026-08-28` | `AGENTS.md`, `CLAUDE.md`, `Makefile`, `.pre-commit-config.yaml` | 4 tracked files modified (198 +/-67) — intentional post-reorg polish (sibling of `d404ac8`). Plus 5 untracked zero-byte root files (`0`, `14`, `agent('Execute`, `int`, `None`). | `git add` + commit in 1 chunk. `rm` untracked orphans + gitignore pattern. |
| `ikigai-data-tree-28mb` | `src/ikigai/data/matheus/` (28.28 MB, 38 files, 99.6% tracked) | Hardcoded path in `src/mcp_server/server.py:149-150`. Includes tracked `.ipynb_checkpoints/` + `byd-tracker.db`. | Add `data/**/*.ipynb_checkpoints/`, `data/**/*.db{,-shm,-wal}` to `src/ikigai/.gitignore`. `git rm --cached` tracked throwaways. |
| `empty-leaf-dirs-verify-2026-08-28` | 3 stale empty dirs: `src/ikigai/src/ikigai/{override,persistence,entities/ops}` | Created 22/06/2026 14:29:39. `scripts/` + `workflows/` are NOT empty (refuted claim). | `git log --diff-filter=D` first; then `rmdir`. Skip `.claude/worktrees/`. |
| `V-MESH-STALE-2026-08-28` | 10 doc refs say `verify_mesh*.py` is at root | `SYSTEMS_TOPOLOGY.md`, `ÍNDICE PROGRESSIVO.md`, `04-agent-mcp-interfaces.md`, `CLUSTER_PROJ.md`, 3 ADRs, CHECKPOINT. | Update after HIGH finding fix. |

---

## LOW findings

| ID | Path | Safe Action |
|----|------|-------------|
| `verify-zero-byte-root-artifacts` | root zero-bytes (`a.last_update\``, `0`, `500`, etc.) | `Remove-Item -Force`; gitignore pattern. |
| `verify-claude-workflows-job-hunter-sl1` | `.claude/workflows/job-hunter-sl1.js` (14,571 B, untracked) | `Remove-Item -Recurse -Force .claude\workflows\`. |
| `openwiki-dot-collision` | `.openwiki/README.md` containing `.env.example` content | Rename `.openwiki/README.md → .openwiki/.env.example`. |
| `.agents-vendored-skill-library` | `.agents/skills/` (67 files, 612 KB, vendored ruflo) | `git rm -r .agents/skills`; KEEP `.claude/skills/`. |
| `verify-gitnexus-gitignore` | `.gitnexus/` (110 MB) | Add `.gitnexus/` to root .gitignore; remove dead `cache/` rule. |
| `verify-hypothesis-gitignore` | `.hypothesis/` (314 KB, 674 files) | Optional: add to .gitignore (defense-in-depth). |
| `ikigai-nested-layout` | `src/ikigai/src/<pkg>/` (depth 5) | Update `src/ikigai/README.md` L26-48 to real layout; add `observability` to pyproject. |
| `VERIFY-STRAY-TILDE-DIR` | `src/ikigai/~/.ikigai/` (12 `.db`, 320 KiB tracked) — literal-tilde path bug | `git rm -r 'src/ikigai/~'`; add `**/~/**` to .gitignore. |
| `contracts-pyproject-orphan` | `src/contracts/pyproject.toml` (never installed) | `rm src/contracts/pyproject.toml`; extend `__init__.py` `__all__`. |
| `verify-src-init-py` | `src/` lacks top-level `__init__.py` (intentional uv-layout) | KEEP. |
| `life-pyproject-claim` | root `life/` package, no pyproject.toml (intentional) | KEEP. |
| `handlers-live-verify` | `handlers/daily.py`, `handlers/weekly.py` (live Typer subprocess wrappers) | KEEP. |
| `phase3_v1_scripts_audit` | `scripts/smoke/phase3_v1.{sh,bat}` | KEEP; 8 doc refs to path. |
| `verify-no-src-imports-root-life` | `src/*` never imports root `life.*` (verified) | KEEP; add 1-paragraph note to CLAUDE.md. |

---

## REFUTED claims (13 — do NOT take proposed actions)

| ID | Original claim | Refutation |
|----|----------------|------------|
| `cluster-md-root-supersede` | CLUSTER_*.md legacy | 154 cross-refs across 41 files; canonical strategic prose. |
| `cli-hub-legacy-refute` | root `cli/centrals/handlers/plugins` legacy | Live CLI hub — pre-2026-08-28 era. **[partially DOWNGRADED under palette reframe]** |
| `verify-ikigai-venv-claim` | `src/ikigai/.venv` committed | NOT tracked; `.gitignore` line 16 excludes. |
| `adversarial-verify-solverforge-calendar-db` | `calendar.db` inside `src/` | UNTRACKED. Adapter uses `data/solverforge_calendar/unified_planning.db`. |
| `langgraph_api_verify` | `src/ikigai/.langgraph_api/` committed | NOT tracked. |
| `cache-not-committed` | `.pytest_cache`, `.ruff_cache` committed | NOT tracked. |
| `operational-packages-core-orphan` | `packages/core` orphan sibling | CANONICAL PAV kernel; uv workspace member. |
| `verify-test-results-empty` | `test_results/` empty leftover | 8 tracked files (~84 KB), audit-cited. |
| `verify-empty-scripts-workflows` | `scripts/` + `workflows/` empty | Both populated. |
| `qa-swarm-stub-claim` | `qa_swarm.yaml` empty stub | 14,048 B / 401 lines, fully wired. |
| `op-docs-002` | `src/operational/docs/` duplicates root `docs/` | DIFFERENT scope (PAV-internal vs system-wide). |
| `root-tests-duplication` | root `tests/` duplicates `src/mesh/tests` + `src/contracts/tests` | Neither exists. Root is sole coverage. |
| `pycache-recent-execution` | root `__pycache__` + `a.last_update\`` show recent execution | 80-day-stale bytecode. |

---

## Safe-Action Execution Order

1. `git rm` 14 tracked zero-byte files at `src/operational/` root.
2. `rm` 5+ untracked zero-byte root files.
3. Append `.gitignore` patterns: zero-byte, literal-tilde, expanded agent runtime state.
4. **SKIP** untrack of "69 committed `.pyc`" — *that claim was refuted (`.pyc` not tracked, just `__pycache__/` dirs ignored correctly)*.
5. Fix CI `verify_mesh` step + rename.
6. gitignore PAV medic binaries (DEFERRED per user).
7. gitignore `src/ikigai/data/matheus/` artifacts.
8. `git rm -r .agents/skills`.
9. `git rm -r 'src/ikigai/~'`.
10. `rm src/contracts/pyproject.toml`; extend `__init__.py` `__all__`.
11. Skip CLI dual-layout fix **[DOWNGRADED]**.
12. Skip dual langgraph.json fix **[DOWNGRADED]**.
13. Skip plugins fix **[DOWNGRADED]**.
14. Remove empty stale dirs (`override/`, `persistence/`, `entities/ops/`).
15. Rename `.openwiki/README.md → .openwiki/.env.example`. Remove `.claude/workflows/`.
16. Fix `src/ikigai/README.md` L26-48 to show real layout.
17. Add `.gitnexus/` to root .gitignore; remove stale `cache/` rule.
18. Decide `data/test-fixtures/`: commit or gitignore.
19. **[GATED]** Commit 4 tracked modifications: `git add AGENTS.md CLAUDE.md Makefile .pre-commit-config.yaml`.
20. **[GATED]** Refactor Protocol — F01-F40 doc patches (require explicit user "go").

---

## Reframe under deep-agent canonical architecture (2026-08-28 evening)

User pivot: master branch = **deep-agent (carro-chefe) doing bidirectional
sync** between forks-prontas widgets (tuiboard / taskdog / solverforge-calendar)
↔ vault local `.db.markdown`. Today:

- **PAV desativado** (active stop, not deferred) — does NOT become a backend
- **IKIGAi in design** — being built as the deep-agent harness
- **forks-prontas widgets** are user views: tuiboard (TS/Bun), taskdog
  (Python FastMCP), solverforge-calendar (Rust rmcp) — all external MCP servers
- **vault `.db.markdown`** is the source of truth (markdown + YAML frontmatter);
  SQLite mirror is derived
- **CLI** is becoming a command palette over MCP contracts (not a build target);
  bespoke TUI/CLI in `apps/` was deleted intentionally per `apps/cli` and
  `apps/tui` reorg; legacy `cli/cli.py` + `centrals/` + `handlers/` + `plugins/`
  surfaces belong to the retired PAV TUI/CLI era
- **Integration pattern**: MCP contracts, not bespoke UI
- **Don't restore old PAV TUI/CLI** (`apps/cli` and `apps/tui` deleted
  intentionally); build new interfaces under `interfaces/`

Under this lens:

| Finding | Re-prioritization | Reason |
|---------|-------------------|--------|
| CLI dual-layout (HIGH) | **Downgraded → expected** | Command palette over MCP contracts; multiple surfaces coexisting is natural. |
| Dual `langgraph.json` (HIGH) | **Downgraded** | Master branch owns root `langgraph.json` (6 graphs all mounted from `vibe-ops/src/langgraph_entry.py`); `src/ikigai/langgraph.json` is vestigial but inconsequential. |
| Plugins fix (HIGH) | **Downgraded** | Plugin system belonged to legacy CLI era; no replacement planned. |
| Medic binaries (HIGH) | **Deferred (carries forward)** | First-party Go tool (`module github.com/life-oss/medic`); needs a separate decision (clone vs submodule vs keep vendored). May serve the deep-agent pipeline — survive pending review. |
| Verify-mesh-root-misplacement (HIGH) | **Still HIGH** | Script-pointing-at-wrong-CI-path is still a defect, orthogonal to architecture. |
| 14 zero-byte tracked (HIGH) | **Still HIGH** | Garbage in git index — orthogonal to architecture. |
| Stray `~` directory (LOW→MEDIUM) | **Still promoted** | Real bug from a tilde-expansion accident; untracked promptly. |
| `interfaces/tui/` empty (Phase 4-6 of reorg) | **Paused** | TUI build is not on the deep-agent roadmap; no bespoke UI. |
| IKIGAi-paused docs (runbooks, bootstrap, vault-layers) | **Paused per ADR-007** | Data-first methodology (5+ SONHO logs gate) still applies; defer feature work. |
| `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` + dependents | **STALE** | Pre-pivot diagnostic; SUPERSEDED trailer applied (see doc-migration plan). |
| `docs/PAV_INVENTORY.md` (1976 lines) + `docs/SYSTEMS_TOPOLOGY.md` + `docs/ARCHITECTURE_INDEX.md` + `docs/CONCEPTUAL_MODEL.md` | **STALE** | PAV-era cargo-chefe framing; SUPERSEDED trailers applied. |

**Net post-reframe:** from 8 HIGH → 2 actionable HIGH (verify-mesh + zero-byte),
with PAV and IKIGAi-era findings demoted to STALE/PAUSED/DEFERRED. Trailers
applied 2026-08-28 to the 10 most-load-bearing stale docs (see
`docs/diagnostics/2026-08-28-doc-migration/00-INDEX.md`).

---

## Cross-references

- Workflow transcript: `C:\Users\mathe\AppData\Local\Temp\claude\C--Users-mathe-code-space-life-oss-life\2248628b-662f-4735-b7ea-26387a8ea0ff\tasks\w13rdhwpp.output`
- Workflow script: `C:\Users\mathe\AppData\Local\Temp\life-audit-workflow.js`
- Doc cross-ref fixes (F01-F40): see `01-f01-f40.md` (forthcoming)
- Refactor Protocol: see `life/CLAUDE.md` "Refactor Protocol" section
- Companion doc-migration plan: `docs/diagnostics/2026-08-28-doc-migration/00-INDEX.md`
- Canonical architecture: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/master-branch-carro-chefe-2026-08-28.md`
- Legacy PAV era context: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/legacy-pav-ui-era-2026-08-28.md`
- Trailer pattern: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/docs-superseded-trailer-2026-08-28.md`
