# W5.3 — Kill Switch Consumer UX (Design)

> **Status:** DESIGN (2026-09-05) — Wave 5 Scenario C follow-up.
> **Scope:** Consumer UX layer ONLY. Architecture (W5.1) and implementation
> (W5.1.1) are SHIPPED at `sys_ikigai/security/kill_switch.py` (per ADR-029 §S1-S5,
> R1-R12). W5.3 designs the operator-facing CLI subcommand + TUI tab that
> *consume* the kill switch state — **zero architectural change, zero
> schema change, zero constants change.**
> **Prereqs:** ADR-029 (Accepted 2026-09-04, commit `1f3cd66`); W5.1.1
> implementation (5 `algorithm_constants.json` keys at
> `src/ikigai/src/agents/v2/prompts/algorithm_constants.json`); drift
> invariant (e) retroactive ship.
> **Out of scope:** See §5 — auto-revert logic, algorithm tuning procedure
> itself, SONHO log integration (W5.6), meta-planner wiring (Plan D E-track).

---

## 1. Problem Statement

The kill switch architecture (ADR-029) is **load-bearing but invisible**.
During a tuning iteration the operator needs to answer four questions in
under 10 seconds:

1. **Is the kill switch currently active?** (Which mechanism? env / vault / data?)
2. **Did it fire recently, and why?** (`actor_mismatch` vs `rate_limit_exceeded`
   vs `manual_override` vs `vault_write_bypass`)
3. **What is the recovery path?** (Specific to the activating mechanism per
   `_recovery_path_for_reason` in `sys_ikigai/security/kill_switch.py:302-316`)
4. **Is my iteration being rate-limited?** (Per R10 — `KILL_SWITCH_RATE_LIMIT_PER_HOUR`)

Today the operator must `cat data/review_queue/*.json`, `tail -f
.vault_audit.log`, and `ls -lt vault/.kill_switch.md data/.kill_switch`
manually. This is **error-prone** during a tight tuning loop (ADR-030 §3
prescribes 5-min iteration cadence) and **bypasses the audit trail** when
the operator clears the kill switch via shell without writing to
`data/review_queue/`.

W5.3 designs the **single canonical consumer surface** — a CLI subcommand
(primary) and a TUI tab (secondary) — that wraps every kill switch
interaction in auditable, Pydantic-validated calls to the existing
`kill_switch.py` module.

---

## 2. UX Surfaces

### 2.1 Recommendation — One primary, one secondary

| Surface | Type | Role | Implementation |
|---------|------|------|----------------|
| **PRIMARY** | `life kill-switch` CLI subcommand | Scriptable, JSON-output, exits 0/1 | New Typer sub-app `interfaces/cli/kill_switch.py` registered in `interfaces/cli/read_tasks.py:app` |
| **SECONDARY** | `interfaces/tui/operator/` tab `[5]` | Live dashboard during long iterations | Add 5th tab "KillSwitch" to existing 4-tab Textual app (`interfaces/tui/operator/app.py`) |

**Why CLI primary:** ADR-029 S2.4 mandates the MCP resource
`ikigai://kill-switch/status` — already wired in W5.1.1. A Typer CLI that
mirrors that resource is the lowest-friction surface for the operator
(works in headless SSH sessions, pipes into `jq`, and can be called from
`make` recipes that compose with the existing v2 CLI hooks per W3.5 / W3.6).

**Why TUI secondary:** the operator TUI (`interfaces/tui/operator/`)
already exists with 4 tabs (Tasks / Adapters / Backend / Queue). Adding
a 5th tab is **structurally consistent** with Phase 9 Option A precedent
(memory `phase-9-shipped` — 4-tab operator TUI shipped 2026-09-03). The
operator already has the TUI open during tuning; the kill switch status
belongs alongside the existing Queue tab.

### 2.2 CLI surface — `life kill-switch <verb>`

Five verbs, all read-only except `clear`:

| Verb | Args | Reads | Writes |
|------|------|-------|--------|
| `status` | `--json` | env var + vault + data + last 10 events | none |
| `history` | `--limit N --json` | `data/review_queue/*.json` filtered to kill-switch events | none |
| `pause` | `--reason <text>` | current activation status | appends audit entry (manual_override) |
| `resume` | `--confirm` | current activation status | calls `recover_kill_switch` + appends audit entry |
| `recover` | (alias for `resume --confirm`) | — | — |

