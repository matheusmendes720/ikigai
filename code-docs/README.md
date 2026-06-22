# code-docs — Specifications Root

Unified index for all engineering specifications: ADRs, PRDs, BRDs, and ARDs.
Located at: https://github.com/matheusmendes720/ikigai/tree/master/code-docs

> All specs are **append-only** unless explicitly refactored. Do not delete or rewrite existing sessions, topics, or paragraphs.

---

## GitHub Infrastructure

| Resource | URL |
|----------|-----|
| Repository | https://github.com/matheusmendes720/ikigai |
| Project Board (Kanban + Roadmap) | https://github.com/users/matheusmendes720/projects/4 |
| Issues | https://github.com/matheusmendes720/ikigai/issues |
| Wiki | https://github.com/matheusmendes720/ikigai/wiki |

---

## ADRs — Architecture Decision Records

| Path | Subject |
|------|---------|
| `code-docs/adr/OPERATIONAL/` | PAV kernel decisions (habit engine, policy FSM, pomodoro SM) |
| `code-docs/adr/VIBE-OPS/` | Cybernetic engine decisions (data flow, RAG, mesh topology) |

**See also:**
- `vibe-ops/architecture/` — live ADRs
- `life-ops/operational/docs/adr/` — live operational ADRs

## PRDs — Product Requirements Documents

| Path | Subject |
|------|---------|
| `code-docs/prd/OPERATIONAL/` | PAV kernel product requirements |
| `code-docs/prd/VIBE-OPS/` | Cybernetic engine product requirements |

**See also:**
- `vibe-ops/planning/` — live PRDs

## BRDs — Business Requirements Documents

| Path | Subject |
|------|---------|
| `code-docs/brd/CLUSTER_PLAN.md` | Cluster 1 (Plan) business requirements |

**See also:**
- `vibe-ops/planning/CLUSTER_PLAN_BRD.md` — live BRD

## ARDs — Architecture Requirements Documents

| Path | Subject |
|------|---------|
| `code-docs/ard/` | Architectural framing and system design |

---

## Navigation

```
code-docs/
├── adr/          ← Architecture Decision Records
├── prd/          ← Product Requirements Documents
├── brd/          ← Business Requirements Documents
├── ard/          ← Architecture Requirements Documents
└── README.md     ← This file
```
