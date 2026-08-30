# Fork-Connection Spec — Open Questions (Expanded)

**Date:** 2026-08-30
**Status:** DRAFT (awaiting user answers to unblock writing-plans)
**Companion to:** `docs/superpowers/specs/2026-08-30-fork-connection-architecture.md` §10
**Purpose:** Deep drill-down on each open question so the user can answer with full visibility into trade-offs, reversibility, and downstream impact.

Each question is structured the same way: Question → Options → Key trade-offs → Reversibility → Recommendation → If you pick the other option → What I need from you.

---

## Q1. In-repo vs external-repo for fork servers

### Question

Where do the downstream fork MCP servers (`solverforge_calendar.server`, `tuiboard.server`) live in the source tree?

### Context

`taskdog` is the only fork connected today. It follows a **hybrid pattern**: factory in this repo (`src/ikigai/src/ikigai/gateway/clients/taskdog.py`) + subprocess binary in external repo (`/mnt/c/.../apps/dev-tools/taskdog`). New forks can mirror this OR choose differently. Affects CI reliability, onboarding, version coupling, code locality.

### Options

**α — Both external (mirror taskdog).** Each fork in its own repo. CI must skip-if-missing. 3 repos to clone.
**β — Both in-repo.** `src/solverforge_calendar/` + `src/tuiboard/`. Single clone; matches "fully local" invariant.
**γ — Mixed (solverforge in-repo, tuiboard external).** Asymmetric; pick per fork.
**δ — git submodule.** Single clone with submodule init; known Git complexity pain.

### Key trade-offs

| Dim | α | β | γ | δ |
|---|---|---|---|---|
| CI reliability | LOW | HIGH | LOW | MED |
| Clone-and-run | 3 repos | 1 repo | 3 repos | 1 (+ init) |
| Matches taskdog | YES | NO | partial | NO |
| Project's "fully local" | WEAK | STRONG | WEAK | MED |

### Reversibility

- **α → β** is HARD (re-import modules back); **β → α** is MEDIUM; **γ → β** is EASY (just `git mv`); **δ → anything** is HARD.
- **β is the most reversible choice** — doesn't lock in multi-repo.

### Recommendation

**β — both in-repo.** Matches project's "fully local" + "SQLite + filesystem only" invariants. CI always runs. New contributors `git clone && uv sync && pytest`.

### If you pick α instead

Add `tests/gateway/clients/conftest.py` skip-if-missing fixtures + CI matrix with 3 of 4 builds OK + onboarding docs at `docs/onboarding/fork-setup.md`. Recurring operational cost.

### What I need

> "In-repo (β) or external (α)?"

---

## Q2. FastMCP or hand-rolled JSON-RPC for fork servers

### Question

Should each fork's MCP server use the FastMCP framework (matching `src/ikigai/src/mcp_server/server.py`) or hand-roll a stdlib-only JSON-RPC 2.0 loop?

### Context

Two valid idioms:
- **FastMCP** — `@server.tool("name")` decorators; capability negotiation built-in; mcp SDK as dep
- **Hand-rolled** — read stdin, parse `Content-Length:` header, dispatch, write JSON-RPC response, drain stderr; ~150 LOC stdlib

Layer 1 uses FastMCP. Layer 2a forks are downstream subprocesses spawned by `StdioAdapter`, which already implements JSON-RPC framing on the gateway side. The fork just needs to **speak JSON-RPC 2.0 over Content-Length-framed stdio**.

### Options

**i — Hand-rolled JSON-RPC (recommended).** Zero deps; matches what `StdioAdapter` already expects.
**ii — FastMCP (matches Layer 1).** Reuse `mcp` SDK; auto schema from Pydantic.
**iii — Hybrid.** Not real (FastMCP owns its transport).

### Key trade-offs

| Dim | i hand-rolled | ii FastMCP |
|---|---|---|
| New deps per fork | 0 | ~30 transitive |
| LOC per server | ~150 | ~80 |
| Schema parsing | manual | auto |
| Cold-start latency | ~50ms | ~250ms |
| Matches `StdioAdapter` framing | YES | YES |
| Matches Layer 1 idiom | NO | YES |

### Reversibility

- **i → ii** is MEDIUM; **ii → i** is HARD (lose SDK abstractions).

### Recommendation

**i — hand-rolled.** Forks are SMALL (≤3 tools each); SDK's biggest win is reducing boilerplate on large surfaces. `StdioAdapter` already speaks JSON-RPC. Zero-dep forks = easier CI. Transport framing reusable via `src/ikigai/src/ikigai/gateway/stdio_server_base.py`.

