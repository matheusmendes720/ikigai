# Archived — PAV Kernel (Produtividade Algorítmica Visual)

> **Status:** ARCHIVED 2026-08-31 — preserved append-only, NOT canonical.
> **Source of truth:** deep-agent canonical (`src/ikigai/`) per
> [ADR-013: canonical-scope-discipline](../../code-docs/adr/ADR-013-canonical-scope-discipline.md).

## What

The original `src/operational/` package — 427 files of pure-arithmetic
business logic for the PAV operating system:

- 15 Pydantic v2 entities (Routine, Habit, Pomodoro, Policy, Journal, ...)
- 7 core algorithms (habit engine `H(t) = 1 − e^(−λ·streak)`, energy
  `E = R·(1 − H(t))`, Q_HE composite score, 4-state policy FSM with
  hysteresis, 8-state pomodoro SM, sleep validator, daily consolidator)
- Repository Protocol + InMemory + SQLite persistence layer
- YAML/frontmatter parsers + Markdown daily/weekly report generators
- 10-sprint build (scaffolding → sign-off), 30-40 day arc

See [`./src-operational/CLAUDE.md`](./src-operational/CLAUDE.md) for the
package-level overview and `README.md` for the legacy quick-start.

## Why archived (not deleted)

Per user directive 2026-08-31, the IKIGAI agent layer is **planner-only** —
math/policy/scoring tools have been stripped and the drift detector in
`src/ikigai/tests/test_canonical_scope.py` enforces
`IKIGAI_TOOLS = 12` (no `ikigai_score`, `ikigai_regime`, etc.).

Three reasons to preserve rather than delete:

1. **Append-only invariant** — the project keeps `vault/`, `vibe-ops/`,
   `strategics/`, and `data/review_queue/` append-only. The PAV kernel
   had no production callers outside its own self-contained tests, but
   the convention is preserved.
2. **Audit trail** — 427 files represent 30+ months of design iteration
   on the PAV-OS pivot. Future engineers (or the user, one year from now)
   need a record of *why* the math kernel was deprecated and *what*
   was tried.
3. **Revivable** — the package is self-contained (`uv workspace`,
   no external runtime deps) and could be revived if the
   planner-only IKIGAI architecture showed gaps in 6–12 months.

## Scope discipline (canonical reference)

ADR-013 — *canonical-scope-discipline* — defines what lives where:

| Layer | Responsibility | Math/policy? |
|-------|----------------|--------------|
| `src/ikigai/src/agents/` | Planner — 12 IKIGAI_TOOLS bound to MCP | NO |
| `src/ikigai/src/mcp_server/` | Agent → MCP gateway | NO |
| `src/mesh/` | Cross-fork task view + sync | NO |
| `src/contracts/` | Canonical Pydantic schemas | NO |
| **This archive** | **PAV arithmetic kernel** | **YES (preserved)** |

If math/policy is needed in the future, the canonical answer is to revive
the archived kernel rather than to re-add scoring tools to the agent
layer (the drift detector will fail CI).

## How to revive

```bash
cd archive/legacy-pav/src-operational/
uv sync                # uv workspace, self-contained
uv run pytest          # 2839 tests as of 2026-08-31
uv run ruff check packages/core/src/
uv run mypy packages/core/src/
```

The package's own `CLAUDE.md` and `README.md` continue to document the
sprint arc and source-of-truth specs.

## Cross-refs

- [ADR-013 — canonical-scope-discipline](../../code-docs/adr/ADR-013-canonical-scope-discipline.md)
- [PAV-OS pivot 2026-08-26 trailer](../../docs/design-system/34-superseded-pav-era-tokens.md)
- [legacy-pav-ui-era memory](../../.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/legacy-pav-ui-era-2026-08-28.md)
- [GitHub commit `240ae08`](../../../../.git/refs) — math kernel stripped from agent/MCP/gateway

---

*Archived 2026-08-31 per user directive. NO Co-Authored-By.*
