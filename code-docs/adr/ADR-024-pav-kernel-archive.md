# ADR-024: PAV Kernel Archive

> **Status:** Accepted (2026-08-31 archive execution; drift invariants enforce)
> **Deciders:** matheus (project owner)
> **Source:** W5.3e of dcode-harness-PLAN.md §4

---

## Context

The PAV (Produtividade Algorítmica Visual) kernel was the original
algorithmic operating system for this project — 427 files of pure-arithmetic
business logic including Q_HE composite scoring, regime FSM, habit engine,
energy adjuster, and pomodoro state machine. It shipped with bespoke TUI
and CLI applications in `apps/cli` and `apps/tui`.

Two converging decisions drove the archive:

**PAV TUI/CLI deprecated (2026-08-26).** The build-from-scratch UI
hypothesis failed. Custom terminal applications accumulated I/O concerns
that violated the "pure logic, zero I/O" invariant. Mathematical
auto-performance algorithms in bespoke interfaces had zero consumer demand —
no SONHO logs proved the workflow was being run. The AI-native model
pivot meant: let existing apps consume contracts via MCP; do not build
our own terminal UIs. The `apps/cli` and `apps/tui` trees were deleted
intentionally. New interfaces are built under `interfaces/` instead.

**PAV math deprecated (2026-08-31).** The IKIGAI agent layer was
restructured as planner-only — math/policy/scoring tools are not in
`IKIGAI_TOOLS` (12 tools, enforced by drift invariant in
`src/ikigai/tests/test_canonical_scope.py`). The pure-arithmetic
kernel was physically moved from `src/operational/` to
`archive/legacy-pav/src-operational/` via `git mv` (commit `cc51acc`).
This was an archive, not a deletion, preserving the full audit trail
while removing the kernel from the canonical build.

**What was archived.** The complete PAV arithmetic kernel: 15 Pydantic v2
entities, 7 core algorithms (habit engine `H(t) = 1 − e^(−λ·streak)`,
energy `E = R·(1 − H(t))`, Q_HE composite score, 4-state policy FSM
with hysteresis, 8-state pomodoro SM, sleep validator, daily
consolidator), repository protocol + SQLite persistence, YAML/frontmatter
parsers, and Markdown report generators.

**What was preserved.** The archive at `archive/legacy-pav/` is kept
as a reference. It is self-contained (`uv workspace`, no external runtime
deps), could be revived if the planner-only architecture shows gaps in
6–12 months, and serves as an audit trail of 30+ months of PAV-OS
design iteration.

---

## Decision

1. **PAV TUI/CLI is deprecated.** `apps/cli` and `apps/tui` were deleted
   intentionally. New interfaces are built under `interfaces/`. The PAV
   CLI/TUI must not be restored.

2. **PAV math kernel is archived.** `src/operational/` was moved to
   `archive/legacy-pav/src-operational/` (427 files, commit `cc51acc`).
   The archive is read-only. No new imports, no new code, no execution in
   the canonical build.

3. **IKIGAI agent layer is planner-only.** Per ADR-013, math/policy/
   scoring tools are out of `IKIGAI_TOOLS`. The drift detector in
   `test_canonical_scope.py` enforces this boundary mechanically.

4. **Revival requires explicit user adjudication** per the Revival
   Criteria in the algorithm-attribution-design spec (see below).
   "Algorithm is conceptually interesting" is not a revival trigger.

---

## Consequences

### Positive

- Clean separation: IKIGAI Deep Agent operates as a planner reading
  `./strategics/` markdown; the PAV math kernel is removed from the
  runtime path entirely.
- No algorithm creep into agent code — the drift detector will fail CI
  if any production code imports archived math symbols.
- Revival path is documented: revive the archive first, then re-integrate,
  rather than re-adding scoring tools to the agent layer.

### Negative

- Scoring, regime classification, Q_HE composite, habit streak, and
  energy calculations are not available until revival criteria are met.
- Empirical tuning of any heuristic output is gated on 5+ SONHO log
  observations (per algorithm gate discipline).

---

## Revival Criteria

The following criteria are lifted verbatim from
[`docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md`]
§Revival Criteria:

> An algorithm module may be revived (re-imported by production code,
> modified, or replaced) only when ONE of the following is true AND
> user adjudicates:
>
> 1. **Consumer demand:** A backend service or deep agent reads from
>    this module's exports, AND the module produces incorrect/wrong
>    values in real use. Symptom: failed test or operator report.
> 2. **Telemetry pain:** Telemetry from real SONHO/ONDA logs shows
>    the algorithm output diverges from what the user wants. Symptom:
>    measured mismatch in ≥5 consecutive observations.
> 3. **Day-to-day conflict:** User opens a planning cycle and finds the
>    algorithm's behavior conflicts with their actual decision-making.
>    Symptom: user override + complaint in cycle retrospective.
>
> **Negative criterion:** "Algorithm is conceptually interesting" or
> "Algorithm has clean math" is NOT a revival trigger.

Revival requires user adjudication in addition to meeting one of the
above criteria. The archive is not automatically revived by telemetry
alone.

---

## Cross-references

- [ADR-013 — canonical-scope-discipline](../code-docs/adr/ADR-013-canonical-scope-discipline.md)
  — planner-only invariant; defines what is in-scope vs out-of-scope;
  forbids PAV math in agent layer
- [`docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md`]
  — algorithm attribution model; source of Revival Criteria verbatim above
- [`archive/legacy-pav/SUPERSEDED.md`] — archive directory notice;
  explains what moved, why archived, how to revive
- [Memory: `pav-kernel-archived-2026-08-31`](../../.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/pav-kernel-archived-2026-08-31.md)
  — archive execution record; commit `cc51acc`; 427 files preserved
- [Memory: `legacy-pav-ui-era-2026-08-28`](../../.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/legacy-pav-ui-era-2026-08-28.md)
  — PAV TUI/CLI deprecation context; why build-from-scratch UI hypothesis
  was abandoned
- [`archive/legacy-pav/src-operational/`] — archived PAV arithmetic kernel
  (read-only; not part of canonical build)

---

*ADR-024 — archived 2026-08-31 per user directive. No Co-Authored-By.*