### If you pick ii instead

Add `mcp[cli]>=1.0` to each fork's `pyproject.toml` + create `fastmcp_subprocess_runner.py` wrapping SDK for StdioAdapter compatibility + update CI fixtures.

### What I need

> "Hand-rolled (i) or FastMCP (ii)?"

---

## Q3. Auth model for the gateway

### Question

How do we authenticate callers of `UnifiedMCPGateway`?

### Context

`UnifiedMCPGateway` listens on `127.0.0.1:8765`. Today no auth — any local process can call. Threat model today: scripts-as-user accidentally calling. Threat model future: malicious tool injected into Claude Code's MCP config.

### Options

**a — No auth (current taskdog pattern).** Localhost-only; any local process. Matches existing.
**b — Shared secret in env var.** `IKIGAI_GATEWAY_SECRET`; `Authorization: Bearer` header. Blocks accidental.
**c — Per-fork capability token.** Gateway generates at register time; forks receive via env. Smallest blast radius.
**d — Unix socket + filesystem ACL.** Kernel-enforced; weak Windows support.

### Key trade-offs

| Dim | a | b | c | d |
|---|---|---|---|---|
| Implementation LOC | 0 | ~50 | ~200 | ~100 |
| Blocks accidental | NO | YES | YES | YES |
| Blocks malicious tool | NO | partial | YES | YES |
| Cross-platform | YES | YES | YES | weak on Win |
| Matches existing | YES | NO | NO | NO |

### Reversibility

- **a → b/c/d** is EASY; **b → c** is MEDIUM; **any → a** is EASY.

### Recommendation

**a — no auth for v1.** Gateway only listens on `127.0.0.1`; network isolation is in place. `data/` is on user's filesystem; an attacker who can call the gateway can already read the data. YAGNI: add auth on concrete threat, not preemptively. Document the assumption in the spec.

### If you pick b instead

Add `IKIGAI_GATEWAY_SECRET` to `start_gateway.py` + `Authorization` header check in `gateway.py:make_handler` + onboarding doc with `secrets.token_urlsafe(32)` command.

### What I need

> "None (a), shared secret (b), or per-fork (c)?"

---

## Q4. Event log destination

### Question

Where do SSE events emitted by `UnifiedMCPGateway.emit_adapter_call()` get persisted?

### Context

`gateway.py:108` `publish_event()` writes to `EventLog`. Today default is `data/gateway/events.jsonl`. Three concrete alternatives.

### Options

**i — Single `data/gateway/events.jsonl` (current).** One append-only file. Matches append-only invariant.
**ii — Per-namespace files.** `data/gateway/<fork>_events.jsonl`. Filter without grep; bounded file size.
**iii — SQLite with structured columns.** Queryable; indexable; non-append-only.

### Key trade-offs

| Dim | i single JSONL | ii per-namespace | iii SQLite |
|---|---|---|---|
| Implementation LOC | 0 | ~30 | ~150 |
| Query simplicity | grep | grep + cat | SQL |
| Bounded growth | NO | NO | YES |
| Append-only invariant | YES | YES | NO (UPDATE) |
| Cross-fork analytics | hard | medium | easy |

### Reversibility

- **i → ii** is EASY; **ii → iii** is HARD (replay JSONL → SQLite; duplicate data); **iii → i** is MEDIUM.

### Recommendation

**i — single JSONL.** Volume bounded: ~100 events/day × 1KB = 36MB/year. Not a real problem. Append-only invariant is sacred. Grep + awk sufficient.

### If you pick iii instead

Use `sqlite3` stdlib. Schema: `events(id INTEGER PK, ts TEXT, namespace TEXT, tool TEXT, args TEXT, result TEXT, duration_ms INTEGER, error TEXT)`. Index on `(namespace, ts)`. Per `verify-agent-fabricated-failures` memory: do NOT switch formats during testing without clearing both stores first.

### What I need

> "Single JSONL (i), per-namespace (ii), or SQLite (iii)?"

---

## Q5. Tool surface evolution strategy

### Question

How do we version tool names when the underlying schema or semantics change?

### Context

Today's tool names are pinned in factory docstrings. When evolution arrives (e.g., `sf_schedule` needs RRULE support), what convention?

### Options

**α — Suffix-version (`sf_schedule_v2`).** New alongside old; deprecate after migration.
**β — Major version prefix (`sf2_schedule`).** Bump at namespace level.
**γ — YAGNI (recommended).** Decide when concrete pain arrives.
**δ — Discriminated union per tool.** `version` param in input; complex schemas.

### Key trade-offs

