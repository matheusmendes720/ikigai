# Plano Trimestral — Deep Agent Build (Q4-2026)

> **Status:** ACTIVE — first vault infra project (per [[deep-agent-build-q4-vault-plan-2026-08-28]])
> **Owner:** matheus
> **Approved:** 2026-08-28 (claude-code interactive planning session)
> **Companion:** `placeholder.md` (sibling — append-only invariant preserved)
> **Period:** 2026-10-05 → 2026-12-20 (ISO weeks W41–W52, plus W53 if applicable; ~66 working days)

---

## 1. Contexto

O **Deep Agent** é a frente canônica do master branch (carro-chefe), per [[master-branch-carro-chefe-2026-08-28]]. Bidirecional:
- **Forks-prontas** (tuiboard / taskdog / solverforge-calendar) ↔ **vault local** `.db.markdown`

Arquitetura dual-layer (per [[interfaces-architecture-2026-08-27]]):
- **Forks-prontas** = user views
- **CLI/TUI nativos** = backend control plane ONLY (operator), NOT user views
- **vault-journal** deferred

Build sequence non-negotiable: **backend → data → agent → algorithms LAST** (per [[pav-as-ikigai-subsystem-2026-08-28]] + [[vault-planning-false-gap-2026-08-28]]).

This plan covers the **backend phase** for the Deep Agent build (Submetas B0–B4 of the canonical 7-phase ordering, per [[backend-phase-reordering-2026-08-28]]). Submetas B5 (agent wiring) e B6 (vault sync) defer to 2027-Q1.

---

## 2. Backend Phases Escopadas

5 fases, ~13 semanas. Mapeamento sprint ↔ fase:

| Fase | Phase name | Weeks | Sprint | Início | Fim |
|------|-----------|-------|--------|--------|-----|
| **B0** | Hygiene | 1 | S1 | 2026-10-05 | 2026-10-09 |
| **B1** | A2UI schema | 2 | S2–S3 | 2026-10-12 | 2026-10-23 |
| **B2** | Server-mgmt CLI | 2 | S4–S5 | 2026-10-26 | 2026-11-06 |
| **B3** | MCP gateway | 2 | S6–S7 | 2026-11-09 | 2026-11-20 |
| **B4** | Queue worker | 2 | S8–S9 | 2026-11-23 | 2026-12-04 |
| (deferred) | | | | | |
| B5 | Agent wiring | 2027-Q1 | — | — | — |
| B6 | Vault sync | 2027-Q1 | — | — | — |

Buffer restante (W50–W52): retrospectiva de trimestre + spillover técnico + holiday slack.

---

## 3. "Done" Criteria Por Fase (não-matemático)

Per [[vault-planning-false-gap-2026-08-28]]: zero numeric thresholds que re-ancorem em Q_HE / regime / vector scoring. "Done" = artefatos concretos + verificáveis:

| Fase | "Done" quando… |
|------|----------------|
| **B0 hygiene** | `uv sync` succeeds from fresh clone + `pav doctor` returns OK + `.github/workflows/ci.yml` verde + docs (CLAUDE.md, README) match code state (or estão flagged com trailer per [[docs-superseded-trailer-2026-08-28]]) |
| **B1 A2UI** | Schema published em `src/contracts/a2ui.py` (or `src/mesh/a2ui.py`) com Pydantic v2 strict (`frozen=True`, `extra="forbid"`) + ≥ 1 demo end-to-end script em `examples/` + ≥ 5 unit tests passing em `tests/` |
| **B2 server-mgmt CLI** | Typer CLI `pav server` com 5 subcommands (`ls`, `inspect`, `status`, `start`, `stop`), output `--json` supported, ≥ 10 tests pass, demo script end-to-end |
| **B3 MCP gateway** | MCP server starts cleanly via `ikigai.bat mcp` + ≥ 3 tools expostos wirados à A2UI + server-mgmt + integration test verde em `tests/integration/` |
| **B4 queue worker** | Producer + consumer com filesystem queue (`data/review_queue/`, append-only) + idempotency on `ueid` + ≥ 8 tests pass + ≥ 1 end-to-end demo (write-to-queue → consumer-process) |

---

## 4. Decision Gates em Scope

### 4.1 — AG3 Gateway Orphan (BLOCKER pre-B3)

Per [[ag3-gateway-orphan-2026-08-27]]: ~1600 lines de gateway + adapters + tests no worktree `feat/data-model-unification` **NUNCA mergeado**.

**Required decision: MERGE or DISCARD?** Must resolve **antes de S6 (B3 start, 2026-11-09).**

| Opção | Custo | Risk | Outcome |
|-------|-------|------|---------|
| **A. Cherry-pick** to clean branch + run tests | ~2-3 days | may surface latent bugs | Shortcut para B3 (frees S6-S7) |
| **B. Discard entirely**, rewrite from spec | ~1 semana | clean slate, mais tempo | Nada desperdiçado; spec-driven rebuild |

