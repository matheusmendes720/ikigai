# AGENTS.md — `docs/`

**Score 9 — distinct domain: the wiki.** The canonical map of the system plus
the dated register of what preceded it. Six tracked files, plus this guide.

## OVERVIEW
`docs/README.md` is the wiki root; `docs/superpowers/specs/` holds the spec
series that specified the pivot.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| How the system works today | `README.md` §"O mapa canónico" | the canonical map, first |
| How the system got here | `README.md` §"O registo (datado, preservado)" | archive; describes an unpublished system |
| Where to start, per persona | `README.md` §"Entrada por persona" | implementing agent, auditor, human |
| The spec that produced the pivot | `superpowers/specs/2026-11-01-00-data-layer-series.md` | the series index |
| The DOM | `superpowers/specs/2026-11-01-01-unified-dom.md` | SPEC-01 |
| The store | `superpowers/specs/2026-11-01-02-cloud-store.md` | SPEC-02 |
| The services, the transport and the harness | `superpowers/specs/2026-11-01-03-service-transport-pi.md` | SPEC-03 |
| What the cut removed, and why | `superpowers/specs/2026-10-30-05-cut.md` | SPEC-05, the cut |

## CONVENTIONS
- **Two things live here, and they do not mix.** The canonical map comes first;
  the dated register comes after and describes a system that is not published.
  A decision that cites what it eliminated is history, not architecture.
- **PT-BR throughout this subtree.**
- **The spec format is fixed**: `Goal` · `Por que agora` · `Anti-padrão que
  este spec evita` · `Decisões` (D1…Dn) · `Files` · `Contrato` · `Steps`
  (Tasks) · `Done criteria — observável por uma pessoa` · `Fora de escopo` ·
  `Self-review`, footer `*Spec NN proposed <date>.*`.
- **The series order is mandatory**: 01 before 02 before 03, and no client
  before SPEC-03 is green.
- **Done criteria are observable by a person, and quantified** — search p95
  < 50 ms over 10k artifacts, < 100 ms at 14 days.
- **Files stay under 500 lines** (SPEC-01 splits `dom.py` from `dom_kinds.py`
  for exactly this reason).

## ANTI-PATTERNS
- **Never read the register as architecture.** The langgraph harness, the
  operator CLI, the fork mesh and the cybernetic engine are unpublished, not
  deleted; a document describing them is a record of what was.
- **Never cut by line count** (SPEC-05): each removal needs a verified
  dependency closure, on a branch, revertible.
- **Never treat the spec series as the current contract.** It is the record of
  the pivot (2026-11-01); the ADRs published after it (ADR-039…047) carry the
  later decisions.
- **Never read `docs/auto-performance-os/` as a live dependency.** It exists on
  this machine but is gitignored (`.gitignore:425`) and is not published.