**No `enable` verb.** Per ADR-029 R11, the kill switch is a *safety*
mechanism, not a *workflow*. Activation happens through the 3 mechanisms
(env / vault / data) per ADR-029 S1. The CLI surfaces **inspection and
recovery only** — it never programmatically sets a kill switch. Operators
who want to halt use `touch data/.kill_switch` (R1 priority 3) or commit
`vault/.kill_switch.md` (priority 2) — explicit filesystem actions that
produce a co-located audit trail.

### 2.3 TUI surface — `[5]` tab

Mirrors the existing 4-tab layout (memory `phase-9-shipped`). New tab
renders 4 widgets (see §4.2 for layout).

---

## 3. Operator Workflow

### 3.1 Pre-iteration (every tuning cycle start)

```bash
# 1. Confirm kill switch is INACTIVE before starting
life kill-switch status --json | jq '.is_active'
# Expected: false. If true, run `life kill-switch history` first to triage.
```

### 3.2 During iteration (rate-limit monitoring per R10)

```bash
# 2a. Watch rate-limit window (KILL_SWITCH_RATE_LIMIT_PER_HOUR=50, WINDOW_S=3600)
#     Spins off the existing JSON output every 5s; no new daemon.
watch -n 5 'life kill-switch status --json | jq ".rate_limit"'

# 2b. (TUI alternative — opens tab [5] in the operator TUI)
python -m interfaces.tui.operator
# Press `5` to switch to KillSwitch tab.
```

The CLI `status --json` output includes a `rate_limit` block computed
locally by re-reading `data/review_queue/*.json` (sliding 1h window per
ADR-029 R10). No new state — purely a read of the existing queue.

### 3.3 False positive (kill switch fired but bypass was legitimate)

```bash
# 3. Inspect the firing event
life kill-switch history --limit 1 --json | jq '.[] | {trigger, actor_at_fault, entity_id, recovery_path, context}'

# 4. Decide: false positive → resume; true positive → leave active.
life kill-switch resume --confirm \
    --reason "W4.7 retroactive fix landed; bypass was legitimate transition_validator gap"
# → appends a TaskChange-style audit entry to data/review_queue/<ts>-RESUME-<kill_id>.json
#   with action="kill_switch_resume" and the operator's --reason string.
# → calls recover_kill_switch(vault_root, data_root) from kill_switch.py:441.
# → EXIT 0 on success, EXIT 2 if any of the 3 mechanisms remains active.
```

### 3.4 True positive (kill switch firing is correct)

```bash
# 3. Inspect + leave active.
life kill-switch history --limit 1 --json

# 4. DO NOT run `resume`. Instead, fix the upstream bypass:
#    - actor_mismatch      → check transition_validator usage at the call site in <context.file>:<context.line>
#    - rate_limit_exceeded → raise KILL_SWITCH_RATE_LIMIT_PER_HOUR in algorithm_constants.json (then resume)
#    - manual_override     → operator already knows; re-evaluate the halt decision
#    - vault_write_bypass  → grep for direct filesystem writes to vault/ in the listed context.file
#
# 5. After the upstream fix, resume per §3.3.
```

### 3.5 State matrix — CLI verb × activation status

| Current state | `status` | `history` | `pause` | `resume` |
|---------------|----------|-----------|---------|----------|
| All 3 mechanisms inactive | exit 0, `is_active=false` | exit 0, returns last 10 kill-switch events (may be empty) | exit 0, no-op (already inactive); refuses with message unless `--force` | exit 0, no-op (nothing to clear) |
| `env_var` active | exit 1, `is_active=true, active_reason=env_var` | exit 0 | exit 1, refuses (env var can't be set via CLI) | exit 0 with `--confirm` |
| `vault_file` active | exit 1, `active_reason=vault_file` | exit 0 | exit 1, refuses (vault writes go through `vault_write` MCP tool, not CLI) | exit 0 with `--confirm` (deletes the file per `recover_kill_switch`) |
| `data_file` active | exit 1, `active_reason=data_file` | exit 0 | exit 0, writes `data/.kill_switch` | exit 0 with `--confirm` |
| Multiple mechanisms active | exit 1, `active_reason=<first per R1 priority>` | exit 0 | exit 1, refuses | exit 0 with `--confirm` (clears all 3 per S4) |

`pause` refuses for `env_var` and `vault_file` because those mechanisms
require filesystem actions outside the CLI's authority (env var = shell
session; vault file = `vault_write` MCP tool). This forces the operator
to make a deliberate, location-specific choice — see §4 (safety rails).

