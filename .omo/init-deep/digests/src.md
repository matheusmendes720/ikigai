# DIGEST — src/ subtree

## LOCATIONS WRITTEN

| Path | Score | Role |
|------|-------|------|
| `src/AGENTS.md` | 15 | Subtree root — serverless source layer, import identities |
| `src/contracts/AGENTS.md` | 15 | Canonical Pydantic v2 contracts (DOM + planning tree) + store SQL |
| `src/ikigai/AGENTS.md` | 12 | Poetry sub-project: strategics loader, meta-planner contracts, souls, tests |
| `src/ikigai/src/AGENTS.md` | 2 | Post-purge stub — only the read-only strategics loader |
| `src/mesh/AGENTS.md` | 15 | Phase 3 cross-fork mesh: adapters + append-only review queue |
| `src/mesh/adapters/AGENTS.md` | 11 | Fork boundary — `ForkAdapter` Protocol + two adapters |
| `src/services/AGENTS.md` | 6 | Domain services — the only layer a client reaches (ADR-037) |
| `src/transport/AGENTS.md` | 2 | The six-tool MCP surface over the services |

Scores: 3 files>20 + 2 subdirs>5 + 2 code>70% + 1 own config + 2 pkg `__init__.py` + 2 symbols>30 + 2 exports>10 + 3 refs>20; code = (.py+.sql)/tracked, exports = summed `__all__`, refs = import sites in tracked `.py` outside.
`src/` 3(226)+2(9)+1+2+2(1518)+2(200)+3(146/51) = **15**; code 152/226
`src/contracts/` 3(29)+2(26/29)+1+2+2(90)+2(103)+3(111/73) = **15**; 1 subdir
`src/ikigai/` 3(128)+2(8)+1+2+2(985)+2(16) = **12**; code 78/128, refs 1
`src/ikigai/src/` 2 = **2**; 3 files, code 2/3, 3 symbols, 3 exports, 1 ref
`src/mesh/` 3(30)+2(27/30)+1+2+2(310)+2(43)+3(106/34) = **15**; 2 subdirs
`src/mesh/adapters/` 2(6/7)+2+2(72)+2(14)+3(75/34) = **11**; 7 files, 1 subdir
`src/services/` 2(5/6)+2+2(38) = **6**; 6 files, 9 exports, 8 ref sites
`src/transport/` 2 = **2**; 3 files, code 2/3, 15 symbols, 5 exports, 1 ref

## LOCATIONS CONSIDERED AND SKIPPED (covered by the parent file)

| Path | Score | Covered by |
|------|-------|-------------|
| `src/agents/` (+memory 4, +reflection 6) | 8 | `src/AGENTS.md` WHERE TO LOOK — planner layer, 7 files |
| `src/data/` | 4 | `src/AGENTS.md` ANTI-PATTERNS — 3 modules, 2 tracked `*.db` + 2 `pytest-tmp` paths |
| `src/life_tatics/` (+domain 2) | 2 | `src/AGENTS.md` WHERE TO LOOK — Typer CLI, 4 `.py` + 2 `.md` |
| `src/planner/` | 0 | `src/AGENTS.md` ANTI-PATTERNS — 8 `.md`, 0 code |
| `src/ikigai/tools/` | 4 | `src/ikigai/AGENTS.md` STRUCTURE — 2 dev CLIs, 0 importers |
| `src/ikigai/tests/` (+store 6, +contracts 4, +services 4, +transport 4, +skills 4, +reports 0) | 12 | `src/ikigai/AGENTS.md` WHERE TO LOOK — the drift net |
| `src/mesh/cli/`, `src/mesh/adapters/tests/` | 4, 2 | `src/mesh/AGENTS.md` STRUCTURE; `src/mesh/adapters/AGENTS.md` WHERE TO LOOK |

Also under `src/ikigai/`: contracts 6, souls 2, scripts 2, docs 0, data 3 — `src/ikigai/AGENTS.md` STRUCTURE.

## CROSS-SUBTREE FACTS THE ROOT FILE MUST KNOW

1. **The ADR-037 purge is drift-guarded; one purged path is unguarded.** `src/ikigai/tests/test_canonical_scope.py::RETIRED_PATHS` pins 12 retired paths as absent (0 tracked each) — `src/ikigai/src/{agents,chat,mcp_server,plugins,ikigai_wrapper.py,gateway_client.py}`, `src/tuiboard`, `src/solverforge_calendar`, `interfaces/tui`, `vibe-ops/vibeops-tui`, `plugins/paperclipai`, `langgraph.json`. `src/ikigai/src/observability` is likewise absent but **not** listed; `src/ikigai/src/` now holds only `src/ikigai/src/strategics/` (2 files) + `src/ikigai/src/AGENTS.md`.
2. **The client surface: one module, six tools, one importer.** `src/transport/mcp_server.py` (195 lines) registers `search_artifacts`, `get_artifact`, `upsert_artifact`, `delete_artifact`, `list_relations`, `embed_text` on `FastMCP("ikigai-data")`; the transport comes from `IKIGAI_MCP_TRANSPORT`. The only tracked file importing `src.transport` is `src/ikigai/tests/transport/test_mcp_tools.py`.
3. **The live dependency chain is transport → services → data → contracts.** `src/transport/mcp_server.py` imports `src/data/client.py` and `src/data/repository.py` plus the three service modules; all three import `src/data/repository.py`. `src/services/sync.py` (381 lines) exposes `VaultSync`, `VaultSource`, `SyncReport`, `default_sources` and never writes the vault.
4. **Five identical copies of the canonical UEID pattern live in `src/`, plus one divergent one.** `src/contracts/common.py::_UEID_PATTERN` (`[a-z]{2,8}:…`) is copied verbatim into the `artifacts_uid_format` CHECK of `src/contracts/migrations/0001_init.sql` and into `src/mesh/adapters/taskdog.py`, `src/mesh/dep_subsystem.py`, `src/mesh/taskdog_cli.py`, `src/mesh/td_dep.py`; `src/ikigai/contracts/proposal.py::_UEID_REGEX` is the divergent `{2,5}` 4-part form — each is asserted separately, do not "unify" them.
5. **The planner layer's namespace merge is inert.** `src/agents/__init__.py` appends `src/ikigai/src/agents` to `__path__` under an `is_dir()` guard; that sibling is purged, so the guard is false and nothing merges — yet the docstring still advertises "IKIGAI_TOOLS = 12 planning tools" and "the repo ships TWO directories named `agents`". `src/mesh/adapters/__init__.py` likewise still documents "v1 scope: only CREATE actions are wired".

## VERIFICATION

- `git ls-files` counts: src 226, contracts 29, ikigai 128, ikigai/src 3, mesh 30, mesh/adapters 7, services 6, transport 3, ikigai/tests 66.
- `git ls-files` on every purged path → 0 tracked files; the on-disk copies of `src/tuiboard`, `interfaces/tui`, `plugins/paperclipai/`, `archive/legacy-pav` and `langgraph.json` are gitignored leftovers (`.gitignore:591,593,609,610,611`), not published.
- Symbols/exports/refs from an AST pass over tracked `.py`; the 6 tools come from `@mcp.tool()`; `src/mesh/adapters/__init__.py::__all__` = `CliAdapter`, `ForkAdapter`, `TaskdogAdapter`; `src/mesh/adapters/solverforge_calendar.py` is absent.
- Every path named above was checked against the live tree at HEAD `2ae8478`; written headers hand-set 8/8/7 for adapters/services/transport, totals above recomputed.
