# DIGEST — repository root scope (canonical serverless tree)

## LOCATIONS WRITTEN

| Path | Score | Role |
|------|-------|------|
| `AGENTS.md` | 8 | Root knowledge base — scope, structure, code map, conventions, anti-patterns |
| `specs/AGENTS.md` | 8 | Milestone-spec corpus — the frontmatter contract (NEW this wave) |
| `.claude/AGENTS.md` | 13 | Agent harness — prompts, 39 skills, loop scripts (NEW this wave) |

Scores: `AGENTS.md` (root contract, 9 sections, 50–150 lines) = files 1 750 (+3) + subdirs 38 (+2) + own config set (setuptools/pyproject/pytest.ini) (+1) + setuptools root (+2) + refs 81 (+3) = **8**; the root file is the KB entry point by assignment, so the band does not gate it.
`specs/` = 3 (101 tracked files) + 2 (100 dirs) + 3 (53 outside refs) = **8** — distinct domain (a spec corpus is readable only from its frontmatter), so the root wave promoted it.
`.claude/` = 3 (246 files) + 2 (6 subdirs) + 1 (`settings.json`, `proven-config.json`) + 2 (59 symbols) + 2 (26 sourceable shell fns) + 3 (186 outside refs) = **13** — the only location in group g8 that deserved its own file.

## LOCATIONS CONSIDERED AND SKIPPED (covered by the parent file)

| Path | Score | Covered by |
|------|-------|-------------|
| `code-docs/` (+9 subdirs) | 9 | root `AGENTS.md` STRUCTURE row + WHERE TO LOOK (`code-docs/adr/`) |
| `docs/` (+11 subdirs) | 8 | root `AGENTS.md` STRUCTURE row + UNIQUE STYLES (PT-BR docset) |
| `vault/` | 8 | root `AGENTS.md` STRUCTURE + ANTI-PATTERNS (ADR-012 sole writer) + UNIQUE STYLES (Planning Note) |
| `vault/ikigai/` | 8 | root `AGENTS.md` — planning-note channel; append-only tree, owner "go" required to touch |
| `tools/vault/` | 9 | `tools/AGENTS.md` WHERE TO LOOK + ANTI-PATTERNS already cover all 6 CLI modules |
| `taskwarrior/` | 13 | `taskwarrior/AGENTS.md` — full workspace: taskrc, 54 shell aliases, PT-BR docs |
| `.agents/skills/` | 7 | `.claude/AGENTS.md` CONVENTIONS — the two parallel skill trees |
| `src/agents/` | 8 | `src/AGENTS.md` WHERE TO LOOK — planner layer, 7 files |
| `src/ikigai/tests/` | 12 | `src/ikigai/AGENTS.md` WHERE TO LOOK — the drift net |
| `code-docs/adr/` | 7 | root `AGENTS.md` WHERE TO LOOK — 39 ADRs incl. ADR-037 |

The other 41 skipped locations and their arithmetic live in the 10 group digests (`src`, `vibe-ops`, `tests`, `interfaces-and-sys-ikigai`, `tooling-meta`, `docs`, `adr-and-specs`, `harness-meta`, `docs-aux`, `vault`); every one is covered by the parent file named there.

## CROSS-SUBTREE FACTS THE ROOT FILE MUST KNOW

1. **One client surface.** `src/transport/mcp_server.py` (195 lines) is the whole published MCP surface: six `@mcp.tool()`s (`search_artifacts`, `get_artifact`, `upsert_artifact`, `delete_artifact`, `list_relations`, `embed_text`) on `FastMCP("ikigai-data")`, transport chosen by `IKIGAI_MCP_TRANSPORT` (stdio | http | streamable-http | sse, default stdio, unknown → `ValueError`), host/port from `FASTMCP_HOST`/`FASTMCP_PORT`. The dependency chain is transport → `src/services/` → `src/data/` → `src/contracts/`.
2. **ADR-037 reversed the storage rule.** The canonical scope (2026-11-01) is serverless / cloud-native: a single cloud store plus a local cache, D3 = Supabase (ADR-037 §4). "Fully local — SQLite + filesystem only, zero cloud deps" was true until that date and is false now.
3. **The purge is drift-guarded, with one gap.** `src/ikigai/tests/test_canonical_scope.py::RETIRED_PATHS` pins 12 retired paths as absent; `src/ikigai/src/observability` is equally absent but **not** listed.
4. **The cybernetic kernel is the pipeline, not `cybernetics/`.** `vibe-ops/src/cybernetics/engine.py` defines `BinaryKnowledgeTree` (a gap-search knowledge tree); the Adjuster is `vibe-ops/src/pipeline/policy_engine.py::PolicyEngine` with `POLICY_MAP` over `PolicyState` (PUSH / MAINTAIN / REDUCE / RECOVER) declared in `vibe-ops/src/schemas/pydantic_v2.py`.
5. **The drift net is five files, not three.** `test_canonical_scope.py`, `test_drift_invariants.py`, `test_drift_detector.py`, `test_drift_state.py` under `src/ikigai/tests/`, plus `src/ikigai/tests/contracts/test_dom_kinds_drift.py`. `test_drift_extended_invariants.py` — named by ADR-032…035 — does not exist.
6. **Two import identities, one package name.** `from src.contracts.X` and `from sys_ikigai.X` resolve to distinct module objects; monkeypatch both. `src/` has no `__init__.py`; `src/mesh/` has no `pyproject.toml`.
7. **`.gitignore` swallows 1–4 letter root dirs** (`/[a-zA-Z]` … `/[a-zA-Z][a-zA-Z][a-zA-Z][a-zA-Z]`, lines 509–513); `!/src/`, `!/docs/`, `!/bin/`, `!/life/` (522–536) re-admit four of them. Only `data/` and `logs/` stay swallowed.
8. **The harness is published but not canonical.** `.claude/` holds 246 files (222 Markdown, 12 code, 0 Python). Four `ikigai-*` skills are one-line machine-absolute paths to an absent `src/ikigai/src/agents/v2/skills/`; three hook helpers named by `settings.json`/`.codex/hooks.json` do not exist; `agents.v2.skills` is absent, so `/triage` and `/extract` fail at runtime.
9. **The mesh has two adapters.** `CliAdapter` and `TaskdogAdapter` only; the calendar adapter left with the PC-only scope, and v1 is `create`-only.

## VERIFICATION

- `git ls-files` counts at HEAD `b28b3356`: 1 750 tracked files in total (20 at the repo root + 38 tracked root directories); `specs/` 101 files / 100 dirs; `.claude/` 246 files / 6 subdirs; `docs/` 205; `vault/` 175; `code-docs/` 69; `tests/` 85 (71 `.py`, 9 `.sh`, 3 `.bat`, 2 `.md`); `src/` 226.
- Header and length audit: root 147 lines with all 9 headers; `specs/AGENTS.md` 73; `.claude/AGENTS.md` 73; `life/AGENTS.md` 80 — every file inside its band.
- Nine stale root claims re-measured and corrected (legacy-pav row, `code-docs/` subdir list, missing `docs/`, stale commit header, "fully local" bullet, drift-test pointer, zero-byte count 75, PT-BR `docs/`, gitignore negation claim); `code-docs/README.md` + `code-docs/00-INDEX.md` still point at the removed `code-docs/ard/` tree and `life-ops/` root.
- Every path named above was checked against the live tree; the six-tool count comes from the `@mcp.tool()` decorators, the `RETIRED_PATHS` count from the drift test, and `PolicyState` from the schema module.
