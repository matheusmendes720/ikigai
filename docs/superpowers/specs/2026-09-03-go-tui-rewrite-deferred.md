# Go TUI Rewrite — DEFERRED Spec

> **Status:** DEFERRED 2026-09-03 — captured for future evaluation, no implementation work
> **Source:** `/btw` side question 2026-09-03 — "what if we do this full python server management in go!? with buble tea and glow to read vault file tree feat"
> **Verdict:** DEFER. Re-evaluate when trigger conditions below are met.

---

## Context

Current TUI implementation lives at `interfaces/tui/operator/`:
- **Python Textual app, ~250 LOC**
- **3 tabs:** Adapters / Backend / Queue
- **Polling-based refresh** (5s `set_interval`) — no filesystem subscription
- **No vault tree viewer** — vault reading happens via MCP `vault_read` + Typer CLI; TUI does not render `vault/`
- Shipped Phase 9 (commit `fe61dcc`); augment commit is uncommitted in working tree (Phase B halt)
- `interfaces/tui/README.md` carries SUPERSEDED trailer; no other TUI exists

The user asked: would a Go rewrite with **Bubble Tea** + **Glow** + **Cobra** be a better investment?

---

## Proposal (DEFERRED)

Replace the Python operator TUI with a Go binary that adds:
1. **Vault file tree viewer** — Glow renders `vault/**/*.md` natively
2. **Live filesystem subscription** — `fsnotify` push updates (vs current 5s poll)
3. **Single static binary** — no venv, cross-platform Win/Mac/Linux
4. **Better TUI UX** — Elm-style architecture (Bubble Tea) is best-in-class
5. **Cobra CLI surface** — mirrors existing `life v2 cycle|score|regime` commands

### Tech stack

- **Language:** Go 1.22+
- **TUI framework:** [Bubble Tea](https://github.com/charmbracelet/bubbletea) (Elm-architecture)
- **Markdown rendering:** [Glow](https://github.com/charmbracelet/glow) — handles vault file tree natively
- **CLI:** [Cobra](https://github.com/spf13/cobra) — sub-commands
- **Filesystem watcher:** `fsnotify`
- **IPC with Python backend:** HTTP/SSE → `UnifiedMCPGateway` (no Go deep-agent SDK)

---

## Pros

| # | Pro | Why it matters |
|---|-----|----------------|
| 1 | Native markdown rendering | Glow renders `vault/**/*.md` out of the box — solves the missing vault viewer gap |
| 2 | Push updates via fsnotify | Replaces 5s poll with event-driven updates |
| 3 | Single static binary | No Python venv, no dependency hell, true cross-platform distribution |
| 4 | Best-in-class TUI UX | Elm-architecture is well-tested; Charm tools are widely adopted |
| 5 | Faster cold start | Go binaries start in ms vs Python's ~1s import-time overhead |
| 6 | Cross-platform binaries | `go build` produces Win/Mac/Linux binaries in one shot |

## Cons

| # | Con | Why it matters |
|---|-----|----------------|
| 1 | Replaces 250 LOC of working Python | Existing operator TUI is functional; rewrite is risky |
| 2 | 2-language drift | Python harness + Go TUI = 2 build pipelines, 2 dep trees, 2 test suites |
| 3 | Vault writes still route through Python `vault_write` MCP | Go can't bypass the sole-writer invariant; must HTTP to gateway |
| 4 | No Go deep-agent SDK | TUI must HTTP/SSE to Python `UnifiedMCPGateway` for any agent interaction |
| 5 | New build pipeline | Go modules + cross-compile Win/Mac/Linux replaces simple `uv run` |
| 6 | All upstream-side work stays Python | Graph nodes, skill flows, vault_write invariant — Python forever |

---

## Verdict: **DEFER**

**Reasoning:**
- Single-user local system — no external distribution need; static binary advantage is theoretical
- CLI + skills already cover ~95% of daily use
- 2-language drift cost > Glow vault rendering benefit for a system nobody outside this machine uses
- Phase B halt (2026-09-03) showed the Python TUI work is already partial; finishing Python is cheaper than starting Go
- The vault tree viewer is the only feature that would clearly win with Go/Glow — but it isn't on the daily-driver path yet

---

## Trigger conditions for re-evaluation

Reopen this spec when **ANY** of the following become true:

1. **External user demo requirement** — someone outside this machine needs to install + run the system. Static binary wins.
2. **Vault tree viewer becomes daily-driver** — the user starts wanting to navigate `vault/` 5+ times per day. Glow's rendering is materially better than terminal CLI `ls + cat`.
3. **Cross-platform packaging pain** — `uv` install failures on Windows/Mac start costing real time. Binary distribution is the answer.
4. **Python TUI proves inadequate** — Textual's 5s polling causes user-visible lag or bugs that can't be fixed cheaply.

---

## Future implementation outline (when triggered)

If/when deferred → active:

1. **Spike (2h):** Go binary that reads `vault/` + renders one markdown file via Glow. Validates the stack.
2. **Foundation (1d):** Bubble Tea app with Cobra sub-commands; HTTP client to `UnifiedMCPGateway` for backend calls.
3. **Vault tree (1d):** fsnotify subscription + Glow render + tree navigation.
4. **Operator tabs (2d):** Port Adapters/Backend/Queue tabs from Textual to Bubble Tea.
5. **Cross-platform build (0.5d):** GitHub Actions matrix for Win/Mac/Linux binaries.
6. **Deprecate Python TUI (0.5d):** `interfaces/tui/operator/` → archive, README SUPERSEDED trailer.

**Total estimated:** ~7 days when triggered.

---

## Out of scope (forever)

- Replacing Python Deep Agent harness with Go (no Go deep-agent SDK + drift risk)
- Replacing `vault_write` invariant enforcement (Python is canonical per attribution §7)
- Replacing `IKIGAI_TOOLS` MCP server (15 tools, drift detector 5/5)
- Replacing data mesh (`src/mesh/`) — adapters stay Python

---

*Spec written 2026-09-03 per user request "spec only please.. its a work for next other day". Defer until trigger conditions met.*
