# ADR-013: Canonical Scope Discipline (In-Scope vs Out-of-Scope)

> **Status:** ACCEPTED (2026-08-31)
> **Deciders:** matheus (project owner)
> **Load-bearing:** YES — read at start of every session; referenced by all future audits/tours
> **Replaces (informally):** repeated ad-hoc scope reaffirmations in session memory

---

## Context

After 5-lens deep tour (2026-08-31), user surfaced recurring scope violations: same out-of-scope items (algorithm/math execution, PAV code, parallel math kernels) keep re-appearing in tour/audit outputs despite prior decisions to defer/archive. Memory files capture decisions but enforcement is informal. This ADR formalizes the scope contract so future sessions do not re-litigate.

User verbatim (2026-08-31): "preciso de uma estrategia melhor e persistente pra solidificar as specs e adr...voltando no mesmo erro de sempre"

---

## Decision

### IN SCOPE — work that advances the project

| # | Item | Status |
|:--|:-----|:-------|
| 1 | **UEID canonical format** | Q1 decision 2026-08-31 — 5-part canonical; 4-part deprecated; 2-part isolated **(SUPERSEDED by ADR-014 on 2026-09-04: 4-part canonical is the final decision; drift detector regex wins)** |
| 2 | **Vault write invariant** | `tools_vault.py` is canonical sole writer; CLI bypasses via `MarkdownDB`/`Triagem` need resolution (Q-reformulated) |
| 3 | **Mesh data integrity** | PAE validator must gate non-create actions; data evaporation is current bug (Q-reformulated) |
| 4 | **Doc drift** | 40-50% of docs actively misleading; 9+ drifts identified; missing ADRs to be created (Q-reformulated) |
| 5 | **Drift detectors / CI hardening** | Promote load-bearing invariants from convention to test-enforced (Q-reformulated) |
| 6 | **Deep agents harness microscope** | Full inspection of harness, loops, graphs, workflows (user explicit demand 2026-08-31) |

### OUT OF SCOPE — must NEVER be revisited in tours, audits, or decisions

The following are EXPLICITLY excluded from any work, tour, audit, or decision. They are the **closed set** of forbidden topics for this project.

| Forbidden item | Reason / canonical reference |
|:---------------|:----------------------------|
| Algorithm/math execution in agent layer | User verbatim 2026-07-09, 2026-08-28, 2026-08-31: *"o ikigai agent nao cuida de algoritmos matematicos como regas de negocios, politicas"* |
| Algorithm/math execution in orchestrator (vibe-ops) layer | Same as above; orchestrator observes feedback, never executes math |
| `src/agents/ikigai_maintainer/` package (entire tree) | Archived-in-place per Phase B but FULL MATH remains; user demanded DELETE 2026-08-31 |
| `src/ikigai_wrapper.py` (singleton) | Exposes archived graph to `langgraph dev`; DELETE per same directive |
| `score_vectors.py`, `heuristics.py`, `balance.py`, `decompose.py`, `corrections.py` nodes | Math nodes; DELETE |
| `compute_meta_vector`, `compute_qhe`, `compute_score`, `compute_regime`, `compute_phase`, `compute_passion_score`, `compute_skill_score`, `compute_market_score`, `compute_revenue_score`, `compute_course_score`, `compute_alignment_label`, `compute_weighted_priority`, `rank_tasks`, `classify_opportunity`, `apply_hysteresis` | Math functions; out of scope |
| `IkigaiScorer`, `QHEScorer`, `PassionScorer`, `RegimeClassifier`, `PhaseDetector`, `VectorScorer` classes | Out of scope; only `src/operational/packages/core/src/operational/` may instantiate these (canonical kernel) |
| `src/ikigai/src/ikigai/core/scoring/` and `src/ikigai/src/ikigai/core/heuristics/` parallel kernels | Cosmetic residue from parallel refactoring; DELETE |
| `vibe-ops/src/cybernetics/daily_loop.py` composition paths | Already raise NotImplementedError per attribution §3; latent `_compute_target` is dead code |
| PAV TUI/CLI/math (`apps/cli`, `apps/tui`, `src/operational/` user-facing layers) | Desativated per `legacy-pav-ui-era-2026-08-28`; never revive |
| M01/N01/A02/A06 algorithm decisions | Deferred per `algorithm-decisions-defer-2026-08-28`; revisit only on explicit user demand |
| `taskdog_start` @tool | Out of scope until workflow needs it (Phase 7 deferred) |
| Path 3 taskdog MCP gateway | Out of scope; module missing; resurrect only on explicit demand |
| New `taskdog_*` MCP tools | Forbidden by drift detector; Path 1 (harness subprocess) is canonical |
| `vault_write` adding new fork adapters without ADR | Forbidden by attribution §7; sole canonical writer |
| `IKIGAI_TOOLS` adding algo/policy/scoring tools | Forbidden by drift detector; count must stay at 12 |
| Restoring PAV-era tokens, components, or journeys | Forbidden; SUPERSEDED trailers only |

---

## Drift Detector (load-bearing enforcement)

A drift detector test (`tests/test_canonical_scope.py`) MUST FAIL if any production code (agent/MCP/gateway/mesh/orchestrator layer) imports, references, instantiates, or calls any out-of-scope symbol from the table above. This is the enforcement mechanism for this ADR.

**Implementation outline:**
1. Collect out-of-scope symbols into a frozen set in the test file
2. Walk Python source files under `src/agents/`, `src/mcp_server/`, `src/ikigai/src/ikigai/gateway/`, `src/mesh/`, `src/ikigai/src/agents/`, `vibe-ops/src/`
3. AST-scan for `import`, `from ... import`, decorator usage (`@tool` over math-named funcs), class instantiation
4. Fail with list of violations

---

## Consequences

- All future tours/audits MUST filter against this list BEFORE presenting options
- Memory files that contradict out-of-scope MUST be marked SUPERSEDED in frontmatter
- New ADRs that bring back out-of-scope items MUST explicitly mark themselves as RESCINDING ADR-013 (and require explicit user consent)
- If user expresses new intent that touches out-of-scope: first update this ADR, then proceed

---

## Persistent enforcement (how to make this stick)

1. **Session-start hook (future):** Read this ADR on session start; surface scope rules before any tour/audit
2. **Memory index pointer:** `MEMORY.md` references this ADR under "Architecture / scope decisions" with high priority
3. **Drift detector test:** Enforces mechanically in CI (see above)
4. **Pre-flight check:** Before any tour, list which lens touches out-of-scope; if yes, recuse or scope-limit

---

## Related

- `algorithm-scope-reframed-2026-08-30` — IKIGAI = planner, NOT scoring engine
- `algo-cleanup-5-tiers-shipped-2026-08-31` — Tier 1-5 closed active paths; dormant paths pending deletion
- `master-branch-carro-chefe-2026-08-28` — canonical architecture
- `legacy-pav-ui-era-2026-08-28` — PAV desativated
- `algorithm-decisions-defer-2026-08-28` — M01/N01/A02/A06 deferred
- `taskdog-3-paths-architecture-canonical-2026-08-31` — Path 1 canonical, Path 3 deferred
- `ueid-5part-canonical-decision-2026-08-31` — UEID Q1 decision **(superseded by ADR-014 on 2026-09-04)**
- [[Phase 0 audit closure 2026-08-31]]