---

## 4. Safety Rails

### 4.1 Default read-only

The CLI's default mode is read-only. `status` and `history` perform no
writes. `pause` requires `--reason <text>` (refuses empty string).
`resume` requires `--confirm` (refuses without the flag). This matches
the existing operator TUI invariant — "read-only, never writes to
`vault/`, `data/`, or anywhere" (per `interfaces/tui/operator/README.md:36-37`).

### 4.2 Confirmation prompt for `resume`

`resume` without `--confirm` prints:

```
Kill switch active via env_var.
Recovery will:
  - pop IKIGAI_KILL_SWITCH from os.environ
  - delete vault/.kill_switch.md (if present)
  - delete data/.kill_switch (if present)
  - append data/review_queue/<ts>-RESUME-<kill_id>.json (audit)

Pass --confirm to proceed. Pass --dry-run to preview only.
```

`--dry-run` shows the plan without executing. This mirrors the existing
`recover_kill_switch` semantics in `sys_ikigai/security/kill_switch.py:441`
but adds explicit human-in-the-loop confirmation.

### 4.3 Audit trail requirement

Every `pause` and `resume` invocation **MUST** append a JSON entry to
`data/review_queue/` (per ADR-029 S5.1). The entry schema is the existing
`KillSwitchEvent` with `action="kill_switch_resume"` or
`action="kill_switch_pause"` (R11 append-only enum extension — same
pattern as `action="kill_switch_active"` shipped at W5.1.1). Refusal to
append halts the operation (fail-closed).

### 4.4 TUI tab — visual confirmation

The 5th TUI tab renders the kill switch state as a **persistent status
banner** at the top of every other tab when active (not just the
KillSwitch tab itself). This mirrors how the existing Queue tab shows a
pending-events count badge (`interfaces/tui/operator/app.py:48-58`).
Visually:

```
+---------------------------------------------------+
| KILL SWITCH ACTIVE — vault_file (priority 2)      |
| 3 events in last 1h | last trigger: actor_mismatch |
| recovery: edit vault/.kill_switch.md status: inactive |
+---------------------------------------------------+
```

The banner is **read-only** — click-through opens the KillSwitch tab
where `p` (pause) and `r` (resume, requires `shift+r`) keys trigger the
same CLI verbs via subprocess.

### 4.5 Refusal to clear without context

`resume` requires a non-empty `--reason` argument. Refuses with exit
code 3 if missing. The reason is persisted to the audit entry's
`context.reason` field — makes the W5.10 tuning procedure audit trail
(ADR-030 §3) searchable by rationale.

---

## 5. Scope Boundary (OUT of scope for W5.3)

These are explicitly **not** W5.3. Each is a follow-up task with its own
design document or ADR.

| Item | Owner | Reference | Why out of scope |
|------|-------|-----------|------------------|
| Auto-revert logic | W5.10 | ADR-030 §3 | ADR-013 (planner-only) + R11 (human-in-the-loop) forbid auto-clear. Auto-revert would defeat the kill switch's safety purpose. |
| Algorithmic tuning procedure | W5.10 | ADR-030 §3 | Tuning workflow (5-min iteration cadence, evidence ledger) is its own scope. W5.3 surfaces the kill switch state; W5.10 surfaces tuning state. |
| SONHO log ritual integration | W5.6 | memory `plan-a-sonho-log-ritual` | Gated on 5+ SONHO logs. W5.3 surfaces kill switch events; W5.6 surfaces the human's interpretation of those events. |
| Meta-planner wiring (kill switch → meta-planner abort) | Plan D E-track | `docs/superpowers/plans/2026-09-04-meta-planner-plan-d.md` | The meta-planner is a separate subgraph. Kill switch interaction with the meta-planner is a separate design decision. |
| Kill switch activation from CLI | — | ADR-029 S1, R11 | Activation is intentionally filesystem-only (3 mechanisms). CLI activating the kill switch would re-introduce the bypass risk that R5 catches. |
| Auto-rate-limit tuning | — | ADR-029 R10, ADR-019 | Rate limit values live in `algorithm_constants.json`. Operator edits the JSON per ADR-019; CLI never writes to JSON. |

