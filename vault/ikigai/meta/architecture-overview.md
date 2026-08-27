# IKIGAi Architecture Overview (DATA-FIRST perspective)

> **Audience:** Future engineering agents picking up this codebase cold.
> **Scope:** Sub-atomic-level map of the 3-subsystem topology, with the gap between
> "code that exists" and "code that observes the human's reality" surfaced up front.
> **Source of truth:** This file is a *handoff doc*; cross-check against
> `README.md`, `CLAUDE.md`, and `vibe-ops/architecture/ADR-*.md` for canonical claims.

---

# 1. The 3 subsystems

The repo is three subsystems welded together by a thin root CLI. They share a
filesystem but not a process, and they only talk to each other through well-defined
boundary contracts.

## 1.1 `life/` (root CLI hub)

- **Role:** Typer-based orchestrator. Mounts *centrals* (task, knowledge, research) and
  *handlers* (daily, weekly). Plugins attach via `PluginProtocol`.
- **Language:** Python 3.12+, Typer + Rich + structured logging.
- **How it talks to others:** **Subprocess.** Every cross-subsystem call goes through
  `BaseCentral.run_cli(cwd, module, args, json_out)` which shells out, parses JSON, and
  returns `{ok, stdout, stderr, data, error?}`. Handlers double as integration tests by
  design — running `python -m life.cli daily run` exercises every reachable central.
- **Key file:** `life/cli/cli.py` — the Typer app root.

## 1.2 `vibe-ops/` (cybernetic engine)

- **Role:** The Target → Sensor → Adjuster → Persist → Sync → Index loop. Bridges
  Obsidian vault ↔ SQLite ↔ Taskwarrior. Owns the 17 Pydantic entities that mirror
  the user's planning artifacts.
- **Language:** Python (cybernetic engine, SQLite bridge, Typer+Rich CLI) +
  Rust (the `vibeops-tui/` ratatui binary that polls `vibe_ops.db`).
- **How it talks to others:**
  - **In-process:** `SyncEngine` (middleware) is the *only* module touching all three
    backends simultaneously. UEIDs (`<CLUSTER>:<ENTITY>:<ID>`, e.g. `study:topic:st_python_01`)
    are content-addressed (`upstream_id` SHA-256) so every sync is idempotent.
  - **To PAV kernel:** through the `pav sync` subprocess bridge — `operational` stays
    *standalone* and never imports from `vibe-ops/`.
- **Key files:** `vibe-ops/src/middleware/sync_engine.py`, `vibe-ops/src/cybernetics/daily_loop.py`,
  `vibe-ops/architecture/ADR-001-data-flow-topology.md`.

## 1.3 `life-ops/operational/` (PAV kernel)

- **Role:** The Produtividade Algorítmica Visual (PAV) productivity kernel. Pure
  arithmetic — *zero LLM*, *zero NLP*. Owns the 14 persistent entities, the
  `Habit`/`Policy`/`Pomodoro` state machines, the Q_HE composite score, and the
  two user-facing surfaces (CLI + TUI).
- **Structure:** uv workspace, three packages:
  - `packages/core/` — Layer 1: pure logic, zero I/O. Habit engine, policy engine,
    pomodoro state machine, parsers, persistence Protocol.
  - `apps/cli/` — Layer 3: thin Typer controllers (12 sub-typers). `state.py` holds
    14 `_PersistentRepo` instances backed by JSON flat files in `~/.time-tasker/`.
  - `apps/tui/` — Textual TUI (7 screens + Help modal). `PAVApp.SCREENS` dict + `BINDINGS`.
- **Standalone rule:** Hard invariant from `CLAUDE.md §Global Conventions`.
  **No imports from root `life/` or `vibe-ops/`.** Integration is one-way, via
  subprocess. A `pav sync vault|code|all|status|conflicts` subcommand bridges to
  `vibe-ops/src/scripts/vault_sync.py`.

