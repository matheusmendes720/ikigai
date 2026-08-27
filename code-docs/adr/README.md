# ADRs — Master Index

Cross-cutting Architecture Decision Records for the Algorithmic Life OS.
Each ADR captures a single architectural decision: Status, Date, Context,
Decision, Consequences, Alternatives, Implementation Rules. Append-only —
ADRs are immutable once Accepted; superseded ADRs are linked, never edited.

> **Note:** This is the index for `code-docs/adr/`. Two other ADR surfaces
> exist and are linked from `00-INDEX §7`:
> - `vibe-ops/architecture/` (cybernetic engine — see `VIBE-OPS.md`)
> - `life-ops/operational/docs/adr/` (PAV kernel — see `OPERATIONAL.md`)

The full 27-document consolidation across all 3 surfaces is documented in
`2026-08-27-master-adr-index.md` (§1 + §1.1 tables).

---

## ADR Index

| File | Status | Date | Subject |
|------|:------:|------|---------|
| `ADR-007-data-first-methodology.md` | Accepted | 2026-07-02 | Data-first methodology: schema → storage → adapters |
| `ADR-008-ikigai-vector-count.md` | 🟡 Proposta | 2026-08-27 | IKIGAI vector count (5 vs 4) — decision required |
| `ADR-009-pydantic-strict-mode-invariance.md` | 🟡 Proposta | 2026-08-27 | Pydantic v2 strict mode across all entities — decision required |
| `ADR-010-dual-claude-md-scope.md` | 🟡 Proposta | 2026-08-27 | Dual `CLAUDE.md` scope strategy — decision required |
| `ADR-011-ikigai-mcp-http-sse-transport.md` | 🟡 Proposta (recommended) | 2026-08-27 | HTTP+SSE transport for IKIGAI MCP server |
| `2026-08-27-decision-questionnaire.md` | 🟡 Draft | 2026-08-27 | 4 Proposta ADRs (008-011) reframed as decision questions |
| `2026-08-27-master-adr-index.md` | 🟡 Draft | 2026-08-27 | Cross-surface consolidation (11 cross-cutting + 6 cybernetic + ~13 PAV) |
| `2026-08-27-cross-cutting-triage.md` | 🟡 Draft | 2026-08-27 | Decision-dependency matrix + recommended order for ADRs 008-011 |
| `OPERATIONAL.md` | index | — | Pointer to PAV kernel ADR set (`life-ops/operational/docs/adr/`) |
| `VIBE-OPS.md` | index | — | Pointer to cybernetic engine ADR set (`vibe-ops/architecture/`) |

Base path: `C:\Users\mathe\code_space\life-oss\life\code-docs\adr\`

---

## Status Legend

| Status | Meaning |
|--------|---------|
| **Accepted** / **Aceita** | Decision is final and binding. No edits — supersede, don't rewrite. |
| **Proposta** / **Proposed** | Awaiting user decision. Can be edited freely. |
| **🟡 Draft** | New ADR or support doc being drafted. Can be edited freely. |
| **Superseded** | Replaced by a newer ADR. Link to replacement; never edited. |
| **Rejected** | Decision was considered and rejected. Link to rationale; never edited. |
| **index** | Pointer file (no status); routes to another ADR surface. |

---

## Cross-References

| Topic | Canonical source |
|-------|------------------|
| Data-first methodology | `ADR-007-data-first-methodology.md` |
| IKIGAI vector count | `ADR-008-ikigai-vector-count.md` (Proposta) |
| Pydantic strict mode | `ADR-009-pydantic-strict-mode-invariance.md` (Proposta) |
| Dual CLAUDE.md scope | `ADR-010-dual-claude-md-scope.md` (Proposta) |
| HTTP+SSE MCP transport | `ADR-011-ikigai-mcp-http-sse-transport.md` (Proposta, recommended) |
| Per-ADR decision aids | `2026-08-27-decision-questionnaire.md` |
| Cross-cutting decision order | `2026-08-27-cross-cutting-triage.md` |
| Cross-surface consolidation | `2026-08-27-master-adr-index.md` |
| Cybernetic engine ADRs (001-006) | `vibe-ops/architecture/` via `VIBE-OPS.md` |
| PAV kernel ADRs (12 PRDs + 3 sprints) | `life-ops/operational/docs/adr/` via `OPERATIONAL.md` |
| Pending-decision + ADR consolidation | `code-docs/00-INDEX.md §8j` |
| Known gaps (G8 = this README) | `code-docs/00-INDEX.md §12` |

---

## Maintenance

When adding a new ADR:

1. **Append-only** — never edit an Accepted ADR. Supersede, don't rewrite.
2. **Filename convention** — `ADR-NNN-kebab-slug.md` for fixed-numbered ADRs; `YYYY-MM-DD-<topic>.md` for drafts and support docs.
3. **Numbering** — sequential across all 3 surfaces: next is **ADR-012** (per `2026-08-27-master-adr-index.md` §7.4).
4. **Cross-reference** — every ADR points to canonical source (file + line range or section).
5. **Update this README** — add row to the index table; bump counts.
6. **Update `code-docs/00-INDEX.md §7b`** — keep both indexes in sync.
7. **Update `2026-08-27-master-adr-index.md`** if this is a new cross-cutting ADR (so the 3-surface consolidation stays canonical).

---

*ADR master index — v1.0 — 2026-08-28 — closes gap G8 from `00-INDEX §12.1`*
