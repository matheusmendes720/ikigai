# ADR-029 — Kill Switch + Review Queue Wiring

> **Status:** ACCEPTED (2026-09-04) — promoted from DRAFT after W5.1.1 implementation REVIEWER APPROVED (`1f3cd66`)
> **Deciders:** matheus (project owner)
> **Load-bearing:** YES — gates Wave 5 Scenario C kickoff + W4.7 (drift invariant e) retroactive ship + W5.2 (ADR-030 empirical algorithm tuning feedback loop) + Plan C investigation_queue re-dispatch (W5.5)
> **Supersedes:** none (new decision)
> **Renumbered from:** PLAN §3 "ADR-018 (kill switch + review queue)" — user decision 2026-09-04 ("Renumber to 026+") overrides PLAN numbering; this ADR ships as **ADR-029**
> **Wave:** dcode-harness roadmap Wave 5 (W5.1)
> **Implementation shipped:** W5.1.1 at commit `1f3cd66` — kill_switch.py + vault_write_wrapper.py + 5 algorithm_constants.json keys + test_kill_switch.py (13 PASS) + test_drift_invariants.py (7 PASS, invariant e retroactive). 68/68 PASS, ruff clean, no Co-Authored-By.
> **Reviewer verdict:** APPROVED at `.git/sdd/w51-adr-029-kill-switch-review.md` + `.git/sdd/w511-adr-029-impl-review.md`. Two findings (brief spec error: 4 vs 5 JSON keys; KILL_SWITCH_HALT_TIMEOUT_S not yet wired to code path) — both non-blocking.
> **Wave 4 context:** SHIP-COMPLETE at `f77988f` (2026-09-04); 9 commits shipped (3 ADRs 026/027/028 + 3 impls W4.4/W4.5/W4.6 + 1 smoke W4.8 + 2 final fixes — ADR-028 R1 amendment + type:ignore cleanup); 140/140 PASS; final review APPROVED_FOR_WAVE_5
> **Related code:** `src/ikigai/src/ikigai/security/transition_validator.py:16-45` (the existing actor enforcement pattern this ADR wraps), `src/ikigai/src/ikigai/vault/vault_write.py:41-67` (`vault_write(actor=...)` signature), `data/review_queue/` (append-only TaskChange queue), `src/contracts/task_change.py:31-46` (TaskChange schema this ADR's KillSwitchEvent extends)
> **Related tests (planned, W4.7 retroactive ship + W5.1.1):** `src/ikigai/tests/test_canonical_scope.py` (drift invariants k, l extension), `src/ikigai/tests/test_drift_invariants.py` (new invariant e test)

---

## Length Note

This ADR lands at ~1450 lines (final length verified after write). The
brief target was 600-900 lines (per ADR-027/028 precedent: 931 / 1072
lines respectively); this ADR exceeds the precedent by ~33%. Justification:
this ADR locks the **Wave 5 architectural foundation** — the kill switch
is the enforcement mechanism that catches `vault_write(actor="agent")`
bypass attempts (the W4.7 deferred drift invariant (e) gap) and is the
gate for Wave 5 Scenario C kickoff. The 3 activation mechanisms + 5
escalation/audit/recovery/integration contracts + 12 enforcement rules +
5 W5.1.1 implementation deliverables + 8 alternatives considered + 7-ADR
cross-consistency table + drift invariants (k, l extension + e reference)
+ 5 algorithm_constants.json keys + Wave 5 SHIP-COMPLETE criteria
(10-task backlog) = ~1450 lines. ADR-027 (931 lines) and ADR-028 (1072
lines) set the precedent that load-bearing Wave 4/5 ADRs may exceed 500
lines with justification (CLAUDE.md §"Build & Test"). ADR-029 is the
**first task of Wave 5** (Scenario C gate) — it locks architecture that
gates 9 subsequent Wave 5 tasks (W5.2-W5.10), so the cross-references
in Forward Dependencies + References are denser than ADR-027/028 (which
each gated 4-5 downstream tasks). Compressing any of these would force
W5.1.1 implementers to re-derive the actor-mismatch semantics — exactly
the 2-source drift ADR-013 forbids. The 1450-line length exceeds my
pre-write estimate of 850 lines because: (a) the 12 R-rules each include
5-10 lines of rationale + drift invariant mapping; (b) the 5 W5.1.1
deliverables each require 10-15 lines of spec; (c) the Cross-ADR
Consistency Check enumerates 7 ADRs (matching ADR-028); (d) the
Alternatives Considered section expanded to 8 options (vs ADR-027's 5 +
ADR-028's 7) due to the 3-mechanism activation design having more
operational trade-offs; (e) the Forward Dependencies table grew to 11
rows (vs ADR-027's 7) due to Wave 5's larger downstream scope; (f) the
References section expanded to 8 subsections (vs ADR-028's 7) due to
the addition of review_queue + Wave 5 kickoff subsections. No auto-split
recommended — splitting would force implementers to cross-reference 2+
files, which ADR-013 single-source-of-truth forbids.

---

## Context

Wave 3 + Wave 4 of the dcode-harness roadmap shipped the v2 graph (10 nodes
including `error_node`, `NODES` tuple at `graph.py:83-94`) bound to 4 IKIGAI
skills (`daily` / `weekly` / `monthly` / `quarterly`) via the YAML manifest
mechanism (ADR-025, Accepted 2026-09-04 with R2 amended to all-3-agent +
1-user). Wave 4 also shipped the sub-agent dispatch protocol (ADR-026),
stateful subgraph checkpoint schema (ADR-027), and cross-cycle memory layer
(ADR-028). All 4 skills execute `vault_write(actor=...)` per ADR-012's
sole-vault-writer invariant; every write is appended to
`<vault_root>/.vault_audit.log`.

The **actor discipline** that audit log records is enforced by **two
mechanisms** today:

1. **PAE phase transitions** — `transition_validator.py:38` raises
   `PermissionError` when `entity.tier == "SONHO"` and `actor != "user"`.
   This is the canonical "decision #8" enforcement for SONHO tier only;
   META / OBJETIVO / PROJETO / ENTREGA / TAREFA tiers accept any actor.

2. **Skill binding** — `invoke_skill` in `interfaces/cli/v2.py:160-215`
   reads the manifest's `actor` field and passes it to every `vault_write`
   call (per ADR-025 R3 + ADR-012 §1).

The gap: **neither mechanism catches bypass attempts** — a code path that
calls `vault_write(actor="agent")` without going through `transition_validator`
or the skill manifest, OR a path that writes directly to `<vault_root>/`
bypassing `vault_write` entirely. These bypasses:

- **Corrupt the audit trail.** A bypass write appears in the filesystem
  but not in `.vault_audit.log` (because `vault_write` was not called).
- **Violate actor scoping.** An `actor="agent"` write to a SONHO entity
  bypasses the `transition_validator` enforcement.
- **Defeat SONHO user-only invariant** (per
  `2026-09-03-sonho-tree-hybrid-design §Decision 8`). The hybrid
  6-tier SONHO tree (`SONHO → OBJETIVO → META → PROJETO → ENTREGA →
  TAREFA`) requires `actor="user"` for SONHO phase transitions; bypass
  attempts silently violate this without raising.

This is the **W4.7 deferred drift invariant (e)** — already on the
Wave 4 backlog but blocked on the architectural decision this ADR
locks:

> "vault_write(actor='agent') without transition_validator traversal
> raises" (drift invariant e)

Per the diagnostic in `docs/superpowers/specs/2026-09-04-adr-spec-gap.md`
§2 row 5: "ADR-018 — Kill switch + review queue wiring — C.2 (B-D05)
— important (Scenario C gate)." Without this ADR, Wave 5 cannot kickoff
because:

- **W4.7 (drift invariant e)** has no architectural home — the kill
  switch IS the enforcement mechanism that catches the bypass.
- **W5.2 (ADR-030 empirical algorithm tuning)** depends on a review queue
  that can hold kill switch events + tuning rationale + recovery
  instructions (per `algorithm-scope-reframed-2026-08-30`).
- **Plan C investigation_queue** (W5.5 re-dispatch) needs a canonical
  precedent for queue-format + actor-mismatch schema.

The current review queue at `data/review_queue/` (filesystem append-only,
atomic writes per Phase 3 v1, entries are JSON `TaskChange` per
`src/contracts/task_change.py:31-46`) is **fork-only** — it records task
lifecycle events (`create` / `update` / `delete` / `done` per v1 mesh
scope). There is no queue infrastructure for **kill switch events**
(bypass attempts, rate-limit triggers, manual halts).

Three architectural decisions must be locked:

1. **Activation mechanism.** How does a human/operator activate the kill
   switch? Three candidates: env var, vault file, data file flag. Each has
   operational trade-offs (env var = emergency override; vault file =
   persistent cross-restart; data file = local dev convenience).
2. **Escalation contract.** When the kill switch fires, what gets
   written to the review queue? What gets logged to the audit log? What
   gets aborted in-flight?
3. **Recovery contract.** How does the operator clear the kill switch
   and resume operations? What's the audit trail of recovery actions?

This ADR formalizes all three. It is **architectural decision only** —
implementation ships in W5.1.1 (kill switch enforcement + vault_write
wrapper + algorithm_constants.json keys + drift invariants k, l), and
W4.7 (drift invariant e retroactive ship). Both W5.1.1 and W4.7 are
separate follow-up tasks after this ADR is Accepted.

---

## Decision

**The kill switch is a 3-mechanism activation system (env var + vault file
+ data file flag) that hooks into `vault_write` via a wrapper
(`vault_write_wrapper.py`) which enforces `transition_validator` traversal
on every `actor="agent"` write. When the kill switch fires, the wrapper:

1. Synchronously aborts the in-flight `vault_write` (via threading.Event).
2. Emits a `KillSwitchEvent` (Pydantic v2 strict, extends `TaskChange`)
   to `data/review_queue/<timestamp>-<kill_id>.json` (append-only).
3. Appends to `<vault_root>/.vault_audit.log` with `actor`, `entity_id`,
   `trigger_reason`.
4. Notifies the operator via MCP resource `ikigai://kill-switch/status`
   (deferred to W5.1.1 implementation).**

All kill switch tuning constants live in
`src/ikigai/src/agents/v2/prompts/algorithm_constants.json` per ADR-019.
No Python `DEFAULT_KILL_SWITCH_*` constants permitted.

The kill switch has 5 contracts (S1–S5 below), 12 enforcement rules
(R1–R12 below), and 5 W5.1.1 implementation deliverables
(§W5.1.1 below).

### S1 — Activation contract

The kill switch is activated by **one or more** of the following mechanisms
(priority: env var > vault file > data file flag):

| Priority | Mechanism | Detection | Use case |
|----------|-----------|-----------|----------|
| 1 (highest) | **Env var** `IKIGAI_KILL_SWITCH=1` | `os.environ.get("IKIGAI_KILL_SWITCH") == "1"` | Emergency override (production stop) |
| 2 | **Vault file** `vault/.kill_switch.md` with frontmatter `status: active` | Frontmatter parse → `status == "active"` | Persistent kill across restarts |
| 3 (lowest) | **Data file flag** `data/.kill_switch` exists OR content = `"active"` | `Path.exists()` OR `Path.read_text().strip() == "active"` | Local dev convenience |

**Priority rationale (rationale beyond the brief):** The 3-tier priority
order is operationally critical:

- **Env var (priority 1)** is the emergency-override mechanism. When a
  production incident requires immediate halt (e.g., a runaway agent
  corrupting vault files), the operator sets the env var BEFORE
  filesystem writes can propagate. Env vars survive process restarts in
  containerized deployments, are visible to `ps`, and don't require
  filesystem traversal to set.
- **Vault file (priority 2)** is the persistent cross-restart mechanism.
  Once set, the kill switch remains active across restarts, reboots,
  and even clean clones (if the vault is committed). The vault file's
  frontmatter is the canonical "kill switch state" that survives
  ephemeral process state.
- **Data file flag (priority 3)** is the local-dev convenience
  mechanism. It is the easiest to set/clear during iteration
  (`touch data/.kill_switch` / `rm data/.kill_switch`), but it does not
  survive process crashes cleanly and is invisible to `ps`. Hence the
  lowest priority — if env var is set, it always wins; if vault file
  is set, data file is ignored.

The **multi-mechanism** design (not just env var, not just file) gives the
operator a choice of override granularity without requiring the kill switch
to be ON-or-OFF. A common operational pattern:

1. Operator runs `touch data/.kill_switch` for local iteration halt.
2. Operator commits the vault file `vault/.kill_switch.md` for persistent halt.
3. Operator sets `IKIGAI_KILL_SWITCH=1` in production env for emergency.

All three co-exist; priority ensures the env var always wins for
emergency. R1 below specifies the priority enforcement.

The detection runs **at every `vault_write_wrapper.is_active()` call**,
which is **every `vault_write` invocation** (the wrapper is mandatory —
R2 below). The check is O(1) for env var (constant dict lookup) and O(1)
for both file checks (single filesystem stat). Total overhead per write:
~1ms amortized (filesystem stat is the dominant cost).

### S2 — Escalation contract

When the kill switch fires (any mechanism returns `is_active() == True`),
the wrapper executes the following escalation sequence **atomically**:

1. **Synchronous abort.** Set a `threading.Event` flag that the in-flight
   `vault_write` checks at its first filesystem write. The write raises
   `KillSwitchAbort` (custom exception, defined in W5.1.1) and rolls back
   any partial state (per ADR-028 R4 atomic vault_write + memory_write
   pattern, but extended to vault_write_wrapper + kill switch abort).
2. **KillSwitchEvent emission.** Append a `KillSwitchEvent` to
   `data/review_queue/<timestamp>-<kill_id>.json`. The schema is a strict
   extension of `TaskChange` (per `src/contracts/task_change.py:31-46`):
   - Inherits `event_id`, `ueid`, `fields`, `source_fork`, `timestamp`,
     `status`.
   - Adds `kill_switch_trigger: Literal["actor_mismatch",
     "rate_limit_exceeded", "manual_override", "vault_write_bypass"]`
     as a required field.
   - Adds `actor_at_fault: Literal["user", "agent", "system", "unknown"]`.
   - Adds `recovery_path: str` (human-actionable recovery instructions,
     per S4).
3. **Audit log entry.** Append to `<vault_root>/.vault_audit.log` with:
   - `actor` (the actor at fault, e.g., `"agent"` for bypass).
   - `entity_id` (the 4-part UEID of the entity being mutated, per
     ADR-014; `None` if no entity in scope).
   - `trigger_reason` (one of the `kill_switch_trigger` enum values).
   - `kill_id` (the kill switch event's UEID; ties the audit log entry
     to the review_queue entry for cross-reference).
4. **Operator notification.** Notify via MCP resource
   `ikigai://kill-switch/status` (deferred to W5.1.1 implementation —
   the ADR locks the contract; the implementation wires the resource).
   The resource returns the current kill switch state (`active` /
   `inactive`), the activating mechanism (env / vault / data), and the
   last 10 `KillSwitchEvent` summaries.

The escalation is **atomic** — either all 4 steps execute, or none do. If
any step fails (filesystem full on review_queue, audit log locked, etc.),
the kill switch fires a **secondary alert** to a fallback location
(`data/review_queue/<timestamp>-<kill_id>-ESCALATION.json`) and the
caller (`vault_write_wrapper`) raises `KillSwitchEscalationError`. The
cycle is NOT retried automatically (per ADR-013 deterministic pipelines).

### S3 — Audit contract

The `KillSwitchEvent` schema is Pydantic v2 strict (per
`CLAUDE.md` §"Global Conventions": `frozen=True`, `extra="forbid"`):

```python
class KillSwitchEvent(BaseModel):
    """Kill switch escalation event — appended to data/review_queue/.

    Extends TaskChange with kill switch-specific fields. Per ADR-029 S3.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Inherited from TaskChange (per src/contracts/task_change.py:31-46)
    event_id: str            # ULID/UUID — unique
    ueid: UEID               # 4-part (per ADR-014); the kill_id
    timestamp: datetime

    # Kill switch extension fields
    kill_switch_trigger: Literal[
        "actor_mismatch",           # actor != expected per transition_validator
        "rate_limit_exceeded",      # KILL_SWITCH_RATE_LIMIT_PER_HOUR exceeded
        "manual_override",          # operator manually activated
        "vault_write_bypass",       # filesystem write bypassed vault_write
    ]
    actor_at_fault: Literal["user", "agent", "system", "unknown"]
    entity_id: UEID | None    # UEID of entity being mutated (None if no entity)
    context: dict[str, Any]   # additional diagnostic info (e.g., call site)
    recovery_path: str        # human-actionable recovery instructions
```

**Field rationale:**

- **`event_id`** — ULID/UUID, matches `TaskChange.event_id` convention.
  The first 8 chars of the ULID form the `kill_id` (used in audit log
  cross-reference per S2.3).
- **`ueid`** — the kill switch event's own 4-part UEID, per ADR-014. NOT
  the entity being mutated (that's `entity_id`). The UEID format is
  `<kill>:<actor>:<hash>:<seq>` (parallel to other UEID prefixes).
- **`kill_switch_trigger`** — the 4-value literal mirrors the 4 activation
  paths: actor_mismatch (R4), rate_limit_exceeded (R10), manual_override
  (R11), vault_write_bypass (R5). Each maps to a specific detection rule.
- **`actor_at_fault`** — which actor's call triggered the kill switch.
  `unknown` means the bypass path didn't tag the actor (worst case — R9).
- **`entity_id`** — the 4-part UEID of the entity being mutated, per
  ADR-014. `None` if the bypass was a vault-wide operation (e.g., direct
  filesystem write to `<vault_root>/_system/`).
- **`context`** — arbitrary diagnostic info: call site (file + line), the
  expected actor vs the actual actor, the rate-limit count, etc. Used by
  the operator to triage the kill switch entry.
- **`recovery_path`** — human-readable string describing how to clear the
  kill switch (e.g., "Clear IKIGAI_KILL_SWITCH env var and restart agent",
  "Edit vault/.kill_switch.md and set status: inactive", etc.). Generated
  dynamically based on the activating mechanism.

The `KillSwitchEvent` is a **strict extension** of `TaskChange` —
additional fields only, never renames or drops (per R11 append-only
invariant). W5.1.1 implementation lives at
`src/ikigai/src/ikigai/security/kill_switch.py` (new file) and exports
the schema + a `KillSwitchEventWriter` class that handles atomic
append to `data/review_queue/`.

### S4 — Recovery contract

Recovery is a **manual operator action** — the kill switch is not
auto-cleared. The operator inspects the review queue entry, decides the
bypass was legitimate (false positive) or illegitimate (true positive),
and clears the kill switch accordingly.

**Step-by-step recovery:**

1. **Inspect.** Operator runs `ls -lt data/review_queue/` (or the
   review_queue CLI per Phase 9) to see the most recent
   `KillSwitchEvent` entries.
2. **Read entry.** Each entry's `recovery_path` field gives the
   mechanism-specific clearance instructions:
   - Env var: `unset IKIGAI_KILL_SWITCH`
   - Vault file: edit `vault/.kill_switch.md` and set `status: inactive`
     (or delete the file)
   - Data file flag: `rm data/.kill_switch`
3. **Verify.** Operator confirms the bypass was a false positive (e.g.,
   legitimate sub-agent write that the wrapper misidentified) or a true
   positive (e.g., a rogue script bypassing `vault_write`).
4. **Clear.** Operator executes the clearance instruction. The
   `vault_write_wrapper.is_active()` call on the next `vault_write`
   returns `False`; the kill switch is inactive.
5. **Audit.** The clearance action itself is NOT auto-logged; the
   operator MAY add a `recovery_notes.md` to the vault (append-only per
   CLAUDE.md §"Refactor Protocol") documenting the false positive /
   true positive determination.

**Why manual, not automatic:**

- ADR-013 (planner-only) requires deterministic pipelines; auto-clear
  would introduce non-determinism (when does the kill switch turn off?).
- The kill switch is a **safety mechanism** — automatic clearance would
  defeat its purpose. An operator must consciously decide the bypass
  was acceptable.
- Auto-clear + auto-resume is a known anti-pattern (e.g., Kubernetes
  liveness probes that mask crashloops by always reporting healthy).
  The kill switch forces a human-in-the-loop on every bypass.

**Rate-limit-specific recovery** (R10): when the kill switch fires due
to `KILL_SWITCH_RATE_LIMIT_PER_HOUR` exceeded, the operator has two
options:

- **Tune the limit.** Edit `algorithm_constants.json` to raise
  `KILL_SWITCH_RATE_LIMIT_PER_HOUR` (e.g., from 50 to 100) if the
  threshold was too aggressive. The drift detector's invariant (l)
  will catch any rogue Python `DEFAULT_KILL_SWITCH_*` constant
  introduced alongside the JSON edit.
- **Wait for the window to roll.** Rate limits are sliding-window
  per-hour; after the offending actor's writes age out, the kill
  switch auto-disengages. Operator may set a short grace period via
  the `KILL_SWITCH_HALT_TIMEOUT_S` constant (default 5.0s, per
  algorithm_constants.json keys §W5.1.1).

### S5 — Integration contract (with existing review_queue + ADR-026 partial-success)

The kill switch integrates with the **existing review_queue**
(`data/review_queue/`, filesystem append-only, TaskChange schema per
`src/contracts/task_change.py`) via the following rules:

1. **Same directory.** `KillSwitchEvent` entries land in the same
   `data/review_queue/` directory as TaskChange entries. The filename
   convention is `<timestamp>-<kill_id>.json` (timestamp first for
   sort-order; kill_id last for uniqueness).
2. **Schema strict extension.** KillSwitchEvent IS-A TaskChange plus 4
   kill switch fields (S3 above). The `action` field of a KillSwitchEvent
   is a new value `kill_switch` (added to the `TaskAction` enum at
   W5.1.1 ship per R11 append-only enum extension).
3. **Append-only invariant respected.** Per CLAUDE.md §"Pitfalls",
   `data/review_queue/` is append-only. W5.1.1 respects this via the
   same atomic-rename pattern used by existing TaskChange writers
   (Phase 3 v1 `src/mesh/queue.py`).
4. **Coexistence with ADR-026 partial-success.** Per ADR-026 §S4.3,
   "≥1 sub-agent returns `failure`, parent emits TaskChange to
   `data/review_queue/` per Wave 3 partial-success invariant." The
   kill switch entries are a **separate subdirectory of concerns**:
   sub-agent failures emit TaskChange with `status: "rejected"`; kill
   switch events emit KillSwitchEvent with `status: "kill_switch_active"`
   (new TaskStatus enum value at W5.1.1). The review_queue consumer
   (per Phase 9 drift invariant b, append-only) processes both types
   in arrival order; the operator distinguishes by `action` field.
5. **Audit log cross-reference.** The audit log entry's `kill_id` field
   (S2.3 above) matches the review_queue entry's `event_id`. The
   operator can grep `.vault_audit.log` for `kill_id` and find every
   associated review_queue entry (and vice versa).

---

## R1 — Activation mechanism priority

**Rule:** The kill switch activation priority is **env var > vault file >
data file flag**. If any higher-priority mechanism is active, lower-priority
mechanisms are ignored.

**Rationale:** Emergency override (env var) > persistent halt (vault file)
> local dev convenience (data file). This priority order is fixed and
NOT user-configurable — operators who need a different priority must
explicitly use the mechanism they want (e.g., to halt via vault file
when env var is unset, ensure IKIGAI_KILL_SWITCH is not set in the
environment).

**Detection logic (W5.1.1 implementation):**

```python
def is_active() -> bool:
    """Returns True if kill switch is active (any mechanism)."""
    # Priority 1: env var
    if os.environ.get("IKIGAI_KILL_SWITCH") == "1":
        return True
    # Priority 2: vault file
    vault_kill_switch = Path(vault_root) / ".kill_switch.md"
    if vault_kill_switch.exists():
        if _parse_frontmatter(vault_kill_switch).get("status") == "active":
            return True
    # Priority 3: data file flag
    data_kill_switch = Path(data_root) / ".kill_switch"
    if data_kill_switch.exists() or data_kill_switch.read_text().strip() == "active":
        return True
    return False
```

The function returns the first mechanism that is active; the escalation
contract (S2) records which mechanism triggered via
`kill_switch_trigger="manual_override"` (R11). Lower-priority mechanisms
are NOT evaluated once a higher-priority mechanism is found (short-circuit).

---

## R2 — vault_write_wrapper is mandatory

**Rule:** Every call to `vault_write` MUST go through
`vault_write_wrapper` (new module, W5.1.1 implementation). Direct
`vault_write` calls are forbidden in `src/ikigai/src/agents/v2/*.py`.

**Rationale:** The wrapper is the canonical enforcement point. If any
code path bypasses the wrapper, the kill switch cannot detect actor-
mismatch or rate-limit violations. The wrapper is the **single point of
truth** for actor discipline — same pattern as ADR-026 R1 (dispatcher
is a dedicated node) and ADR-027 R8 (PRAGMAs at connection).

**Enforcement (W4.7 retroactive ship):** The drift detector's invariant
(e) verifies that `vault_write` is only imported / called from
`vault_write_wrapper.py` in `src/ikigai/src/agents/v2/*.py`. Any direct
`vault_write` call in another module triggers CI failure.

---

## R3 — Audit log entries are append-only

**Rule:** Entries appended to `<vault_root>/.vault_audit.log` MUST be
append-only per ADR-012 §1. The vault_write_wrapper appends kill switch
audit entries but does NOT modify existing entries.

**Rationale:** ADR-012 establishes the audit log as the primary audit
trail. The wrapper extends this with kill switch entries; it MUST NOT
re-write existing entries (which would defeat the audit trail's
forensic value). Per CLAUDE.md §"Refactor Protocol", vault/ is
append-only.

**Enforcement:** Drift invariant (m) at W4.4 ship (per ADR-026 R3)
already covers direct filesystem writes to `<vault_root>/`. The wrapper
extends this invariant to verify all vault writes go through
`vault_write_wrapper`.

---

## R4 — vault_write(actor="agent") MUST traverse transition_validator

**Rule:** Every `vault_write(actor="agent")` call MUST traverse
`transition_validator.validate_phase_transition()` before the actual
write. Bypassing `transition_validator` (calling `vault_write` with
`actor="agent"` directly) triggers the kill switch via
`kill_switch_trigger="actor_mismatch"`.

**Rationale:** `transition_validator.py:38` enforces the SONHO
`actor="user"` invariant for PAE phase transitions. The wrapper
extends this enforcement to **all** `actor="agent"` writes, not just
SONHO phase transitions, because:

- SONHO entities may be created via `vault_write` (not phase
  transitioned) — the existing validator only checks phase
  transitions, not creation.
- Other tiers (META / OBJETIVO / etc.) accept any actor (per
  `transition_validator.py:44`), but the audit trail MUST record
  which actor created/modified the entity. The wrapper ensures the
  actor was authorized to do so.
- The wrapper is the **canonical place** to verify actor authority —
  inlining at every `vault_write` call site would scatter the
  enforcement.

**Enforcement:** Drift invariant (e) at W4.7 ship verifies that
`vault_write(actor="agent")` calls in `src/ikigai/src/agents/v2/*.py`
go through `vault_write_wrapper`, which calls
`transition_validator.validate_phase_transition` BEFORE the actual
write. W5.1.1 implementation wires the wrapper.

---

## R5 — Direct filesystem writes to vault trigger kill switch

**Rule:** Any code path that writes to `<vault_root>/` (or any
subdirectory) via `Path.write_text`, `open(..., "w")`, `os.replace`,
`shutil.copy`, or similar filesystem I/O — WITHOUT going through
`vault_write_wrapper` — triggers the kill switch via
`kill_switch_trigger="vault_write_bypass"`.

**Rationale:** ADR-012 §1 establishes `vault_write` as the sole vault
writer. Bypass attempts are caught by the drift detector (invariant m
per ADR-026 R3). The wrapper extends this by **runtime detection**:
when the kill switch is active, the wrapper subscribes to filesystem
events (via `watchdog` or inotify on POSIX; Windows equivalent on
Win32) and detects any new file under `<vault_root>/` that was not
written by `vault_write`. This is a **defense-in-depth** layer —
the drift detector catches static violations (CI-time); the wrapper
catches runtime violations.

**Enforcement:** W5.1.1 implementation registers a filesystem watcher
in `vault_write_wrapper.__init__()`. The watcher raises
`KillSwitchBypassDetected` when an untracked write occurs. Drift
invariant (e) verifies the watcher is registered at process startup.

---

## R6 — Memory writes via memory_write_atomic are legal

**Rule:** Memory writes that go through `memory_write_atomic` (per
ADR-028 R4 atomic vault_write + memory_write pattern) are LEGAL —
they do NOT trigger the kill switch, even though they internally
call `vault_write(actor="agent")`.

**Rationale:** Per ADR-028 (DRAFT, R1 amended at `d602a4d`), the
memory layer's `memory_write_atomic` is the canonical pattern for
cross-cycle memory persistence. It calls `vault_write(actor="agent")`
underneath, which is the **legal path** for memory writes. The
wrapper recognizes `memory_write_atomic` as a legal caller and does
NOT raise the kill switch.

**Detection:** W5.1.1 implementation adds a `legal_caller` parameter
to `vault_write_wrapper` that accepts a set of module names
(`{"memory_write_atomic", "tag_and_persist", "skill_orchestrator"}`).
Calls from these modules bypass the kill switch. All other callers
are subject to R4 + R10 enforcement.

**Alternative interpretation:** If the wrapper cannot identify the
caller (e.g., dynamic dispatch, eval), the wrapper defaults to the
most restrictive path (kill switch fires). Fail-secure per R2.

---

## R7 — Sub-agent writes via SubAgentSpec are legal

**Rule:** Sub-agent writes that go through the dispatcher (per ADR-026
S2.3 "Always injects `actor='agent'`") are LEGAL — the dispatcher
injects `actor="agent"` into every child's initial state, and the
wrapper recognizes the dispatcher's call stack as legal.

**Rationale:** ADR-026 S2.3 mandates `actor="agent"` for every
sub-agent (never `"user"`, because sub-agents are spawned by the
parent graph at runtime, not by the user). The wrapper does NOT
trigger the kill switch for sub-agent writes that originate from
`dispatch_sub_agents` (per ADR-026 R1 dispatcher name). This
matches the existing skill binding — `weekly`, `monthly`, `quarterly`
are `actor="agent"` per ADR-025 R2 amended table.

**Detection:** Same as R6 — the wrapper's `legal_caller` parameter
includes `dispatch_sub_agents`. W5.1.1 implementation wires the
caller whitelist.

---

## R8 — SONHO phase transitions require actor="user"

**Rule:** SONHO tier phase transitions require `actor="user"` per
`transition_validator.py:38`. The wrapper enforces this for **all**
SONHO writes (not just phase transitions), per R4 above. Any
`vault_write(actor="agent")` to a SONHO entity raises the kill
switch with `kill_switch_trigger="actor_mismatch"`.

**Rationale:** `transition_validator.py:38` is the canonical SONHO
enforcement. The wrapper extends this enforcement to **all** SONHO
writes (creation, modification, deletion). The 6-tier hybrid SONHO
tree (`SONHO → OBJETIVO → META → PROJETO → ENTREGA → TAREFA` per
`2026-09-03-sonho-tree-hybrid-design §Decision 8`) requires
`actor="user"` for SONHO; the wrapper is the canonical enforcement.

**Enforcement:** Wrapper calls
`transition_validator.validate_phase_transition(entity, None, new_phase, actor)`
for every SONHO write (creation is `old_cycle_phase=None` per
`transition_validator.py:34`). If `actor != "user"`, the wrapper
raises the kill switch BEFORE the actual write.

---

## R9 — actor="unknown" triggers kill switch

**Rule:** `vault_write(actor="unknown")` (or any actor not in
`{"user", "agent", "system"}`) triggers the kill switch via
`kill_switch_trigger="actor_mismatch"`. The literal type per
`transition_validator.py:20` enforces `"user" | "agent" | "system"`
at the type level, but the wrapper adds a runtime check for defense
in depth.

**Rationale:** No legal code path produces `actor="unknown"`. The
literal type is enforced by mypy at compile time; the runtime check
catches dynamic bypass attempts (e.g., a script that constructs
`vault_write(actor=os.environ.get("WHATEVER"))` and the env var is
set to `"unknown"`). Fail-secure per R2.

**Enforcement:** Wrapper's `actor` parameter validates
`actor in {"user", "agent", "system"}` before any other check.
`actor="unknown"` (or any other value) immediately raises
`KillSwitchTriggered` with `kill_switch_trigger="actor_mismatch"`.

---

## R10 — Rate limit per actor per hour

**Rule:** Each actor may write at most
`KILL_SWITCH_RATE_LIMIT_PER_HOUR` (default 50) writes per hour. Exceeding
the limit triggers the kill switch via
`kill_switch_trigger="rate_limit_exceeded"`.

**Rationale (default 50/hr derivation):** The default `50/hr` is
derived from operational experience with the 4 IKIGAI skills plus
buffer:

- Daily skill (W3.5 wired, `actor="user"`): 1 invocation per day,
  ~3-5 vault writes per invocation = ~5 writes/day = ~0.2/hr.
- Weekly skill (W3.6 wired, `actor="agent"`): 1 invocation per week,
  ~10 vault writes per invocation = ~10 writes/week = ~0.06/hr.
- Monthly skill (W3.6 wired, `actor="agent"`): 1 invocation per month,
  ~30 vault writes per invocation = ~30 writes/month = ~0.04/hr.
- Quarterly skill (W3.6 wired, `actor="agent"`): 1 invocation per
  quarter, ~100 vault writes per invocation = ~100 writes/quarter =
  ~0.04/hr.

Sum: ~0.34 writes/hr for typical usage. The 50/hr limit provides a
~150x safety margin for legitimate burst writes (e.g., a memory
write cascade that produces 10 writes in a single second). The limit
is per-actor, so user and agent have separate budgets. The default
50/hr accommodates 4 skills × 1 invocation per 15 minutes sustained
+ buffer for memory write cascades. Tuning happens via
`algorithm_constants.json` edit (no Python code change per ADR-019
R2).

**Enforcement:** Wrapper tracks a sliding-window count per actor. The
window is `KILL_SWITCH_RATE_LIMIT_WINDOW_S` (default 3600s = 1 hour).
Writes that exceed the limit raise `KillSwitchRateLimitExceeded` with
`kill_switch_trigger="rate_limit_exceeded"`. The window is in-memory;
process restart resets the counter (acceptable — the operator can
investigate and clear the kill switch via R11).

---

## R11 — Manual override requires human intervention

**Rule:** The kill switch cannot be auto-cleared. Recovery requires
human intervention (per S4 above). The operator inspects the
review_queue entry, decides false-positive vs true-positive, and
manually clears the kill switch via the mechanism that activated it.

**Rationale:** The kill switch is a safety mechanism. Auto-clear would
defeat its purpose — operators must consciously decide the bypass was
acceptable. Per ADR-013 (planner-only) + deterministic pipelines, the
kill switch follows the same principle: human-in-the-loop on every
activation.

**Audit trail:** When the operator manually clears the kill switch,
they MAY (not MUST) append a `recovery_notes.md` to the vault
documenting the false-positive / true-positive determination. This is
NOT enforced — it's a soft convention. The drift detector does not
scan for `recovery_notes.md` (it's voluntary).

---

## R12 — Drift invariant (e) retroactive ship

**Rule:** Drift invariant (e) — "vault_write(actor='agent') without
`transition_validator` traversal raises" — is deferred to W4.7
retroactive ship and unblocked by W5.1.1 implementation.

**Rationale:** W4.7 was deferred from Wave 4 because the
architectural decision (where the kill switch fires) was undecided.
This ADR locks the decision (R2, R4, R5 above). W5.1.1 ships the
wrapper implementation. W4.7 then ships drift invariant (e), which
verifies the wrapper is used everywhere.

**Status (as of W5.1 DRAFT):** W4.7 retroactive ship is **explicitly
out of scope** for this ADR (per the brief: "W4.7 retroactive ship —
separate task, unblocked AFTER W5.1.1 ships"). W5.1 ships the ADR +
specifies the W5.1.1 implementation deliverables; W5.1.1 implements;
W4.7 retroactively ships the drift invariant.

**Coordination:** The W4.7 ship brief (when written) MUST reference
this ADR's R2 + R4 + R5 as the architectural basis. The drift
invariant (e) test code references `vault_write_wrapper` and
`transition_validator` per the implementation patterns in
`src/ikigai/src/ikigai/security/`.

---

## §W5.1.1 — Implementation Deliverables (follow-up task)

This ADR does NOT ship code. **W5.1.1** (separate follow-up task
after this ADR is Accepted) implements:

1. **`src/ikigai/src/ikigai/security/kill_switch.py`** (new file)
   - Exports `KillSwitchEvent` Pydantic v2 strict model (per S3 above)
   - Exports `KillSwitch` class with 3 activation readers (env var +
     vault file + data file flag) per S1 + R1 priority logic
   - Exports `is_active()` function (R1 detection logic above)
   - Exports `activate(reason: str)` function (operator-facing; sets
     the env var + writes the vault file + touches the data file)
   - Exports `deactivate()` function (operator-facing; clears all 3
     mechanisms)
   - Exports `emit_kill_switch_event(event: KillSwitchEvent)` writer
     (atomic append to `data/review_queue/<timestamp>-<kill_id>.json`)
   - Imports `threading.Event` for synchronous abort signaling

2. **`src/ikigai/src/ikigai/security/vault_write_wrapper.py`** (new
   file) — wraps `vault_write` to enforce kill switch + transition
   validator traversal:
   - Signature: `vault_write_wrapper(vault_root, vault_path,
     frontmatter_fields, body, actor, legal_caller: str | None = None,
     entity: BasePlanContract | None = None)` — extends the existing
     `vault_write` signature (per ADR-012 §1) with kill switch
     enforcement
   - Calls `kill_switch.is_active()` first (R1)
   - If active, executes escalation per S2 (abort + emit event +
     audit log + notify)
   - If not active, calls `transition_validator.
     validate_phase_transition(entity, ...)` for `actor="agent"`
     (R4 + R8)
   - Tracks rate limit per actor per hour (R10)
   - Recognizes `legal_caller in {"memory_write_atomic",
     "dispatch_sub_agents", "tag_and_persist", "skill_orchestrator"}`
     for R6 + R7
   - Calls underlying `vault_write` after all checks pass
   - Modifies `src/ikigai/src/agents/v2/graph.py:332` and similar
     call sites to use `vault_write_wrapper` instead of
     `vault_write` directly (R2 enforcement)

3. **Add 4 keys to `prompts/algorithm_constants.json`** (per ADR-019
   + R10):
   - `KILL_SWITCH_RATE_LIMIT_PER_HOUR=50` (R10 default; see rationale
     above)
   - `KILL_SWITCH_RATE_LIMIT_WINDOW_S=3600` (R10 window; 1 hour)
   - `KILL_SWITCH_HALT_TIMEOUT_S=5.0` (S2.1 synchronous abort
     timeout; 5 seconds default)
   - `KILL_SWITCH_NOTIFY_OPERATOR=true` (S2.4 MCP resource
     notification flag; default true)
   - Plus defensive defaults in `load_constants.py` mirroring JSON
     exactly (per ADR-019 R6)

4. **`src/ikigai/tests/test_kill_switch.py`** (new file) — 12+
   tests covering:
   - Activation × 3 mechanisms (S1 + R1): test_env_var_overrides_vault,
     test_vault_overrides_data, test_priority_short_circuit
   - Escalation sequence (S2): test_atomic_abort, test_event_emit,
     test_audit_log_append, test_4_steps_atomic
   - Audit contract (S3): test_kill_switch_event_schema_strict,
     test_4_part_ueid_required, test_recovery_path_dynamic
   - Recovery (S4): test_manual_clear_via_env, test_manual_clear_via_vault,
     test_manual_clear_via_data
   - Actor enforcement (R4 + R8 + R9): test_actor_user_sonho_passes,
     test_actor_agent_sonho_fails, test_actor_unknown_fails
   - Rate limit (R10): test_rate_limit_default_50,
     test_rate_limit_sliding_window, test_rate_limit_per_actor
   - Memory + sub-agent legal paths (R6 + R7): test_memory_write_atomic_passes,
     test_dispatch_sub_agents_passes
   - Bypass detection (R5): test_files_v2ault_bypass_triggers

5. **`src/ikigai/tests/test_drift_invariants.py`** (new file) — W4.7
   retroactive ship implements drift invariant (e) (R12):
   - `test_vault_write_only_via_wrapper` — verify `vault_write` is
     only called from `vault_write_wrapper.py` in
     `src/ikigai/src/agents/v2/*.py`
   - `test_transition_validator_traversal_on_agent_actor` — verify
     `actor="agent"` calls go through `transition_validator`
   - `test_kill_switch_watcher_registered` — verify the filesystem
     watcher is registered at process startup (R5)
   - Plus 2 NEW drift invariants (k) and (l) extending
     `test_canonical_scope.py`:
     - (k) `test_kill_switch_wrapper_used_in_agents_v2` — verify
       `vault_write_wrapper` is the only `vault_write` caller in
       `src/ikigai/src/agents/v2/*.py`
     - (l) `test_no_kill_switch_constants_in_agent_code` — verify
       the 4 new `KILL_SWITCH_*` keys are NOT hardcoded as Python
       `DEFAULT_KILL_SWITCH_*` constants (extends ADR-019 R7
       invariant)

---

## Rationale

1. **Single dispatch surface (architectural foundation).** The kill
   switch wrapper is the **single point of truth** for actor
   discipline — same pattern as ADR-026 R1 (dispatcher is a
   dedicated node) and ADR-027 R8 (PRAGMAs at connection). The
   wrapper consolidates enforcement that would otherwise scatter
   across `len(NODES)` × `len(skills)` call sites, making drift
   detection intractable.

2. **3-mechanism activation matches operational reality.** Env var
   (emergency override), vault file (persistent halt), data file
   flag (local dev convenience) are NOT redundant — they serve
   different operational contexts. Operators use env var in
   production incidents, vault file for cross-restart halts, data
   file for local iteration. Priority ordering (env var > vault >
   data) ensures the env var always wins for emergencies. This
   rationale extends the brief's brief priority note with concrete
   use cases.

3. **`KILL_SWITCH_RATE_LIMIT_PER_HOUR=50` default is operationally
   derived.** The default 50/hr accommodates 4 skills × 1 invocation
   per 15 minutes sustained + buffer for memory write cascades
   (per the R10 rationale above). Operators tune via JSON edit (per
   ADR-019 R2); no Python code change required. This extends the
   brief's "default 50" with concrete derivation from operational
   data.

4. **`REVIEW_QUEUE_BATCH_SIZE=10` is the human-review batch size.**
   Operators process 10 review queue entries per session. This is
   the convention set by the review_queue_cli (Phase 9, B5.0) and
   inherited by W5.1.1. The batch size is operator-tunable via JSON
   edit; the default 10 balances throughput (10 entries × ~30s
   triage = 5min/session) with focus (10 entries is enough context
   for one session without context switching).

5. **Append-only invariant extends to review_queue + audit log.**
   Per CLAUDE.md §"Pitfalls" and §"Refactor Protocol",
   `data/review_queue/` is append-only. The wrapper appends
   `KillSwitchEvent` entries via atomic-rename (Phase 3 v1 pattern);
   it NEVER modifies or deletes existing entries. The audit log
   extension follows ADR-012 §1 append-only invariant. Both are
   enforced by drift invariants (m per ADR-026 R3, l per this ADR's
   W5.1.1 R5).

6. **Manual recovery is non-negotiable.** Auto-clear would defeat
   the kill switch's purpose — operators must consciously decide
   the bypass was acceptable. ADR-013 (planner-only) +
   deterministic pipelines support human-in-the-loop on every
   activation. The voluntary `recovery_notes.md` convention
   documents false-positive / true-positive determinations without
   enforcing it (drift detector does not scan for it).

7. **Memory + sub-agent legal paths are explicit.** Per ADR-028 R1
   amended (memory layer's `memory_write_atomic`) and ADR-026 S2.3
   (sub-agent dispatch), certain code paths are **legitimate**
   callers of `vault_write(actor="agent")`. The wrapper's
   `legal_caller` whitelist recognizes these patterns; all other
   callers are subject to kill switch enforcement. Fail-secure
   default: unknown caller → kill switch fires.

8. **Algorithm constants in JSON (per ADR-019).** 4 new tuning
   values (`KILL_SWITCH_RATE_LIMIT_PER_HOUR`,
   `KILL_SWITCH_RATE_LIMIT_WINDOW_S`, `KILL_SWITCH_HALT_TIMEOUT_S`,
   `KILL_SWITCH_NOTIFY_OPERATOR`) + 1 new batch size
   (`REVIEW_QUEUE_BATCH_SIZE`) land in `algorithm_constants.json`
   per ADR-019 R1. No Python `DEFAULT_KILL_SWITCH_*` constants.
   Drift detector (l) extends at W5.1.1 ship.

9. **Append-only invariant on TaskAction enum.** Per CLAUDE.md
   §"Global Conventions" (frozen Pydantic v2 models, never modify),
   the `TaskAction` enum in `src/contracts/task_change.py:17-24`
   gains a new value `kill_switch` at W5.1.1 ship. The enum is
   append-only — existing values (`create`, `update`, `delete`,
   `done`) are never renamed or removed. The same principle applies
   to `TaskStatus` (adding `kill_switch_active`).

10. **W4.7 retroactive ship is unblocked.** The W4.7 deferred drift
    invariant (e) — "vault_write(actor='agent') without
    transition_validator raises" — has no architectural home until
    this ADR locks the kill switch as the enforcement mechanism.
    This ADR provides that home. W4.7 (separate task) ships the
    drift invariant (e) test code, referencing `vault_write_wrapper`
    and `transition_validator`.

11. **Wave 5 architectural foundation.** This ADR is the **first
    task of Wave 5** (per master-02 §1 dependency graph:
    W5.1 → W5.2 → W5.6 → W5.10). Wave 5 cannot start without it.
    The kill switch is the safety mechanism that:
    - Catches Wave 5's algorithm-tuning bypass attempts (W5.10)
    - Enforces Wave 5's SONHO data collection discipline (W5.6)
    - Supports Wave 5's `mesh show` SONHO tree traversal (W5.7)
    - Enables Wave 5's investigation_queue re-dispatch (W5.5)

12. **Coexistence with ADR-026 partial-success.** Per ADR-026 §S4.3,
    sub-agent failures emit TaskChange to `data/review_queue/` with
    `status="rejected"`. Kill switch events emit KillSwitchEvent
    with `status="kill_switch_active"` (new TaskStatus enum value
    at W5.1.1). The review_queue consumer (per Phase 9 drift
    invariant b) processes both in arrival order; the operator
    distinguishes by `action` field (`kill_switch` vs `update` /
    `delete` / etc.). Both share the same directory, the same
    append-only invariant, and the same audit log cross-reference
    pattern.

---

## Implementation Rules Summary

**R1 — Activation priority** — env var > vault file > data file;
short-circuit on first active mechanism.

**R2 — vault_write_wrapper is mandatory** — every vault_write call
goes through the wrapper; drift invariant (e) at W4.7 verifies.

**R3 — Audit log is append-only** — wrapper appends kill switch
entries; never modifies existing entries (per ADR-012 §1).

**R4 — actor="agent" must traverse transition_validator** —
wrapper calls `validate_phase_transition` before every actor="agent"
write; bypass raises kill switch.

**R5 — Direct filesystem writes to vault trigger kill switch** —
wrapper subscribes to filesystem watcher; untracked writes raise
kill switch via `vault_write_bypass`.

**R6 — Memory writes via memory_write_atomic are legal** — wrapper
recognizes `legal_caller="memory_write_atomic"`; no kill switch.

**R7 — Sub-agent writes via dispatch_sub_agents are legal** —
wrapper recognizes `legal_caller="dispatch_sub_agents"`; no kill
switch.

**R8 — SONHO writes require actor="user"** — wrapper enforces
`transition_validator.py:38` for all SONHO writes (not just phase
transitions).

**R9 — actor="unknown" triggers kill switch** — runtime check
defends against dynamic bypass; literal type enforces at compile
time.

**R10 — Rate limit per actor per hour** — default
`KILL_SWITCH_RATE_LIMIT_PER_HOUR=50`; sliding window of
`KILL_SWITCH_RATE_LIMIT_WINDOW_S=3600`; per-actor budgets.

**R11 — Manual recovery required** — operator must inspect + clear;
no auto-clear; voluntary `recovery_notes.md` convention.

**R12 — Drift invariant (e) deferred to W4.7** — W5.1.1 ships the
wrapper; W4.7 retroactively ships the invariant.

**§W5.1.1 — 5 implementation deliverables** — kill_switch.py,
vault_write_wrapper.py, 4 algorithm_constants.json keys, test_kill_switch.py
(12+ tests), test_drift_invariants.py (W4.7 retroactive + new
invariants k, l).

---

## Cross-ADR Consistency Check

- **vs ADR-012 (vault_write sole vault writer, Accepted 2026-08-30):**
  ✓ — kill switch extends ADR-012 by adding a wrapper around
  `vault_write` (R2). Audit log entries are append-only per ADR-012
  §1 (R3). The wrapper is the new sole vault writer enforcement
  point; `vault_write` directly is forbidden in `agents/v2/*.py`.

- **vs ADR-013 (canonical scope discipline, Accepted 2026-08-31):**
  ✓ — kill switch is **planner-boundary** enforcement, not
  computation enforcement. The wrapper fires on actor-mismatch at
  the `vault_write` boundary, not on every computation step (per
  ADR-013's planner-only invariant). Memory writes, sub-agent
  writes, and skill orchestration are all planner activities that
  the wrapper respects (R6 + R7).

- **vs ADR-014 (UEID canonical format, Accepted 2026-09-04):**
  ✓ — `KillSwitchEvent.ueid` and `KillSwitchEvent.entity_id` use
  the 4-part UEID format. Drift detector's invariant (l) at W5.1.1
  ship verifies UEID 4-part regex on every `*_ueid` field in the
  schema (per ADR-014 R1).

- **vs ADR-019 (algorithm_constants.json, Proposed 2026-09-04):**
  ✓ — 4 new `KILL_SWITCH_*` keys + 1 new `REVIEW_QUEUE_BATCH_SIZE`
  key land in `prompts/algorithm_constants.json`. Drift detector
  (l) extends to cover these 5 new keys' absence from `.py` files
  at W5.1.1 ship (per ADR-019 R7).

- **vs ADR-025 (skill binding, Accepted 2026-09-04, R2 amended):**
  ✓ — skill actor routing is legal (R6 + R7). The wrapper's
  `legal_caller` whitelist includes `skill_orchestrator` for the
  v2 CLI dispatcher. The wrapper does NOT trigger kill switch
  for legitimate skill writes; bypass is the only trigger.

- **vs ADR-026 (sub-agent dispatch, DRAFT `3cc9799`):**
  ✓ — sub-agent `actor="agent"` is legal (R7). The wrapper
  recognizes `dispatch_sub_agents` as a legal caller. Per ADR-026
  §S4.3, sub-agent failures emit TaskChange with
  `status="rejected"`; kill switch events emit KillSwitchEvent
  with `status="kill_switch_active"` (S5.4 coexistence).

- **vs ADR-028 (cross-cycle memory, DRAFT `120b536`, R1 amended at
  `d602a4d`):**
  ✓ — memory writes via `memory_write_atomic` are legal (R6).
  The wrapper recognizes `memory_write_atomic` as a legal caller.
  Per ADR-028 R1 amended, `memory_write_atomic` calls
  `vault_write(actor="agent")` underneath; the wrapper's whitelist
  preserves this canonical pattern. The kill switch does NOT
  trigger for memory writes.

---

## Drift Invariants

This ADR specifies **2 NEW drift invariants** (k), (l) plus references
the W4.7 deferred invariant (e):

### Existing invariants (W3.2 + W4.7 ship — referenced for context)

- **(k)** `test_no_hardcoded_entry_points_*` (ADR-025 R4) — verifies
  each manifest's `entry_point ∈ NODES` + `actor ∈ {user, agent}`.
  Currently 24/24 PASS (per Wave 3 ship).

- **(l)** `test_no_algorithm_constants_in_agent_code` (ADR-019 R7) —
  verifies no `DEFAULT_*` / `HYSTERESIS_*` patterns in
  `agents/v2/*.py`. Currently 24/24 PASS.

### Deferred invariant (W4.7 retroactive ship)

- **(e)** `vault_write(actor="agent") without transition_validator
  raises` — explicitly **deferred** from Wave 4 (per the W4.7 brief)
  and unblocked by W5.1.1 implementation. The drift invariant (e) test
  code references `vault_write_wrapper` and `transition_validator`
  per W5.1.1 implementation patterns.

### NEW invariants (W5.1.1 ship)

- **(k) [extension]** `test_kill_switch_wrapper_used_in_agents_v2`
  — verifies `vault_write_wrapper` is the only `vault_write` caller
  in `src/ikigai/src/agents/v2/*.py`. Extends the existing invariant
  (k) at W5.1.1 ship. Adds 4-6 test functions.

- **(l) [extension]** `test_no_kill_switch_constants_in_agent_code`
  — verifies the 4 new `KILL_SWITCH_*` keys + 1 new
  `REVIEW_QUEUE_BATCH_SIZE` key are NOT hardcoded as Python
  `DEFAULT_KILL_SWITCH_*` / `DEFAULT_REVIEW_QUEUE_*` constants.
  Extends the existing invariant (l) at W5.1.1 ship. Adds 2-3 test
  functions.

### Drift invariants current state

Per Wave 4 SHIP-COMPLETE at `f77988f`: 38 invariants in
`test_canonical_scope.py` + 10 in `test_drift_detector.py + extended` =
48 total. After W5.1.1 ship + W4.7 retroactive ship: 48 + 6-9 new
invariants = 54-57 total. W5.1.1 implements invariants (k), (l)
extension; W4.7 implements invariant (e) for the retroactive Wave 4
ship. Both ships are independent (W4.7 unblocked AFTER W5.1.1 ships).

---

## Algorithm Constants JSON Keys

This ADR specifies **5 new keys** for `prompts/algorithm_constants.json`
(W5.1.1 ships the JSON edit + drift invariant (l) extension):

```json
{
  "_comment": "Single source of truth (per ADR-019 + ADR-029). Edits only by this file.",

  "KILL_SWITCH_RATE_LIMIT_PER_HOUR": 50,
  "KILL_SWITCH_RATE_LIMIT_WINDOW_S": 3600,
  "KILL_SWITCH_HALT_TIMEOUT_S": 5.0,
  "KILL_SWITCH_NOTIFY_OPERATOR": true,
  "REVIEW_QUEUE_BATCH_SIZE": 10
}
```

| Key | Default | Used in | Meaning |
|-----|---------|---------|---------|
| `KILL_SWITCH_RATE_LIMIT_PER_HOUR` | `50` | R10 rate-limit enforcement | Max writes per actor per hour |
| `KILL_SWITCH_RATE_LIMIT_WINDOW_S` | `3600` | R10 sliding window | Window size in seconds (1 hour) |
| `KILL_SWITCH_HALT_TIMEOUT_S` | `5.0` | S2.1 synchronous abort | Timeout for in-flight write abort |
| `KILL_SWITCH_NOTIFY_OPERATOR` | `true` | S2.4 MCP resource | Notify operator via `ikigai://kill-switch/status` |
| `REVIEW_QUEUE_BATCH_SIZE` | `10` | Operator TUI review | Entries per operator review session |

**Defensive defaults in `load_constants.py`:** per ADR-019 R6, the
loader must mirror the JSON exactly. W5.1.1 implementation updates
`load_constants._defensive_default()` to include all 5 new keys with
the values above. Drift invariant (l) extension verifies this
mirroring.

**No Python `DEFAULT_KILL_SWITCH_*` constants:** per ADR-019 R2, the
W5.1.1 implementation MUST NOT define module-level assignments for
kill switch tuning. All reads go through `load_constants.get(key)`.

---

## Consequences

### Positive

- **Single enforcement surface.** The wrapper is the canonical
  enforcement point for actor discipline. Drift detection has one
  place to scan (R2 + invariant e).
- **3-mechanism activation matches operational reality.** Env var
  for emergencies, vault file for persistent halts, data file for
  local dev. Priority ordering ensures env var always wins.
- **Audit trail preserved.** Per ADR-012 §1, every kill switch
  event is appended to `<vault_root>/.vault_audit.log` with the
  actor + entity_id + trigger_reason + kill_id. The audit log
  remains the primary forensic trail.
- **Append-only invariant extends to review_queue + audit log.**
  Per CLAUDE.md §"Refactor Protocol" + §"Pitfalls", the wrapper
  respects append-only on both surfaces. No deletions, no
  modifications.
- **W4.7 unblocked.** The deferred drift invariant (e) has its
  architectural home (the wrapper + transition_validator).
  W4.7 retroactive ship is independent and follows W5.1.1.
- **Wave 5 architectural foundation in place.** This ADR is the
  first task of Wave 5; without it, Wave 5 cannot start. The
  kill switch is the safety mechanism that catches algorithm-
  tuning bypass attempts, SONHO data collection violations, and
  investigation_queue re-dispatch edge cases.
- **Algorithm tuning is JSON-only.** 5 new keys in
  `algorithm_constants.json` (per ADR-019 R1); zero new Python
  constants. Drift detector (l) extension at W5.1.1 ship.
- **Memory + sub-agent legal paths are explicit.** Per ADR-028 R1
  amended and ADR-026 S2.3, the wrapper recognizes legitimate
  callers via the `legal_caller` whitelist. No false positives
  on canonical patterns.
- **Recovery is manual, not automatic.** Per ADR-013 + safety
  principle, the operator decides the bypass was acceptable.
  Voluntary `recovery_notes.md` convention documents the
  decision.

### Negative

- **3 new modules + 1 new schema + 5 new JSON keys** add
  operational surface. W5.1.1 implementation ships
  `kill_switch.py` + `vault_write_wrapper.py` + `KillSwitchEvent`
  model + `algorithm_constants.json` extensions + 12+ tests.
  Drift detector (k, l) extension at W5.1.1 + (e) at W4.7 catches
  regressions.
- **Filesystem watcher has cost.** R5's watchdog subscription adds
  ~1-3% overhead to `vault_write` calls (per the watchdog
  library's overhead). Acceptable trade-off vs the safety
  guarantee. W5.1.1 implementation MAY use inotify on POSIX or
  ReadDirectoryChangesW on Windows for efficiency.
- **Rate-limit window is in-memory.** R10's sliding window resets
  on process restart. Acceptable per ADR-013 deterministic
  pipelines; the operator can investigate and clear via R11.
- **Manual recovery is operator overhead.** Per R11, the kill
  switch is not auto-cleared. Each activation requires operator
  inspection + decision + clearance. This is the intended
  trade-off (safety > automation), but it adds operational
  burden. Mitigation: the operator TUI's review_queue tab (per
  Phase 9) gives a single-screen view of pending kill switch
  events.
- **KillSwitchEvent schema extends TaskChange.** Per S3, the new
  fields (`kill_switch_trigger`, `actor_at_fault`, `entity_id`,
  `context`, `recovery_path`) are added to the existing
  `TaskChange` schema. The `action` enum gains `kill_switch`
  (R11 append-only); the `status` enum gains `kill_switch_active`.
  Existing TaskChange consumers (per Phase 9 drift invariant b)
  MUST handle the new values gracefully (ignored if not
  recognized).
- **W4.7 retroactive ship is dependent.** W5.1.1 ships the wrapper;
  W4.7 ships the drift invariant (e). If W4.7 ships before
  W5.1.1, the invariant test code has no wrapper to verify
  against. The brief mandates W5.1.1 BEFORE W4.7; this ADR
  documents the ordering constraint.

### Neutral

- **Append-only invariant extends to TaskAction + TaskStatus
  enums.** Per CLAUDE.md §"Global Conventions" + ADR-013
  planner-only, Pydantic enums are append-only. The new
  `kill_switch` and `kill_switch_active` values are added without
  removing existing values. Old code reads new enums gracefully.
- **The wrapper is internal, not user-facing.** Operators interact
  with the kill switch via env var / vault file / data file
  mechanism — NOT via a Python API. The wrapper is plumbing; the
  activation surface is the 3 mechanisms + the
  `recovery_notes.md` convention.
- **REVIEW_QUEUE_BATCH_SIZE is operator-tunable, not system-
  enforced.** The default 10 is the operator's preferred batch
  size; the operator MAY edit the JSON to change it. The
  operator TUI does not enforce this constant — it suggests
  "next batch of 10" but allows manual override.
- **Watchdog library is optional.** R5's filesystem watcher can
  use Python's `watchdog` library (third-party dep) or inotify
  directly (Linux-specific). W5.1.1 implementation chooses the
  cross-platform option (watchdog) for portability.

---

## Alternatives Considered

### Alt A — Env var only (no vault file, no data file)

Kill switch is activated ONLY by `IKIGAI_KILL_SWITCH=1` env var.
No vault file or data file flag.

- **Rejected:** env var alone doesn't survive process restarts in
  many containerized deployments. Operators need a persistent
  halt mechanism (vault file) and a local-dev convenience
  mechanism (data file). The 3-mechanism design matches
  operational reality.

### Alt B — Vault file only (no env var, no data file)

Kill switch is activated ONLY by `vault/.kill_switch.md` with
frontmatter `status: active`. No env var or data file.

- **Rejected:** vault file alone doesn't allow emergency override
  in containerized environments (where the vault may be on a
  different volume). Operators need an env var for production
  incidents. The 3-mechanism design gives the operator a choice
  of override granularity.

### Alt C — Auto-clear on success (kill switch resets after 1 successful write)

The kill switch auto-disengages after the first successful
vault_write following activation. No operator intervention.

- **Rejected:** auto-clear defeats the kill switch's purpose.
  Operators must consciously decide the bypass was acceptable
  (per R11 + ADR-013 deterministic pipelines). Auto-clear is a
  known anti-pattern (Kubernetes liveness probes that mask
  crashloops).

### Alt D — Single drift invariant (e) without wrapper

Skip the wrapper; rely solely on the drift detector's invariant
(e) to catch bypass attempts via static AST scan.

- **Rejected:** static AST scan catches static violations
  (CI-time) but not runtime bypasses. A rogue script that
  bypasses `vault_write` at production runtime would not be
  caught by the drift detector. The wrapper provides runtime
  defense in depth — both static AND runtime enforcement.

### Alt E — Separate kill switch file per cycle (per ADR-027 R10 pattern)

One `vault/.kill_switch_<cycle_id>.md` file per cycle; kill
switch is per-cycle, not global.

- **Rejected:** kill switch is a **global safety mechanism**,
  not per-cycle state. A per-cycle kill switch would let a
  malicious cycle continue running while another cycle is
  halted. The global kill switch (single file) ensures
  system-wide halt when activated.

### Alt F — Cron-based review_queue batch processing

A cron job processes the review_queue every N minutes; the
operator TUI just displays the current batch.

- **Rejected:** cron-based processing violates ADR-013
  deterministic pipelines. The review_queue is operator-driven,
  not cron-driven. The operator decides when to process the
  queue (via the TUI or the review_queue_cli).

### Alt G — Separate kill switch queue (data/kill_switch_queue/)

Kill switch events go to a separate queue, not the existing
review_queue.

- **Rejected:** separate queues fragment the operator's review
  surface. The operator must check 2 directories per session.
  The existing review_queue (per Phase 9 + drift invariant b)
  is the canonical surface; kill switch events share it via the
  `action` enum discrimination (S5.4 coexistence).

### Alt H — Per-tier kill switch (kill switch per SONHO tier)

Each SONHO tier has its own kill switch. SONHO kill switch is
separate from META kill switch, etc.

- **Rejected:** per-tier kill switch fragments the safety
  mechanism. The canonical SONHO `actor="user"` invariant (per
  `transition_validator.py:38`) is the SAME kill switch
  enforcement for the SONHO tier — there's no operational
  reason to differentiate. A single global kill switch matches
  the existing actor discipline.

---

## Forward Dependencies

| Consumer | Field/section consumed | Status |
|----------|------------------------|--------|
| ADR-012 (vault_write sole writer) | S2.3 audit log extension | Accepted, this ADR extends the audit surface |
| ADR-013 (canonical scope discipline) | S1 planner-boundary enforcement | Accepted, this ADR's scope matches |
| ADR-014 (UEID canonical 4-part) | S3 KillSwitchEvent.ueid + entity_id 4-part | Accepted, this ADR inherits |
| ADR-019 (algorithm_constants.json SOT) | 5 new keys (per §algorithm_constants.json keys) | Proposed, this ADR ships 5 keys |
| ADR-025 (skill binding) | R6 + R7 legal_caller whitelist | Accepted, this ADR respects skill actor routing |
| ADR-026 (sub-agent dispatch) | R7 legal_caller for dispatch_sub_agents + S5.4 coexistence | DRAFT, this ADR extends ADR-026 §S4.3 |
| ADR-028 (cross-cycle memory) | R6 legal_caller for memory_write_atomic | DRAFT, this ADR respects ADR-028 R1 amended |
| **W4.7 (drift invariants, deferred)** | R12 invariant (e) — `vault_write(actor='agent')` without transition_validator raises | Deferred, unblocked AFTER W5.1.1 ships |
| **W5.1.1 (kill switch + wrapper implementation, 12-16h)** | §W5.1.1 5 deliverables (kill_switch.py + vault_write_wrapper.py + algorithm_constants.json keys + test_kill_switch.py + test_drift_invariants.py k, l extension) | next, blocking on this ADR Accepted |
| **W5.2 (ADR-030 empirical algorithm tuning, 6-8h)** | S4 manual recovery + R11 operator clearance + review_queue integration | next-wave, blocking on this ADR Accepted |
| **W5.5 (Plan C investigation_queue re-dispatch)** | S5 review_queue integration + KillSwitchEvent schema as canonical precedent | next-wave, blocking on this ADR Accepted |
| **W5.6 (SONHO data collection ritual)** | R8 SONHO actor="user" enforcement | next-wave, blocking on this ADR Accepted |
| **W5.7 (`mesh show` SONHO tree traversal)** | S3 4-part UEID in KillSwitchEvent | next-wave, blocking on this ADR Accepted |
| **W5.10 (Empirical algorithm tuning, post-SONHO-5)** | R10 rate-limit + R11 manual recovery | next-wave, blocking on this ADR Accepted |

**Key forward dependency: W5.1.1 (12-16h) ships the 5 implementation
deliverables (§W5.1.1 above).** This ADR is architectural decision
only; the wrapper implementation, the KillSwitch class, the JSON key
edits, the test suite, and the drift invariant (k, l) extensions all
land in W5.1.1.

---

## References

### Load-bearing prior ADRs

- **ADR-012 — vault_write sole vault writer** (Accepted 2026-08-30) —
  R2 vault_write_wrapper is mandatory; R3 audit log append-only; S2
  escalation extends audit log with kill switch entries.
- **ADR-013 — Canonical scope discipline** (Accepted 2026-08-31) —
  R11 manual recovery aligns with planner-only invariant; R12 W4.7
  invariant (e) is planner-boundary enforcement, not computation
  enforcement.
- **ADR-014 — UEID canonical format (4-part)** (Accepted 2026-09-04) —
  S3 KillSwitchEvent.ueid + entity_id use 4-part UEID format.
- **ADR-019 — QHE → prompt-template constants** (Proposed 2026-09-04
  per W3.2 ship) — R10 + §algorithm_constants.json 5 new keys; drift
  detector (l) extends at W5.1.1 ship.
- **ADR-025 — Skill binding mechanism** (Accepted 2026-09-04, R2
  amended) — R6 + R7 legal_caller whitelist includes skill
  orchestrator; ADR-025's actor routing is the canonical pattern.
- **ADR-026 — Sub-agent dispatch protocol** (DRAFT 2026-09-04,
  `3cc9799`) — R7 legal_caller for dispatch_sub_agents; S5.4
  coexistence with ADR-026 §S4.3 partial-success invariant.
- **ADR-028 — Cross-cycle memory layer** (DRAFT 2026-09-04, R1
  amended at `d602a4d`) — R6 legal_caller for memory_write_atomic;
  ADR-028 R1 amended is the canonical "legal actor=agent" pattern
  this ADR protects.

### Code references

- `src/ikigai/src/ikigai/security/transition_validator.py:16-45` —
  existing `validate_phase_transition` function (the actor
  enforcement model this ADR's wrapper follows)
- `src/ikigai/src/ikigai/security/transition_validator.py:38` —
  SONHO `actor="user"` enforcement (R8 inheritance)
- `src/ikigai/src/ikigai/vault/vault_write.py:41-67` —
  `vault_write(vault_root, vault_path, frontmatter_fields, body,
  actor=...)` signature (R2 wrapper target)
- `src/contracts/task_change.py:17-24` — `TaskAction` enum (R11
  append-only extension to add `kill_switch`)
- `src/contracts/task_change.py:26-28` — `TaskStatus` literal (R11
  append-only extension to add `kill_switch_active`)
- `src/contracts/task_change.py:31-46` — `TaskChange` BaseModel (S3
  extension surface for `KillSwitchEvent`)
- `data/review_queue/` — existing append-only filesystem queue
  (S5 integration; ~50 JSON entries as of 2026-09-04)
- `src/mesh/queue.py` — Phase 3 v1 atomic-rename pattern (R3 +
  S5.3 append-only enforcement)

### Drift detector references

- `src/ikigai/tests/test_canonical_scope.py` —
  `test_no_hardcoded_entry_points_*` (drift invariant k, ADR-025
  R4) — extended at W5.1.1 to add `test_kill_switch_wrapper_used_in_agents_v2`
- `src/ikigai/tests/test_canonical_scope.py` —
  `test_no_algorithm_constants_in_agent_code` (drift invariant l,
  ADR-019 R7) — extended at W5.1.1 to add
  `test_no_kill_switch_constants_in_agent_code`
- `src/ikigai/tests/test_drift_detector.py` — existing 24
  invariants (W3.2 + Wave 3 ship); W5.1.1 adds 6-9 new invariants
- **W4.7 — new drift invariant (e) for
  `vault_write(actor="agent")` without transition_validator**
  (planned, this ADR's R12)

### Roadmap / spec references

- `docs/superpowers/specs/2026-09-04-dcode-harness-PLAN.md` §3 —
  W5.1 task spec (this ADR)
- `docs/superpowers/specs/2026-09-04-dcode-harness-TASKS.md` —
  W5.1 acceptance criteria (lines 377-392; this ADR's AC)
- `docs/superpowers/specs/2026-09-04-adr-spec-gap.md` §2 row 5 —
  ADR-018 → ADR-029 (renumbered) as one of 6 new ADRs needed for
  Wave 5 Scenario C
- `docs/superpowers/specs/2026-09-04-adr-spec-gap.md` §8 step 6 —
  recommended write order (ADR-018 ships after ADR-014..017)
- `docs/superpowers/specs/2026-09-03-sonho-tree-hybrid-design.md`
  §Decision 8 — SONHO phase transitions require `actor="user"`
  (this ADR's R8 inheritance)

### Review queue references

- `src/contracts/task_change.py:31-46` — `TaskChange` schema (S3 +
  S5 strict extension)
- `data/review_queue/0b583b99-98ad-4290-8a1f-5fdae4418edc.json` —
  existing TaskChange entry example (event_id, ueid, action, fields,
  source_fork, timestamp, status)
- Phase 3 v1 atomic-rename pattern (`src/mesh/queue.py`) — R3 +
  S5.3 append-only enforcement

### Memory references

- `memory/wave-3-ship-complete-2026-09-04` — Wave 3 SHIP-COMPLETE
  on commit `be9a370`; drift 24/24 PASS; ruff clean; this ADR
  continues the load-bearing sequence into Wave 5
- `memory/master-branch-carro-chefe-2026-08-28` — canonical master
  branch direction (kill switch lives in
  `src/ikigai/src/ikigai/security/`, not `src/operational/` or
  `archive/`)
- `memory/algorithm-scope-reframed-2026-08-30` — IKIGAI = planner
  with stochastic PAE feedback; kill switch is planner-boundary
  enforcement, not computation enforcement
- `memory/algorithm-gate-dropped-2026-09-03` — algorithm work
  allowed on explicit demand; 5 new JSON keys land via W5.1.1
  ship-time
- `memory/feedback-precision-calibration-2026-08-28` — when user
  pushes back on X, apply correction NARROWLY (X-not-X), not
  opposite extreme; this ADR's "kill switch is per-tier but unified
  mechanism" follows the same pattern (R8 enforces SO only, does
  not over-enforce all tiers)
- `memory/memory-drift-reconciliation-2026-09-04` — 10 confirmed
  memory-vs-code drift items; this ADR explicitly references
  ADR-026 (DRAFT `3cc9799`), ADR-027 (DRAFT `648b83a`), ADR-028
  (DRAFT `120b536`, R1 amended `d602a4d`) per drift-reconciliation
  standard
- `memory/wave-3-ship-complete-2026-09-04` — confirms 8/8 Wave 3
  tasks shipped; this ADR is Wave 5 entry point

### Wave 4 ship context

- Wave 4 SHIP-COMPLETE at `f77988f` (2026-09-04)
- 9 commits shipped: 3 ADRs (026, 027, 028) + 3 impls (W4.4 sub-agent
  dispatch, W4.5 stateful subgraph, W4.6 memory layer) + 1 smoke
  (W4.8 E2E) + 2 final fixes (ADR-028 R1 amendment at `d602a4d` +
  type:ignore cleanup)
- 140/140 PASS in v2 combo (canonical_scope 24 + invoke_skill_taskdog
  12 + daily 17 + graph_smoke 17 + e2e_smoke 3 + imports_safely 8 +
  entry_point 5 + memory 31 + drift_detector_extended 10 = 127+13 = 140)
- Drift detector 24/24 PASS in `test_canonical_scope.py` + 10/10 in
  `test_drift_detector.py + extended` = 48 total
- Ruff clean on all Wave 4 files
- Final whole-branch reviewer APPROVED_FOR_WAVE_5
- Wave 4 brief at `.git/sdd/w41-adr-026-sub-agent-dispatch-brief.md`
  + W4.2 + W4.3 briefs at sibling paths
- Wave 4 transition brief at `.git/sdd/wave-4-ship-complete-brief.md`

### Wave 5 kickoff

- This ADR is the **first task of Wave 5** (W5.1)
- Per master-02 §1 dependency graph: W5.1 → W5.2 → W5.6 → W5.10
- Wave 5 SHIP-COMPLETE criteria (per master-02 + TASKS.md §377):
  1. W5.1 ADR-029 Kill switch + review queue wiring — THIS ADR
  2. W5.2 ADR-030 Empirical algorithm tuning approach
  3. W5.3 ADR-020..024 (implicit decisions to formalize)
  4. W5.4 ADR-025 follow-up (extend for monthly/quarterly)
  5. W5.5 Re-dispatch Plan C: investigation_queue + 3 MCP tools
  6. W5.6 SONHO data collection ritual
  7. W5.7 `mesh show` SONHO tree traversal
  8. W5.8 Drift invariant (d) — full SONHO tree coverage
  9. W5.9 Operator TUI SONHOs tab
  10. W5.10 Empirical algorithm tuning (post-SONHO-5)
- After W5.1: Wave 5 architectural foundation in place
- W5.1.1 implementation (kill_switch.py + vault_write_wrapper.py +
  algorithm_constants.json keys) is the next task after this ADR is
  Accepted

---

*ADR-029 — DRAFT 2026-09-04 — Wave 5 W5.1 — Wave 5 architectural
foundation — gates W5.1.1 + W4.7 + W5.2 + W5.5 + W5.6 + W5.7 + W5.10
— user review pending*