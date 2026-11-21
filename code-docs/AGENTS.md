# AGENTS.md — `code-docs/`

**Score 11 — distinct domain: the decision record.** Everything here is the
`adr/` tree: 14 published ADRs plus the index that publishes them. This is the
only place a decision and its rejected alternative are written down.

## OVERVIEW
`code-docs/adr/` holds Architecture Decision Records: one decision per file,
append-only, published on purpose. `adr/README.md` is the index, the status
legend and the maintenance rules.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| The decision the current scope rests on | `adr/ADR-037-data-layer-canonical-turn.md` | D1–D8; cited by nearly every other file |
| What the agent layer may not touch | `adr/ADR-013-canonical-scope-discipline.md` | enforced by the drift net |
| The identity and its single source | `adr/ADR-014-…` · `adr/ADR-033-…` | the UEID 4-part format |
| The transport the clients speak | `adr/ADR-011-…` | HTTP+SSE; the six MCP tools |
| The websocket channel and the retrieval layer | `adr/ADR-039-…` | the vector, the store's announcements |
| The write-back to the vault | `adr/ADR-043-…` · `adr/ADR-047-…` | 047 amends 043 instead of editing it |
| The panel inside the Telegram | `adr/ADR-044-…` | `proposed` |
| The public route and its gate | `adr/ADR-045-…` | the two gates, the funnel incidents |
| What a search carries | `adr/ADR-046-…` | the search answers "which", the read answers "what" |
| The rules for adding an ADR | `adr/README.md` | read it before writing one |

## CONVENTIONS
- **Filename `ADR-NNN-kebab-slug.md`, numbering sequential.** `ADR-038` is
  reserved for the single-player-store decision, so the next free number is
  `ADR-048`.
- **Two frontmatter styles coexist.** Bold markdown fields
  (`**Status:** Accepted`) in ADR-011/013/014/033/037/039/040/041/043; YAML
  frontmatter (`status: accepted`) in ADR-042/044/045/046/047. Match the
  neighbouring file; do not convert one style into the other.
- **Two body shapes coexist.** The classic record (Status, Context, Decision,
  Consequences, Alternatives, Implementation Rules, Roll-back, Related, Notes)
  and the 13-section PT-BR template of ADR-040…047: Veredito · A pilha ·
  Justificativa · A ponte que já existe · O que está quebrado · Inventário ·
  Dia zero · Evolução · Passos com PASS falsificável · Fora de escopo ·
  Decisões com default · Camadas de falha · Referências.
- **The rejected alternative is part of the record**, with its reason written
  ("Não entra, e a razão fica escrita"). A decision without the alternative is
  not finished.
- **Cross-reference by file and section**, never from memory.

## ANTI-PATTERNS
- **Never edit an Accepted ADR.** Supersede it; a superseded claim is
  annotated, never deleted.
- **Never publish an ADR by accident.** `.gitignore` excludes
  `code-docs/adr/*.md` and re-includes each ADR by name — a new ADR stays
  unpublished until it is named in that list and in the guard's exceptions.
  A file dropped in `adr/` without that allowlist entry is invisible to git.
- **Never write the decision without the reason the alternative was refused.**
- **Never treat an ADR as an importable dependency.** It is a record; the code
  under `src/` is the contract.
- **Never revive the retired runtime** these ADRs name (`sys_ikigai/`,
  `src/mesh/`, `interfaces/`, `vibe-ops/`) — the drift net fails if it returns.

## KNOWN DRIFT (measured 2026-11-20)
- `ADR-044` and `ADR-045` are published but absent from the index table in
  `adr/README.md`.
- `ADR-011`'s own body says `**Status:** Proposta`; `adr/README.md` lists it
  as `Accepted`.
- `docs/README.md` still calls this directory "as cinco decisões"; 14 are
  published.