**Suggested trajectory:** Start B3 prep work (W45-W46) já com a decisão tomada. Hold-up blocker until choice é feita.

---

## 5. Sprint Cadence

- **1 sprint = 2 semanas** (Mon–Fri, ~10 working days úteis)
- **Wave = quarter** (Q4 inteiro = 1 wave containing 4-5 sprints)
- **Weekly review** toda sexta-feira à tarde (template em `03-revisões-semanais/`)
- **Daily log** end-of-week (compliance, not velocity — não geramos ruído)
- **Sprint boundaries** = fase boundaries (1 sprint = 1 fase, exceto B0 que é 1 semana)

---

## 6. Open Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| AG3 merge/discard decision blocks B3 | HIGH | Force decision by end of W45; gate B3 start on resolution |
| A2UI spec (referenced in code, not validated end-to-end) needs spike primeiro | HIGH | Spike em W2-S2 (within B1) para validar assumptions antes de codar schema |
| Vault sync (B6) deferred → B5 (agent) has insufficient design context | MEDIUM | Document explicit deferred-dependency in B5 stub |
| CLI/TUI native interfaces scope ambiguity (per [[pav-cli-tui-future-feature-2026-08-27]]) not fully addressed in Q4 | MEDIUM | Accept ambiguity for Q4; resolve in 2027-Q1 during B5/B6 |
| Single-owner risk (only matheus ships) | MEDIUM | Document review criteria so future contributors can onboard |

---

## 7. Cross-references

### Memory / decisions
- [[master-branch-carro-chefe-2026-08-28]] — canonical direction
- [[backend-phase-reordering-2026-08-28]] — B0-B6 canonical order
- [[vault-planning-false-gap-2026-08-28]] — algorithm-defer scope rule
- [[feedback-precision-calibration-2026-08-28]] — narrow corrective, no swing-to-extreme
- [[interfaces-architecture-2026-08-27]] — dual-layer interface context
- [[ag3-gateway-orphan-2026-08-27]] — pre-B3 decision gate
- [[pav-as-ikigai-subsystem-2026-08-28]] — PAV as subsystem-extension
- [[job-hunter-paused-handoff-2026-08-28]] — job_hunter integration is SPEC-ONLY (out of Q4 scope)
- [[job-hunter-life-integration-spec-only-2026-08-28]] — no code, no consumer this half
- [[q1-q2-q3-q4-resolved-2026-08-27]] — Q1-Q4 cleanup context
- [[reorg-bugs-p0-fixed-2026-08-27]] — what was already fixed pre-Q4
- [[pav-cli-tui-future-feature-2026-08-27]] — operational CLI/TUI status
- [[docs-superseded-trailer-2026-08-28]] — canonical trailer pattern (applies to outdated docs found in B0)

### Vault files
- `01-plano-trimestral/placeholder.md` — sibling (append-only)
- `00-sonho/placeholder.md` — parent sonho (TBD; infra-level, no algo content)
- `02-onda-1/`, `02-onda-2/`, `02-onda-3/` — wave plans (populated per sprint)
- `03-revisões-semanais/` — weekly reviews (one per ISO week)
- `04-relatórios-diários/` — daily retros (end-of-week batch)

### Outside vault
- `src/contracts/` — where B1 A2UI schema lands
- `src/mesh/` — gateway + adapters land here for B3/B4
- `interfaces/cli/` — B2 server-mgmt CLI
- `data/review_queue/` — B4 queue worker filesystem target
- `docs/superpowers/specs/` — spec references (already shipped: A2UI protocol spec + Pydantic schemas)

---

## 8. What is OUT OF SCOPE for this plan

Per [[vault-planning-false-gap-2026-08-28]], deferred until backend + data + agent phases are functional:

- 5 IKIGAi vector scoring (P/S/M/R/C) with current → target
- Regime thresholds (PUSH/MAINTAIN/REDUCE/RECOVER) + hysteresis values
- Q_HE math, 5x3x3 aggregates, weighted scoring
- Kill conditions with numeric thresholds tied to Q_HE / regime
- Quarterly bets with IKIGAi-vector-falsification criteria
- Socratic interview Q1-Q7 answers (vector-anchored horizon)

This plan is a **human-side SOT for infra**. The Deep Agent that will eventually write to vault is future infrastructure (master branch canonical, IKIGAi em design).

---

## 9. Update Cadence

- **Once at quarter start:** Lock-in after this approval.
- **Light touch at each sprint boundary:** Adjust scope if AG3 decision or A2UI spike changes reality.
- **Lock at quarter close:** Archive to `99-archive/2026/` when 2027-Q1 plan takes over.

---

*Scaffold: Plano Trimestral v1 — Infra Project (Real) · Deep Agent build · 2026-Q4 · Claude Code interactive session 2026-08-28.*
