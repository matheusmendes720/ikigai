# AGENTS.md — src/ikigai

## OVERVIEW
Poetry subpackage holding the IKIGAI agent layer: MCP gateway, LangGraph v2 graph, Paperclip orchestrator, and the drift-net test suite (score 17 — 374 files, 291 Python, 9 subdirs, 2 589 symbols, 236 import sites in 76 repo files).

## STRUCTURE
```
src/ikigai/
├── pyproject.toml   # Poetry manifest + ruff/mypy/pytest config for this subpackage
├── src/             # runtime source — 6 installed packages (see src/AGENTS.md)
├── tests/           # drift net + unit/e2e suite (112 .py, 31k LOC)
├── contracts/       # Meta-Planner Proposal contracts (Pydantic v2 strict)
├── souls/           # markdown persona profiles (planner / critic / stoic)
├── tools/           # orphan stdlib CLIs: views.py, vault_taskdog_sync.py
├── scripts/         # sitecustomize hook, trace repro/verify
├── bin/             # single-process orchestrator (gateway + HTTP :8765)
├── data/            # runtime state — gitignored
└── docs/            # deep-dive report + observability notes
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| LangGraph graphs | `langgraph.json` | 5 entries: `ikigai_maintainer_v2`, `ikigai_fork_smoke`, `ikigai_taskdog_mcp`, `ikigai_paperclip`, `ikigai_dynamic` |
| MCP server entry | `run_mcp_server.py` | inserts `src/` on `sys.path`, then `mcp_server.server:main` |
| Console scripts | `pyproject.toml` `[tool.poetry.scripts]` | `ikigai-maintainer-mcp`, `ikigai-deep-agent`, `paperclip`, `paperclipai-bridge` |
| Windows launcher | `ikigai.bat` | `chat\|agent\|run\|list\|checkpoint\|mcp\|gateway\|events\|backend`; sets `PYTHONPATH` to `src` + `..\..\src` |
| Gateway launcher | `start_mcp_gateway.sh` | interactive menu over ikigai / tuiboard / taskdog / solverforge |
| Proposal schema | `contracts/proposal.py` | 11 exported models |
| Persona format | `souls/*.md` | `## Voice` / `## Reasoning Style` / `## Constraints` (7 never-do rules) / `## Sample Behaviors` |
| Runtime DBs | `data/` | `ikigai_checkpoints.db`, `paperclip.db`, `paperclip_dynamic.db` |

## CONVENTIONS
- **Two import identities for the same files.** Poetry installs `src/` flat (`agents.*`, `chat.*`, `mcp_server.*`, `observability.*`, `strategics.*`, `plugins.*`); repo-root code imports them as `src.ikigai.src.*`. Production uses the dotted form, tests use the bare form — patch both.
- **The mypy gate is `poetry run mypy -p src.ikigai.src`** — never `mypy src/`. `mypy_path = ["../.."]` + `explicit_package_bases` + `namespace_packages` exist so the only identity mypy can assign is `src.ikigai.src.*`. There is deliberately no `files`/`modules` key.
- **Ruff deviates from repo defaults here**: line-length 100, `select = [E,F,W,I,N,UP,B,A,C4,PT,RUF]`, `ignore = [E501]`, ruff pinned `^0.17.3` (an open range would silently move the CI gate). Every per-file-ignore carries a comment explaining why — read it before removing the ignore.
- **pytest config lives in this `pyproject.toml`**, not the repo root: `testpaths = ["tests"]`, `pythonpath = ["src", "../.."]`, `addopts = "-v --tb=short"`, plus two `filterwarnings` ignores for PAV-internal models.
- **`from __future__ import annotations` at the top of every module.**
- **Stray zero-byte files at this level** (`0`, `None`, `Path`, `str`, `dict[str`, `noise*.log`, `pytestdebug.log`, session `.txt` dumps) are bash-redirect typos; the root `.gitignore` lists `src/ikigai/<name>` entries for them. Leave them alone.

## ANTI-PATTERNS
- **NEVER delete `start_mcp_gateway.sh`** — preserved per the append-only invariant.
- **NEVER commit `.env`** — gitignored; `.env.example` is the template, and a leaked LangSmith key must be rotated.
- **NEVER write under `src/ikigai/data/`** — runtime state, gitignored, not source.
- **Do not treat `tools/` as live code.** Zero importers repo-wide; `views.py` advertises a `python -m tools.ikigai_views` entry point that does not exist (the module is `views.py`), `find_vault_root()` prefers the legacy `life-ops/ikigai/data/<persona>` layout, and `vault_taskdog_sync.py` hardcodes a WSL path (`/mnt/c/Users/mathe/code_space/apps/dev-tools/taskdog`).
- **`souls/loader.py` rejects path traversal** (`/`, `\`, `..`) before touching the filesystem. Keep it that way.

## NOTES
- `SPEC.md` is the canonical v1.0 spec; `MCP_GATEWAY.md` documents the four MCP surfaces; `docs/observability/` records the acknowledged exception to the "fully local" rule (observability egress is opt-in).
- `scripts/sitecustomize.py` is a stdlib-only import hook that always returns `None` from `find_spec`, so it never claims to provide a module.