---

## 6. Implementation Sketch (NOT code — for reviewer)

The implementation is **purely consumer-side** — it imports the existing
public API from `sys_ikigai.security.kill_switch`:

- `check_kill_switch(vault_root, data_root)` → `KillSwitchActivationStatus`
- `KillSwitchEvent` (Pydantic v2 strict)
- `recover_kill_switch(vault_root, data_root)` → `bool`

No new schemas. No new constants. No new drift invariants. W5.3 adds:

1. `interfaces/cli/kill_switch.py` (Typer sub-app, ≤ 200 lines)
2. Registration line in `interfaces/cli/read_tasks.py:app.add_typer(...)`
3. 5th tab + status banner in `interfaces/tui/operator/app.py` + `data.py`
4. E2E test `interfaces/cli/tests/test_kill_switch_cli.py` (mirror the
   W6.X `test_review_queue_worker` dual-module patch pattern — see
   memory `test-review-queue-worker-dual-module-fix-2026-09-05`)
5. E2E test `interfaces/tui/operator/tests/test_kill_switch_tab.py` (if
   not already covered by `app.py` integration tests)

The 5th TUI tab's `pause` / `resume` keys shell out to the CLI via
`subprocess.run` — **no direct import of `kill_switch.py` from the TUI**.
This keeps the TUI's import chain shallow (per the existing
`data.py:18-22` shallow-import precedent) and means the TUI test suite
never has to mock the kill switch module.

---

## 7. Acceptance Criteria

W5.3 ships when:

- [ ] `life kill-switch status --json` returns the activation status in
      < 100ms (filesystem stat is the dominant cost per ADR-029 S1; ~1ms
      amortized).
- [ ] `life kill-switch history --limit N` reads `data/review_queue/`
      filtered to kill-switch events only (excludes TaskChange entries).
- [ ] `life kill-switch resume --confirm --reason "..."` clears all 3
      mechanisms and appends an audit entry.
- [ ] `life kill-switch resume` (without `--confirm`) refuses with exit
      code 2 and prints the confirmation prompt.
- [ ] `life kill-switch resume --reason ""` refuses with exit code 3.
- [ ] Operator TUI tab `[5]` renders activation state with the same
      visual language as existing tabs 1-4.
- [ ] Operator TUI banner is **read-only** (no `p`/`r` keys without
      `shift+` prefix).
- [ ] Drift invariants unchanged (no new invariant needed — W5.3 is
      pure consumer).
- [ ] ruff + mypy clean. 0 new Python `DEFAULT_KILL_SWITCH_*` constants
      (ADR-019 R2 — verify by `grep -r "DEFAULT_KILL_SWITCH" src/ikigai/src/`).

---

## 8. References (paths only — no duplication)

- ADR-029 (architecture): `code-docs/adr/ADR-029-kill-switch-review-queue.md`
- ADR-030 (tuning procedure): `code-docs/adr/ADR-030-empirical-algorithm-tuning.md`
- ADR-019 (constants in JSON only): forthcoming W5.2
- Plan D (meta-planner): `docs/superpowers/plans/2026-09-04-meta-planner-plan-d.md`
- Implementation (W5.1.1): `sys_ikigai/security/kill_switch.py`
- Algorithm constants: `src/ikigai/src/agents/v2/prompts/algorithm_constants.json`
  (keys: `KILL_SWITCH_RATE_LIMIT_PER_HOUR=50`,
  `KILL_SWITCH_RATE_LIMIT_WINDOW_S=3600`, `KILL_SWITCH_HALT_TIMEOUT_S=5.0`,
  `KILL_SWITCH_NOTIFY_OPERATOR=true`, `REVIEW_QUEUE_BATCH_SIZE=10`)
- Drift detector: `src/ikigai/tests/test_canonical_scope.py` (invariants k, l)
  + `src/ikigai/tests/test_drift_invariants.py` (invariant e retroactive)
- Operator TUI precedent: `interfaces/tui/operator/app.py` (4-tab layout)
  + memory `phase-9-shipped`
- Dual-module patch pattern: memory `test-review-queue-worker-dual-module-fix-2026-09-05`
- Wave 5 backlog: `~/.git/sdd/progress.md` (W5.3 row)
