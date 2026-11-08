# ADRs — the decisions the contracts rest on

Architecture Decision Records for the Algorithmic Life OS. Each ADR captures a
single architectural decision: Status, Date, Context, Decision, Consequences,
Alternatives, Implementation Rules. Append-only — ADRs are immutable once
Accepted; superseded ADRs are linked, never edited.

> **This index lists five.** The repository publishes the decisions the
> current scope rests on, and nothing else: the ADRs of an architecture that
> was replaced describe a system that is not published, and a reader has no
> way to tell that from a description of the one that is.
>
> The rest are not deleted. They stay on the owner's disk and in the git
> history (ADR-037 §"publicação independente"), and the drift net names
> them — so if one comes back, the branch says so.

---

## ADR Index

| File | Status | Date | Subject |
|------|:------:|------|---------|
| `ADR-011-ikigai-mcp-http-sse-transport.md` | Accepted | 2026-08-27 | HTTP+SSE transport for the MCP server — the transport `src/transport/` implements, and the one the clients speak |
| `ADR-013-canonical-scope-discipline.md` | Accepted | 2026-08-31 | Canonical scope discipline — what the agent layer may and may not touch; the rule the drift net enforces |
| `ADR-014-ueid-canonical-format.md` | Accepted | 2026-09-04 | UEID canonical format = 4-part — the identity `src/contracts/common.py` defines |
| `ADR-033-ueid-single-source-mandate.md` | Accepted | 2026-09-21 | The UEID pattern has exactly one source — `src/contracts/common.py` |
| `ADR-037-data-layer-canonical-turn.md` | Accepted | 2026-11-01 | **Virada canônica: camada de dados primeiro** — unified DOM + Postgres store + services/MCP transport; the harness `pi` reused; Telegram as client; the algorithms deferred |
| `ADR-039-websocket-sync-transport.md` | Accepted | 2026-11-08 | **O canal websocket e a camada de recuperação que o alimenta** — o vetor escrito com o artefacto, o store a anunciar as suas mudanças, um canal bidireccional ao lado do MCP |

---

## Status Legend

| Status | Meaning |
|--------|---------|
| **Accepted** / **Aceita** | Decision is final and binding. No edits — supersede, don't rewrite. |
| **Proposta** / **Proposed** | Awaiting user decision. Can be edited freely. |
| **Superseded** | Replaced by a newer ADR. Link to replacement; never edited. |
| **Rejected** | Decision was considered and rejected. Link to rationale; never edited. |

---

## Cross-References

| Topic | Canonical source |
|-------|------------------|
| The transport the clients speak | `ADR-011-ikigai-mcp-http-sse-transport.md` |
| What may and may not be touched | `ADR-013-canonical-scope-discipline.md` |
| The identity, and its single source | `ADR-014-ueid-canonical-format.md` · `ADR-033-ueid-single-source-mandate.md` |
| **Data-layer canonical turn (2026-11-01)** | `ADR-037-data-layer-canonical-turn.md` — DOM + store + services/MCP |
| The websocket sync channel and the retrieval layer | `ADR-039-websocket-sync-transport.md` — the vector written with the artifact, the store announcing its changes |
| The series that specified the pivot | [`docs/superpowers/specs/2026-11-01-00-data-layer-series.md`](../../docs/superpowers/specs/2026-11-01-00-data-layer-series.md) |
| The cut that preceded the pivot | [`docs/superpowers/specs/2026-10-30-05-cut.md`](../../docs/superpowers/specs/2026-10-30-05-cut.md) |

---

## Maintenance

When adding a new ADR:

1. **Append-only** — never edit an Accepted ADR. Supersede, don't rewrite.
2. **Filename convention** — `ADR-NNN-kebab-slug.md`.
3. **Numbering** — sequential: **ADR-038 is reserved** for the single-player-store decision (`specs/production-readiness/ROADMAP.md` O2), so the next free number is **ADR-040**. ADR-039 is the websocket sync channel.
4. **Cross-reference** — every ADR points to canonical source (file + line range or section).
5. **Update this README** — add the row to the index table.
6. **Publish it deliberately.** The ignore rules exclude `code-docs/adr/*.md`
   and re-include each published ADR by name. A new ADR is not published
   until it is named in that list and in the guard's exceptions — a decision
   enters the published tree on purpose, not by accident.

---

*ADR index — reduced to the decisions the contracts rest on, 2026-11-05.*