```
                          ┌────────────────────────────────────────┐
                          │  life/  (Typer orchestrator)           │
                          │  daily / weekly handlers               │
                          │  centrals: task · knowledge · research │
                          └────────────┬───────────────────────────┘
                                       │ subprocess (--json)
                  ┌────────────────────┼─────────────────────────────┐
                  ▼                    ▼                             ▼
        ┌─────────────────┐   ┌────────────────────┐   ┌──────────────────┐
        │ life-ops/       │   │ life-ops/          │   │ vibe-ops/        │
        │ operational/    │   │ life_tatics/       │   │                  │
        │ ★ ACTIVE DEV    │   │ (stable, Poetry)   │   │ (stable, uv)     │
        │ PAV kernel      │   │                    │   │ cybernetic loop  │
        │ standalone      │   │                    │   │ Obs↔SQLite↔TW    │
        └─────────────────┘   └────────────────────┘   └──────────────────┘
```

---

# 2. Data flow today

The DATA-FIRST question — *where does a human-written markdown file actually
go, and what observes it?* — exposes the current loop's weak points.

## 2.1 The intended loop

1. Human opens a markdown template in the Obsidian vault.
2. Human fills in the template (frontmatter + body).
3. **Some agent** ingests the change, computes derived fields, mirrors to SQLite.
4. The PAV kernel reads from SQLite, surfaces the data on a TUI screen.
5. Next period, the loop closes (yesterday's plan ↔ today's log ↔ tomorrow's verdict).

## 2.2 Where the loop breaks today

| Stage | Today | Gap |
|-------|-------|-----|
| **Human edit** | User edits `vault/.../0_daily/journal.md` manually | **No watcher.** Nothing polls the filesystem. The edit sits there until the user runs a command. |
| **Ingestion** | `vibe-ops/src/middleware/bidirectional_sync.py::sync_vault_to_code()` reads manual fields | **One-shot, not continuous.** User must run `pav sync vault` (or `python -m vibe_ops sync_file`) explicitly. |
| **Computed-field writeback** | `sync_code_to_vault()` writes computed fields (RICE, verdict scores) back to `.md` | **Manual fields win, computed fields write back** (D3 from `vault-bidirectional-sync`). The user cannot see derived state without re-syncing. |
| **Daily ↔ daily continuity** | Each daily report stands alone | **No verifier checks that today's log matches yesterday's plan.** No automatic `plan → act → verify` cycle. |
| **Surface** | PAV TUI (7 screens) shows JSON state from `~/.time-tasker/` | **The 9 markdown templates never appear on any TUI screen.** TUI and markdown live in parallel universes. |
| **5-vector scoring** | `IKIGAiVectorEntity` is defined in `life-ops/ikigai/src/` | **Not wired into the human-facing surface.** No TUI widget, no `pav ikigai status` command, no daily deltas surfaced. |

The single sentence: **the user can write markdown all day and the system will not
notice until they run an explicit sync command.**

---

# 3. The "stand-alone header" proposal

The architectural fix to the loop break in §2 is a single, tiny package:
**a Python `Protocol` defining what a "header backend" can do, plus 4 adapter
implementations.** The 9 markdown templates become backend-agnostic; the user can
migrate from filesystem → Obsidian → SQLite without changing the templates or the
agents that read them.

## 3.1 The Protocol surface

```python
class HeaderBackend(Protocol):
    def read_entity(self, ueid: str) -> Entity: ...
    def write_entity(self, ueid: str, entity: Entity) -> None: ...
    def list_entities(self, period: Period | None = None) -> list[Entity]: ...
```

Zero logic in the package. Just shape.

## 3.2 Backend adapters

| Backend | Backing store | When to use |
|---------|---------------|-------------|
| `MarkdownBackend` | Plain `.md` files with YAML frontmatter | Default. File-based, git-friendly, human-readable. |
| `SQLiteBackend` | `vibe_ops.db` (the WAL-mode SQLite the engine already uses) | When the user wants structured queries + indexes + sqlite-vec vector search. |
| `ObsidianBackend` | The user's live Obsidian vault (Dataview-aware) | When the user wants Dataview Bases + Live Previews + plugin integration. |
| `InMemoryBackend` | `dict[str, Entity]` | Tests only. The four property-test suites pin behaviour against this. |

## 3.3 Why this matters

- **Decouples the 9 templates** from any one storage so the user can migrate
  without rewriting template bodies.
- **Lets agents be storage-agnostic.** A `PAE-Maintainer` node can call
  `backend.read_entity(ueid)` whether the entity lives on disk, in SQLite, or
  in Obsidian.
- **Lets tests run fast.** The `InMemoryBackend` keeps the 143-test PAE suite
  sub-second.

---

# 4. The PAE-Maintainer agent

The PAE-Maintainer (Planejamento ↔ Avaliação ↔ Execução) is the agent that closes
the planning loop. Built as a custom Python graph (NOT the langgraph SDK — see
`.omo/drafts/agentic-markdown-system-completion.md` §"Architectural Decisions Captured").

## 4.1 Topology — 5 nodes × 2 channels

```
        ┌──────────┐         ┌──────────┐
        │PROSPECTIVE│         │RETROSPECTIVE│
        │ channel   │         │  channel    │
        │(forward)  │         │ (backward)  │
        └─────┬─────┘         └──────┬─────┘
              │                      │
              ▼                      ▼
       ┌──────────┐           ┌──────────┐
       │ observe  │           │ observe  │
       └─────┬────┘           └─────┬────┘
             │                      │
             ▼                      ▼
       ┌──────────┐           ┌──────────┐
       │   plan   │           │ reflect  │
       └─────┬────┘           └─────┬────┘
             │                      │
             └──────────┬───────────┘
                        ▼
                 ┌──────────┐
                 │ balance  │   (joins both channels, computes Q_HE + 5×3×3)
                 └─────┬────┘
                       ▼
                 ┌──────────┐
                 │  commit  │   (guarded; only writes if vault_hash changed)
                 └──────────┘
```

- **Prospective channel:** observe → plan → (join at balance)
- **Retrospective channel:** observe → reflect → (join at balance)
- **Join:** balance reads from both channels' shared `BalancerState`
- **Guarded commit:** writes only fire when the entity's `vault_hash` differs
  from the last sync — this is the idempotency guarantee.

## 4.2 Wired CLI

```
pav plan run      --cycle-id 2026-Q3
pav plan status   --cycle-id 2026-Q3
pav plan balance  --cycle-id 2026-Q3
pav plan daemon   --cycle-id 2026-Q3     # cron-style, every 5min
```

## 4.3 Quality state

- **143 tests pass**, 96% coverage on the PAE-Maintainer module
- mypy --strict clean, ruff clean
- 0 LLM imports in the hot path (pure arithmetic: Q_HE + 5×3×3 + hysteresis)

---

# 5. The 9 templates (period coverage)

The period pyramid — 5 levels, 9 templates, all PT-BR body / EN keys per ADR-006.

| # | Filename | Period | Frontmatter extras | Verdict formula |
|---|----------|--------|--------------------|-----------------|
| 0 | `00-quartely-planning.md` | Quarterly (Sonho) | `sonho_id`, `parent_period=null` | 8-phase + 5×3×3 + Teste de Fogo |
| 1 | `01-sonho.md` | Long-horizon anchor | `ikigai_score_inicio`, `ikigai_score_fim` | IKIGAi 5-vector composite |
| 2 | `02-avaliacao-trimestral.md` | Quarterly review | `parent_period=01-sonho` | 5×3×3 delta + regime shift |
| 3 | `03-onda.md` | Sprint (2-week wave) | `parent_period=02-avaliacao` | Wave KPI + Q_HE |
| 4 | `04-revisao-semanal.md` | Weekly | `parent_period=03-onda` | Start/Stop/Continue |
| 5 | `05-relatorio-diario.md` | Daily | `parent_period=04-revisao-semanal` | Plan vs Act delta |
| 6 | `06-quartely-review.md` | Quarterly close | `parent_period=01-sonho` | Teste de Fogo matrix + IKIGAi delta |
| 7 | `07-sprint-kickoff.md` | Sprint start | `parent_period=03-onda` | Capacity + cognitive debt |
| 8 | `08-sprint-retrospective.md` | Sprint end | `parent_period=07-sprint-kickoff` | Start/Stop/Continue + KAIZEN |

Verdict enums vary per period. The daily report uses `PASS|PARTIAL|FAIL`; the
quarterly review uses `CONTINUE_WAVE|CORRECT_TRAJECTORY|KILL_WAVE`; the long-horizon
sonho uses `ACTIVE|VALIDATED|FALSIFIED|PIVOTED|ABANDONED`.

---

# 6. Frontmatter contract (ADR-006)

Every template has the same skeleton. Required fields:

| Field | Type | Meaning |
|-------|------|---------|
| `type` | enum | `period_report` (the only valid value for templates) |
| `entity_type` | enum | One of `dream|goal|objective|project|task|deliverable|routine|timeblock|ritual|pomodoro|vector|profile|skill|opportunity|override` |
| `period` | enum | One of `sonho|trimestral|onda|semanal|diario` |
| `id` | str | The local slug (used in filename + cross-references) |
| `template_role` | enum | Where in the period pyramid this file sits |
| `template_version` | str | SemVer of the template body, bumped on body edits |
| `ikigai_cluster` | enum | `PLAN|PROJECT|STUDY` (matches the three cluster docs) |
| `date_start` | date | ISO 8601 |
| `date_end` | date | ISO 8601 |
| `verdict` | enum | Period-specific (see §5) |
| `verdict_score` | float | 0.0–1.0, drives the verdict (≥0.70 PASS, 0.50–0.70 PARTIAL, <0.50 FAIL) |
| `sonho_id` | str\|null | Always back-references the root Dream; `null` only on the Sonho itself |
| `parent_period` | str\|null | Filename of the parent template; `null` for the Sonho |
| `ikigai_vector` | enum | `passion|skill|market|revenue|course` — the dominant vector this period advanced |
| `ikigai_score_inicio` | float | 0.0–1.0, opening composite of all 5 vectors |
| `ikigai_score_fim` | float | 0.0–1.0, closing composite |
| `vault_path` | str | Absolute path in the Obsidian vault (idempotency anchor) |
| `vault_hash` | str | `sha256:16` of the last-synced body — `sync_code_to_vault` is a no-op when this matches |
| `status` | enum | `draft|active|closed` |
| `tags` | str\|list | Free-form; queried by the Dataview Bases |

The contract is enforced by `vibe-ops/src/pipeline/frontmatter_parser.py` (24 entity
types in `MODEL_MAP`).

---

# 7. Where the gap is today (loop breaks)

These are the gaps between *what the system can do* and *what the human's data triggers*:

1. **No auto-ingestion of manual markdown edits.** The bidirectional sync is explicit
   (`pav sync vault`); no filesystem watcher runs by default.
2. **No auto-writeback of computed fields to vault.** Computed fields only land in
   `.md` when the user invokes `sync_code_to_vault`. No cron, no daemon.
3. **No verification that today's daily log matches yesterday's plan.** The
   `plan → act → verify` cycle is *defined* but *not run*. There's no `pav verify daily`.
4. **Operational kernel TUI (9 screens) doesn't surface the markdown plans at all.**
   `apps/tui/src/operational/tui/screens/` shows PAV-native state (routines, habits,
   metrics). The 9 templates from §5 are invisible there.
5. **The 5-vector IKIGAi scoring is not wired into the human-facing surface.** The
   math exists in `life-ops/planner/ikigai_planning/` and `life-ops/ikigai/src/`,
   but no TUI widget, no CLI command, no daily digest surfaces it.
6. **The 4 reporting period templates (`04-revisao-semanal`, `06-quartely-review`,
   `08-sprint-retrospective`) are write-only** — nothing reads them, nothing aggregates
   their verdicts, no roll-up view exists.
7. **The Plan / Project / Study cluster docs are cross-referenced in
   `CLUSTER_PLAN.md` etc. but not enforced.** Nothing rejects a plan that doesn't
   reference a Study, or a Study that doesn't serve a Plan.

---

# 8. What data-first methodology demands of each subsystem

Each subsystem's role under DATA-FIRST — *observe the human's reality before
adding features that won't fire*:

## 8.1 `life-ops/operational/` (PAV kernel)

- **Hide features that aren't observed in 5+ manual logs.** If a screen isn't
  clicked 5 times across the user's logs, it should not be on the menu.
- **The TUI's 7 screens should be ordered by frequency-of-use in actual
  `~/.time-tasker/` writes**, not by spec author preference.
- **JSON output (`--json`) is the test contract.** Every screen renders should be
  reproducible from a `--json` flag, otherwise the visual test cannot run.

## 8.2 `vibe-ops/` (cybernetic engine)

- **Only enable vault sync after the user has 10+ manually-written plans.** Until
  then, sync is a no-op (or refuses with a clear "you don't have enough manual
  data to make sync useful" message). Premature sync creates false confidence.
- **Sync is idempotent; the engine should never corrupt a vault.** Idempotency
  is already in (`vault_hash` SHA-256) — the v1.1 `life sync watch` daemon must
  preserve it.
- **Computed fields write back only to templates, never to freeform prose.** The
  body of a journal entry is human territory.

## 8.3 `life/` (root CLI hub)

- **Add a `pav plan` command that just opens the right template file in the
  editor.** No logic. No arithmetic. Just: `pav plan open --period daily` →
  spawns `$EDITOR` on the daily template, pre-filled with today's date and the
  current Sonho's `sonho_id`. Lower the activation energy to zero.
- **Handlers (`daily`, `weekly`) must become verifier-and-prompter roles**, not
  runners. They should read the user's last 7 daily logs and *ask* "yesterday's
  plan said X, today you logged Y. Verdict?" — not run any algorithm.

---

# 9. Open architectural decisions

From `.omo/drafts/ikigai-as-dom-on-planning-engine.md §8`:

| # | Decision | Status |
|---|----------|--------|
| **D1** | Should `_plan.md` live in vault (Obsidian) or in code (`life-ops/ikigai/data/`)? | Open — affects git-history visibility and Dataview reach. |
| **D2** | Are existing IKIGAi tests (250+) converted to `_plan.md` format in this PR, or follow-up? | Open — affects test-PR scope and review burden. |
| **D3** | How are daily snapshots aggregated — one file per day, or one file per cycle? | Open — affects file count and grep-ability. |
| **D4** | Does planning-with-files need to learn IKIGAi custom frontmatter (`entity_type=IKIGAiDream` etc.) or do we re-purpose existing type values? | Open — affects engine upgrade surface. |

**Note:** D5 (swarm topology) was already locked in the agentic-markdown-system
plan — hybrid (single Atlas + specialists on triggers).

---

# 10. Where engineering agents should start

A short, ordered checklist for any new agent picking up this surface:

1. **Read this file** — `.omo/ikigai/meta/architecture-overview.md` (you're here).
2. **Read the socratic interview** — `.omo/ikigai/meta/socratic-interview.md` —
   the human's stated motivation, the tensions, the regretted-work list.
3. **Read the meta-learning note** — `.omo/ikigai/meta/agents.md` — what prior
   agents tried, what worked, what to avoid.
4. **Read all 5 mock datasets** in `.omo/ikigai/mock-datasets/` — they encode the
   expected shape of the system's output for the 9 templates and the 5 vectors.
5. **Read 5+ manually-written templates** in `.omo/ikigai/closing-2026/` (when
   they exist) — these are the *ground truth* of what the human actually writes;
   if your feature doesn't make those templates easier or richer, it isn't
   justified.
6. **THEN propose changes grounded in observed patterns.** No feature invented
   in a vacuum. Every PR should cite ≥1 manual log or ≥1 mock dataset entry
   that motivates the change.

---

*Handoff doc — generated 2026-07-02. Update when any of the following changes:
the 9 template list, the frontmatter contract (ADR-006), the §7 gap list, or any
of the D1–D4 decisions.*