| Dim | α suffix | β major prefix | γ YAGNI | δ discriminated |
|---|---|---|---|---|
| Migration clarity | high | high | NONE | medium |
| Schema evolution | slow | hard | undecided | incremental |
| Caller complexity | medium | medium | low | high |

### Reversibility

- **γ → α/β** is EASY; **α → β** is HARD; **β → α** is EASY; **δ → α** is HARD.

### Recommendation

**γ — YAGNI until users complain.** v1 surface is the whole scope; we haven't seen evolution yet. When real pressure arrives, pick convention with concrete data.

### If you pick α instead

Document convention in `src/ikigai/src/ikigai/gateway/clients/CONTRACT.md` + 90-day deprecation policy + bump tool surface version in `data/gateway/contract.json`.

### What I need

> "YAGNI (γ) or explicit convention (α/β)?"

---

## Q6. Conformance to `vault_write` as only vault writer

### Question

Do the new fork MCP servers honor the Layer 1 `vault_write` constraint, and how is this enforced?

### Context

Per [[algorithm-attribution-decisions-2026-08-29]] §7, `vault_write` is the ONLY writer to `vault/`. Forks must call `vault_write` MCP from Layer 1; never touch `vault/` directly. Concretely: `sf_schedule` does NOT create vault notes. `tuiboard_snapshot` does NOT write markdown.

### Options

**I — Document-only.** Add to each fork's README: "Do not write to `vault/`. Use Layer 1 `vault_write` MCP tool." Zero code.
**II — Filesystem ACL.** Forks as `nobody`; `vault/` owned by user with `chmod 600`. Kernel-enforced.
**III — Pre-commit / CI grep check.** `grep -r "vault/" src/<fork>` returns 0. Catches imports only.
**IV — Wrapping envelope at call sites.** Tools return `PendingVaultWrite`; gateway forwards to `vault_write`. Cannot be bypassed.

### Key trade-offs

| Dim | I docs | II ACL | III grep | IV envelope |
|---|---|---|---|---|
| Enforcement strength | NONE | strong | medium | strong |
| Implementation cost | 0 | high | low | medium |
| Dev discipline required | HIGH | NONE | low | NONE |

### Reversibility

- **I → III** is EASY; **III → IV** is MEDIUM; **IV → I** is EASY.

### Recommendation

**I + III combined — docs as canonical statement, grep test as safety net.** Constraint already documented in attribution §7. Adding `tests/gateway/clients/test_vault_write_conformance.py` catches regressions cheaply. Runtime enforcement is overkill for personal OS.

### If you pick IV instead

Add `PendingVaultWrite` Pydantic model to `src/contracts/common.py` (tagged-union variant of `VaultWriteInput`) + update fork tool outputs + gateway routing for `PendingVaultWrite`.

### What I need

> "Docs + grep test (I+III), filesystem ACL (II), or wrapping envelope (IV)?"

---

## Summary: how to answer

You can answer all six in a single message or one at a time. Format I can act on:

```
Q1: <letter>
Q2: <letter>
Q3: <letter>
Q4: <letter>
Q5: <letter>
Q6: <letter>
```

Or in natural language — I'll match each answer to the corresponding option. If you want to **defer** one (e.g., "decide later when needed"), say so and I'll mark it DEFERRED in the main spec.

Once all six are answered (or explicitly deferred), I invoke `writing-plans` to produce the implementation plan.

---

## Appendix: minimum-viable spec posture (recommended defaults)

If you want to skip answering some questions and just unblock implementation:

| Q | Default | Action if you don't answer |
|---|---|---|
| Q1 | β in-repo | Revisit if a fork outgrows the tree |
| Q2 | i hand-rolled | Easier to migrate to ii than reverse |
| Q3 | a no auth | Localhost-only is sufficient |
| Q4 | i single JSONL | Volume bounded; matches invariant |
| Q5 | γ YAGNI | Pick when concrete pain arrives |
| Q6 | I+III docs + grep | Catches regressions cheaply |

**"all defaults" / "skip the questions"** → I lock in this table, update main spec with `[DEFERRED — defaults applied]` per question, invoke `writing-plans` immediately. Each task touching a deferred question includes a one-line note: "if [decision] later changes, this task may need a follow-up".

---

## Appendix: what happens if you don't answer

1. Lock in all defaults from appendix above
2. Update main spec deferral markers
3. Invoke `writing-plans` for implementation plan
4. Tasks touching deferred decisions include one-line "if this changes, follow-up" notes

This is reversible — when you revisit a decision, the plan's tasks show it, and a single-line edit reroutes the plan.
