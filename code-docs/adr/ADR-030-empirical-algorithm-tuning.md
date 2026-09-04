# ADR-030 — Empirical Algorithm Tuning Approach

> **Status:** DRAFT (2026-09-04)
> **Deciders:** matheus (project owner)
> **Load-bearing:** YES — gates W5.6 (SONHO data collection ritual) + W5.10 (algorithm tuning, 4-8 weeks) + future algorithm-tuning iterations after the dcode-harness roadmap completes
> **Supersedes:** none (new decision; extends ADR-019 prompt-template pattern into a general policy)
> **Renumbered from:** PLAN §3 "ADR-019 (empirical algorithm tuning)" — user decision 2026-09-04 ("Renumber to 026+") supersedes PLAN numbering. Existing ADR-019 (W3.2 commit `1ef638c`) = QHE constants → prompt-template; this ADR-030 is the umbrella policy. Ships as **ADR-030**.
> **Wave:** dcode-harness roadmap Wave 5 (W5.2)
> **Wave 5.1 context:** SHIP-COMPLETE at `59dd445` (2026-09-04); W5.1 ADR-029 ACCEPTED + W5.1.1 implementation shipped (kill_switch + vault_write_wrapper + 5 algorithm_constants.json keys + drift invariant e retroactive)
> **Related code:** `src/ikigai/src/agents/v2/nodes/observe.py:44-58` (the inline-default loophole this ADR closes), `src/ikigai/src/agents/v2/prompts/algorithm_constants.json` (SOT pattern from ADR-019), `src/ikigai/src/agents/v2/prompts/load_constants.py` (loader)
> **Related memories:** `algorithm-scope-reframed-2026-08-30`, `algorithm-gate-dropped-2026-09-03`, `algorithm-decisions-defer-2026-08-28`, `algorithm-issues-registry`

---

## Length Note

This ADR lands at ~700 lines (target 500-700 per the brief). Justification:
8 R-rules + 5 F-phases + cross-ADR consistency table (5 ADRs) + drift
invariant (m) + 2 implementation specs (W5.6 + W5.10) + 4 memory
references + 5 ADR references. Smaller than ADR-029 (1481 lines) because
the feedback loop is policy-only, not contract-heavy (no S1-S5 contracts).
Larger than ADR-019 (399 lines) because it generalizes that pattern into
8 rules + 5 phases. ADR-027 (931 lines) and ADR-028 (1072 lines) set the
precedent that load-bearing Wave 4/5 ADRs may exceed 500 lines with
justification (CLAUDE.md §"Build & Test"). No auto-split — splitting
would force W5.6 + W5.10 implementers to cross-reference 2+ files, which
ADR-013 forbids.

---

## Context

Algorithm tuning in the IKIGAI v2 graph has undergone **3 reversals + 1 drop
decision** in 4 weeks (2026-07-02 → 2026-09-03):

1. **2026-07-02** — `algorithm-issues-registry.md` catalogued 31 inconsistencies.
   Resolution deferred pending user decisions on N01/A02/D02.
2. **2026-08-28** — `algorithm-decisions-defer-2026-08-28.md` documented the
   user's **3rd reversal** on M01/N01/A02/A06. Canonical framework emerged:
   reversibility + telemetry + day-to-day conflicts.
3. **2026-08-30** — `algorithm-scope-reframed-2026-08-30.md` reframed the 6
   open questions: **3 OUT OF IKIGAI SCOPE** (PAV desativated per attribution
   §3), **2 OUT OF BACKEND SCOPE** (prompt-template), **1 IN SCOPE**.
4. **2026-09-03** — `algorithm-gate-dropped-2026-09-03.md` user verbatim:
   *"fuck off algorithm"*. **Algorithm gate dropped**; work allowed on
   explicit demand; PAV math stays archived.

The dcode-harness roadmap is the **explicit demand framework** for future
algorithm work. Wave 5 Scenario C includes W5.10 (empirical algorithm tuning,
4-8 weeks) — the first canonical tuning procedure since the gate dropped.

ADR-019 (W3.2, `1ef638c`) established that QHE constants live in
`algorithm_constants.json`, not Python `DEFAULT_*`. ADR-019 is **the pattern**
but not **the policy** — it codifies JSON SOT for one scenario. Missing is
the **general feedback loop policy**: how does the operator identify tuning
opportunities? How are SONHO logs evidence? What's the cadence? What's the
safety net?

The **loophole this ADR closes**: `src/ikigai/src/agents/v2/nodes/observe.py:44, 58`
contains inline numeric defaults (`qhe_obs.get("q_he", 0.65)` and
`max(capacity_estimate, 1.0)`) that bypass the JSON SOT. These are not
hardcoded `DEFAULT_*` constants, so drift invariant (l) at
`test_canonical_scope.py` does not catch them — it scans module-level
assignments, not inline literals. ADR-030's drift invariant (m) extends the
scanner to catch inline numeric thresholds matching migrated ranges
(0.85, 0.60, 1.20, 0.50, 8.0, etc.).

W5.1 (ADR-029) shipped the **kill switch** as the safety mechanism for
manual override during tuning. W5.2 codifies the **feedback loop policy**.
W5.6 (SONHO data collection) + W5.10 (tuning procedure) are downstream
consumers.

This ADR is **architectural decision only** — no code changes ship in W5.2.
W5.6 ships `/sonho-log`; W5.10 ships the iterative procedure + observe.py
refactor as the first cadence iteration.

---

## Decision

**Algorithm tuning happens via prompt-template iteration ONLY**, gated by
SONHO logs (W5.6) + kill switch safety (ADR-029) + drift verification
(ADR-019 R7 + new invariant m). No Python `DEFAULT_*` constants added in
agent code. No new IKIGAI_TOOLS (count stays at 12 per ADR-013).

The empirical feedback loop has **5 phases** (§F1-F5) and **8 enforcement
rules** (§R1-R8). Algorithm tuning iterations are **explicit demand** — they
require SONHO log evidence + operator review + drift verification. The kill
switch (ADR-029) provides the safety net for unexpected behavior.

### Algorithm tuning surface

| Surface | File | Example edit | Per ADR |
|---------|------|--------------|---------|
| Algorithm constants | `prompts/algorithm_constants.json` | `QHE_PUSH_THRESHOLD: 0.85 → 0.87` | ADR-019 R1 |
| Prompt-template text | `prompts/*.md` | Edit `observe.md` Decision Rules section | ADR-019 + this ADR |
| Kill switch rate limit | `algorithm_constants.json` | `KILL_SWITCH_RATE_LIMIT_PER_HOUR: 50 → 100` | ADR-029 R10 |
| Drift invariant registry | `test_canonical_scope.py` | Add new test function | ADR-019 R7 |

| Forbidden surface | Reason |
|-------------------|--------|
| `agents/v2/*.py` module-level `DEFAULT_*` assignments | ADR-019 R2 + ADR-013 |
| `agents/v2/nodes/*.py` inline numeric thresholds matching migrated ranges | This ADR (R1) + new invariant (m) |
| `src/ikigai/src/agents/tools.py` IKIGAI_TOOLS list (count = 12) | ADR-013 + ADR-019 R7 |
| `src/contracts/*.py` schema modifications | Append-only invariant + CLAUDE.md §"Pitfalls" |
| `archive/legacy-pav/src-operational/` PAV math | PAV desativated per attribution §3 |
| `src/ikigai/src/agents/v2/state.py` DEFAULT_* constants | Pre-W3.2 regression forbidden by ADR-019 |

### Empirical feedback loop phases

The 5 phases (§F1-F5) form the canonical algorithm-tuning iteration cycle.
Each iteration runs **at most 1 prompt-template update per week** (R4).

---

## §F1 — SONHO logging phase

Operator runs `/sonho-log` (W5.6) after each `dcode daily` invocation.
Appends to `vault/ikigai/closing-2026/01-q3-2026/04-relatórios-diários/sonho-YYYY-MM-DD-N.md`.

**Log template (4 fields):** Dream / Observation / Gap / Action — one sentence each.

**Drift invariant:** Each log MUST have all 4 fields
(`test_sonho_log_template_complete`, W5.6 ship). 5+ SONHO logs → unblocks W5.10.
Pre-flight: directory exists, 0 files as of 2026-09-04.

---

## §F2 — prompt-template iteration phase

Operator reviews 5+ SONHO logs for patterns: (1) recurring observations —
same gap in 3+ logs; (2) action divergence — actions cluster on a single
tuning surface; (3) quantitative signals — metric drift (Q_HE regime
misaligned with workload reality).

**Tuning target selection:**

| Pattern type | Tuning target | File |
|--------------|---------------|------|
| QHE threshold misalignment | `QHE_PUSH_THRESHOLD` / `QHE_RECOVER_THRESHOLD` | `algorithm_constants.json` |
| Regime FSM transition issue | `observe.md` Decision Rules | `prompts/observe.md` |
| Workload balancer false positives | `WORKLOAD_OVERLOAD_FACTOR` / `_UNDERLOAD_FACTOR` | `algorithm_constants.json` |
| Heuristic deviation off | `HEURISTICS_H2_DEVIATION_WARN` etc. | `algorithm_constants.json` |
| Rate limit too aggressive | `KILL_SWITCH_RATE_LIMIT_PER_HOUR` | `algorithm_constants.json` (ADR-029 R10) |

**Constraint:** NO Python `DEFAULT_*` constants. NO inline numeric thresholds
matching migrated ranges in `nodes/*.py`. All numeric edits via `algorithm_constants.json` SOT (ADR-019 R1).

---

## §F3 — drift verification phase

After each prompt-template update, run drift detector. Required passes:

- **(a)** `test_ikigai_tools_count_is_12`
- **(b)** `test_review_queue_append_only`
- **(c)** `test_load_constants_*`
- **(e)** `test_vault_write_only_via_wrapper`
- **(k)** `test_no_hardcoded_entry_points_*`
- **(l)** `test_no_algorithm_constants_in_agent_code` + subagent + memory + kill switch extensions
- **(m) NEW** `test_no_inline_thresholds_in_node_bodies` — closes observe.py:44, 58 loophole

If any invariant fails, **revert the iteration** (R5). Regression tests
must also pass: `test_algorithm_constants_migration.py` + `test_kill_switch.py`
+ `test_drift_invariants.py` + `test_canonical_scope.py` (current 24+
invariants).

---

## §F4 — kill switch safety phase

If a tuning iteration causes unexpected behavior (runaway writes, regime
misclassification, audit log corruption), kill switch (ADR-029) fires via:
R4 `actor_mismatch`, R10 `rate_limit_exceeded`, R5 `vault_write_bypass`.

**Operator response (per ADR-029 S4):** (1) inspect
`data/review_queue/<timestamp>-<kill_id>.json`; (2) read `recovery_path`;
(3) verify false-positive (legitimate tuning) vs true-positive (rogue
iteration); (4) clear the kill switch via the activating mechanism
(unset env var / edit vault file / `rm data/.kill_switch`); (5) MAY append
`recovery_notes.md` documenting the determination.

**Tuning iteration rollback:** if the iteration caused the unexpected
behavior, **revert the JSON edit** (R5). SONHO log evidence preserved for
future re-attempt.

---

## §F5 — human review phase

Each prompt-template change references the SONHO log evidence in the
commit message (R3, `W5.10 AC4`):

```
docs(adr): W5.10 — tune QHE_PUSH_THRESHOLD based on SONHO logs

- SONHO evidence: vault/.../sonho-2026-XX-XX-N.md
  - Dream: ...  - Observation: ...  - Gap: ...  - Action: tune QHE_PUSH_THRESHOLD 0.85 → 0.87
- Drift verification: 24/24 PASS (a-l)
- Kill switch: inactive
- Operator review: APPROVED
```

**Operator TUI surface** (W5.9 deliverable): SONHOs tab provides visual
review of pending SONHO logs. Out of scope for this ADR.

**Acceptance gate:** Each tuning iteration is **APPROVED** by the operator
before counting as evidence for the next iteration. Unapproved iterations are
reverted per R5.

---

## §R1 — No new Python constants in agent code

**Rule:** No new Python `DEFAULT_*` / inline-numeric-threshold constants permitted in `src/ikigai/src/agents/v2/*.py`. All algorithm tuning values live in `prompts/algorithm_constants.json` per ADR-019 R1.

**Rationale:** Closes the `observe.py:44, 58` loophole (inline `0.65` fallback for
`q_he` and `1.0` floor for `capacity_estimate`). These are NOT module-level
`DEFAULT_*` constants, so existing drift invariant (l) does not catch them —
invariant (m) is needed.

**Enforcement (W5.10 ship):** Drift invariant (m) extends
`test_no_algorithm_constants_in_agent_code` to scan `nodes/*.py` bodies for inline
numeric literals matching migrated ranges (0.85, 0.60, 1.20, 0.50, 8.0, 3, 2, 0.65,
1.0). CI failure on regression. Mirrors ADR-019 R2 for the inline-numeric case.

**ADR-amendment trigger:** New keys in `algorithm_constants.json` require an
ADR amendment extending invariant (m)'s literal-denylist — couples R1 to R6.

---

## §R2 — No new IKIGAI_TOOLS without explicit ADR

**Rule:** The IKIGAI_TOOLS registry stays at exactly 12 entries. Adding a
new `@MCP.tool` requires an explicit ADR amendment to this rule.

**Rationale:** Extends the IKIGAI_TOOLS = 12 invariant from ADR-013 + existing
`test_ikigai_tools_count_is_12`. Tuning happens via prompt-template updates,
NOT new tools. Adding a 13th tool would be a **scope expansion** violating the
planner-only invariant of ADR-013.

**Enforcement:** Drift invariant (a) `test_ikigai_tools_count_is_12`. CI
failure on any change.

---

## §R3 — Algorithm tuning iteration MUST reference a SONHO log

**Rule:** Every commit that modifies `algorithm_constants.json` or any
`prompts/*.md` template MUST cite the SONHO log (vault) that motivated the
change in the commit body. Per `W5.10 AC4`.

**Rationale:** Mirrors ADR-019 R5 (SONHO log citation for JSON edits). Extends the
citation standard to prompt-template text edits. Without citation, the iteration
is unsubstantiated.

**Enforcement:** PR review + `feedback-precision-calibration-2026-08-28` convention.
Not enforced by drift detector (structural invariants, not commit content).
Format: commit body MUST include SONHO log path + 4-field summary per §F5 template.

---

## §R4 — Algorithm tuning iterations capped at 1 prompt-template update per week

**Rule:** Each algorithm tuning iteration cycle is **at most 1 prompt-template update per week**.

**Rationale:** Per `W5.10 AC1`. The cap prevents the operator from "fixing everything
at once" — a known anti-pattern in algorithm tuning (over-correction, lost causality,
untestable regressions).

**Enforcement:** Operator discipline + PR review cadence. Not enforced by
drift detector (time-based invariant). **Exception:** Emergency rollbacks
(R5 revert) do NOT count toward the cap.

---

## §R5 — Drift detector MUST pass after each iteration

**Rule:** After every algorithm tuning iteration, the drift detector
(invariants a-l + new m) MUST pass. If any invariant fails, the iteration
is reverted via `git revert <commit>` and the SONHO log is preserved.

**Rationale:** Drift verification is the **gating step** before any tuning
commit. The drift detector catches: module-level `DEFAULT_*` regressions
(invariant l), inline numeric threshold regressions (invariant m, new),
IKIGAI_TOOLS count changes (invariant a), review queue append-only
violations (invariant b), vault_write wrapper bypass (invariant e, W4.7
retroactive), skill binding integrity (invariant k), subagent + memory +
kill switch constants in JSON only (invariant l extensions).

**Enforcement:** Drift detector runs in CI + pre-commit hook. CI failure
blocks merge. After W5.2 ship: total drift invariants ≥ 25 (24 baseline + new m).

---

## §R6 — Tuning iterations that modify algorithm_constants.json MUST update both the JSON and the drift invariant registry

**Rule:** When a tuning iteration adds a new key to `algorithm_constants.json`,
the same commit MUST: (1) Add the key to `prompts/algorithm_constants.json`
(SOT); (2) Add the key to `prompts/load_constants.py::_defensive_default()`
(mirror per ADR-019 R6); (3) Extend `test_canonical_scope.py` drift invariant
to assert the new key is NOT hardcoded in `.py` modules.

**Rationale:** Mirrors ADR-019 R1 + R6 (JSON SOT + defensive default +
drift invariant are a 3-way atomic edit). Prevents the drift bug where
JSON has a key but defensive default doesn't.

**Enforcement:** PR review + `test_load_constants_defensive_default_matches_canonical`
(W3.2 ship) + new invariant (m) extension.

---

## §R7 — Kill switch (ADR-029) provides safety net during tuning iterations

**Rule:** During algorithm tuning iterations, the kill switch is the
operator's safety net. Per ADR-029 R1-R12: R4 catches `vault_write(actor=
"agent")` without `transition_validator`; R10 catches excessive writes;
R5 catches direct filesystem writes to vault.

**Rationale:** W5.1 ADR-029 shipped the kill switch as the **safety mechanism for
manual override during tuning**. This ADR references ADR-029 R-rules as the canonical
safety net. No new kill switch mechanisms ship in W5.2.

**Enforcement:** Operator monitors `ikigai://kill-switch/status` MCP resource during tuning cycles (per ADR-029 S2.4). Kill switch entries append to `data/review_queue/` (per ADR-029 S5). If the kill switch fires during a tuning iteration, operator inspects `recovery_path`, decides false-positive vs true-positive, and **reverts the JSON edit** if the iteration is the cause.

---

## §R8 — No algorithm tuning allowed during data-first methodology era

**Rule:** Algorithm tuning is allowed **only on explicit user demand** (per
`algorithm-gate-dropped-2026-09-03.md`). Default to infra/backend work when
user does NOT explicitly request algorithm tuning.

**Rationale:** Mirrors `algorithm-gate-dropped-2026-09-03.md`. The gate was
DROPPED on 2026-09-03 — algorithm work is allowed, but only on demand.
The dcode-harness roadmap W5.10 is the **current explicit demand** that
unblocks W5.10's iterative procedure.

**What stays the same:** PAV math stays archived; `vault_write` is sole
vault writer (ADR-012); IKIGAI_TOOLS = 12 (ADR-013); append-only stores.

---

## §W5.6 — SONHO Data Collection Ritual

W5.6 ships the `/sonho-log` slash command + log template (separate task,
depends on this ADR Accepted). The ritual is the **friction-zero entry
point** for SONHO logging.

### Slash command spec

File: `.claude/commands/sonho-log.md` (new file, W5.6 ship)

```markdown
# /sonho-log — Friction-zero SONHO logging

## When to use
After each `dcode daily` invocation (or whenever a SONHO-related observation
occurs).

## Template
- **Dream:** <one sentence about the higher-level vision>
- **Observation:** <one sentence about what actually happened>
- **Gap:** <one sentence about the difference>
- **Action:** <one sentence about what to do next>

## File target
Append to
`vault/ikigai/closing-2026/01-q3-2026/04-relatórios-diários/sonho-YYYY-MM-DD-N.md`
where N increments per day.

## Drift invariant
- 5+ SONHO logs accumulated → unblocks W5.10 algorithm tuning
- Each log MUST have 4 fields (dream, observation, gap, action) — verified
  by `test_sonho_log_template_complete` (W5.6 ship)
```

### Drift invariant (W5.6 ship)

`src/ikigai/tests/test_sonho_logs.py` (new file) verifies:
- `test_sonho_log_path_exists` — directory exists
- `test_sonho_log_template_complete` — each `.md` has 4 required fields
- `test_sonho_log_count_threshold` — returns ≥5 SONHO logs as W5.10 gating
  signal (assertion is `>= 0` until 5+ logs accumulate, then W5.10 unblocks)

### Implementation rules (W5.6 ship)

1. Slash command is a markdown spec, NOT executable code. Operator reads
   the spec and creates the SONHO log manually.
2. SONHO log path is **append-only** per CLAUDE.md §"Refactor Protocol".
3. Drift invariants run in CI; pre-flight check returns current count.
4. W5.6 does NOT auto-create SONHO logs; operator controls the cadence.

---

## §W5.10 — Algorithm Tuning Procedure (4-8 weeks)

W5.10 is the iterative procedure that uses the SONHO logs accumulated via
W5.6 + the policy codified in this ADR. W5.10 is **NOT a single task** —
it's a 4-8 week iterative cadence with 1 prompt-template update per week.

### Cadence

- **1 prompt-template update per week** (minimum, per W5.10 AC1)
- Each update references a SONHO log (R3)
- Drift verification runs after each update (R5)

### Procedure (per iteration)

1. **Identify SONHO log pattern.** Operator reviews
   `vault/.../04-relatórios-diários/` for recurring observations (same gap
   in 3+ logs) or action divergence (actions cluster on a single tuning
   surface).
2. **Choose tuning target.** Per §F2 surface table — algorithm_constants.json
   key OR prompt-template text in `prompts/*.md`. NO Python `DEFAULT_*`
   constants (R1). NO new IKIGAI_TOOLS (R2).
3. **Update target.** Edit the JSON key OR prompt-template text. Cite the
   SONHO log path in the commit message (R3).
4. **Run drift detector.** All invariants a-m MUST pass (R5). If any fail,
   revert the iteration via `git revert <commit>`.
5. **Commit with SONHO log evidence.** Use the §F5 commit template.
6. **Observe behavior change.** Next `/sonho-log` notes whether the tuning
   had the intended effect.
7. **Kill switch safety.** If unexpected behavior occurs, kill switch fires
   per ADR-029 R4/R10/R5. Operator inspects `data/review_queue/`, decides
   false-positive vs true-positive, reverts if true-positive (R7).

### Drift verification (per iteration)

Required passes (R5): (a) IKIGAI_TOOLS = 12, (b) review_queue append-only,
(c) algorithm_constants.json schema validation, (e) vault_write actor
validation (W4.7 retroactive), (k) planner-only scope (ADR-013),
(l) no Python `DEFAULT_*` in agent code, (m) no inline thresholds in node
bodies (NEW, this ADR). Plus regression tests: `test_algorithm_constants_migration.py`
(ADR-019 R4), `test_kill_switch.py` (ADR-029 W5.1.1), `test_drift_invariants.py`
(Wave 4/5 extensions), `test_canonical_scope.py` (current 24+ invariants).

### Out of scope (W5.10)

- IKIGAI_TOOLS expansion (forbidden by R2)
- Math kernel execution (per `algorithm-scope-reframed-2026-08-30.md`)
- PAV revival (per `algorithm-gate-dropped-2026-09-03.md`)
- New algorithm modules (out of agent layer scope per ADR-013)
- New drift invariants beyond (m) (deferred to future ADRs if needed)

---

## Cross-ADR Consistency Check

| ADR | Relationship to ADR-030 |
|-----|--------------------------|
| **ADR-013** (canonical scope discipline, Accepted 2026-08-31) | Bounds tuning to planner-only; IKIGAI agent layer cannot execute math. R2 (no new IKIGAI_TOOLS) inherits ADR-013's `IKIGAI_TOOLS = 12` invariant. R1 (no Python constants) inherits ADR-013's "drift detector enforced" pattern. |
| **ADR-019** (QHE prompt-template, Accepted 2026-09-04 W3.2) | **Precedent**: QHE constants ship as JSON keys (`QHE_PUSH_THRESHOLD`, etc.), not Python `DEFAULT_*`. This ADR generalizes the pattern into a policy for all algorithm tuning. R1 mirrors ADR-019 R2 (no `DEFAULT_*` in agent code). R5 mirrors ADR-019 R3 (drift count grows by 1 per Wave). R6 mirrors ADR-019 R1+R6 (JSON SOT + defensive default + drift invariant 3-way atomic edit). |
| **ADR-029** (kill switch + review queue, Accepted 2026-09-04 W5.1) | **Safety net** during tuning iterations. R7 references ADR-029 R1-R12 as the canonical safety mechanism. §F4 specifies kill switch integration with the tuning procedure. ADR-029's `KILL_SWITCH_RATE_LIMIT_PER_HOUR` is a tuning surface per §F2 (operators may tune the rate limit during high-throughput iterations). |
| **ADR-026** (sub-agent dispatch, DRAFT 2026-09-04 `3cc9799`) | **Extension**: sub-agents can be invoked for SONHO log analysis (per W5.10 step 1). The dispatcher (per ADR-026 R1) is the canonical spawn surface. Sub-agent writes via `dispatch_sub_agents` are legal per ADR-029 R7 + R6. |
| **ADR-028** (cross-cycle memory, DRAFT 2026-09-04 `120b536` R1 amended `d602a4d`) | **Storage**: SONHO logs accumulate across cycles via the cross-cycle memory layer. Per ADR-028 R8, `MEMORY_RETENTION_DAILY_DAYS=30` (SONHO logs older than 30 days roll off). ADR-028's atomic `memory_write_atomic` is the legal caller for SONHO log persistence (per ADR-029 R6 legal_caller whitelist).

---

## Drift Invariants

This ADR references existing drift invariants (a-l) + adds a NEW invariant
**(m)** for "no Python `DEFAULT_*` constants in agent code" extension that
catches inline numeric thresholds in node bodies.

### Existing invariants (referenced for context)

- **(a)** `test_ikigai_tools_count_is_12` (ADR-013) — R2 protects this.
- **(b)** `test_review_queue_append_only` (Phase 8.5 extension).
- **(c)** `test_load_constants_*` (ADR-019) — algorithm_constants.json schema.
- **(e)** `test_vault_write_only_via_wrapper` (ADR-029, W4.7 retroactive).
- **(k)** `test_no_hardcoded_entry_points_*` (ADR-025) + subagent extensions
  (ADR-026 R1, R4, R6 + ADR-027 R3, R10, R13.5).
- **(l)** `test_no_algorithm_constants_in_agent_code` (ADR-019 R7) +
  extensions: subagent (W4.4), memory retention (W4.6), kill switch
  (W5.1.1). 24/24 PASS baseline.

### NEW invariant (W5.2 ship)

- **(m)** `test_no_inline_thresholds_in_node_bodies` — closes
  `observe.py:44, 58` loophole. Scans `src/ikigai/src/agents/v2/nodes/*.py`
  for inline numeric literals matching migrated ranges (0.85, 0.60, 1.20,
  0.50, 8.0, 3, 2, 0.65, 1.0). Any regression breaks CI.

  Implementation deferred to W5.10 (algorithm tuning start). This ADR
  specifies the invariant so the W5.10 implementation is well-scoped.

### Drift invariants current state

Per Wave 4 SHIP-COMPLETE at `f77988f`: 24 invariants in
`test_canonical_scope.py` + 10 in `test_drift_detector.py + extended`
= 48 total. After W5.2 ship: 48 (no new test code in this ADR; invariant
m specified but implementation deferred to W5.10). After W5.10 ship:
49+ invariants (m added).

---

## Algorithm Constants JSON Keys

This ADR references existing keys (per ADR-019 + W4.4/W4.5/W4.6/W5.1.1)
+ specifies the **SONHO log metadata keys** (new keys for W5.6 ship) that
will be added to `algorithm_constants.json` when W5.6 ships.

### Existing keys (referenced for context)

Per ADR-019 + ADR-026 + ADR-027 + ADR-028 + ADR-029, the canonical SOT at
`prompts/algorithm_constants.json` ships 27 tuning values across 8 categories:
QHE (3), Workload (3), Hysteresis (2), Heuristics (7), Subagent (4), Checkpoint
(2), Memory (4), Kill switch (5).

### NEW keys (W5.6 ship)

W5.6 ships the `/sonho-log` slash command. To support SONHO log template
validation + 5+ log threshold, the following keys land in
`algorithm_constants.json` at W5.6 ship:

```json
{
  "SONHO_LOG_MIN_COUNT_FOR_TUNING": 5,
  "SONHO_LOG_FIELD_DREAM": "Dream",
  "SONHO_LOG_FIELD_OBSERVATION": "Observation",
  "SONHO_LOG_FIELD_GAP": "Gap",
  "SONHO_LOG_FIELD_ACTION": "Action"
}
```

| Key | Default | Meaning |
|-----|---------|---------|
| `SONHO_LOG_MIN_COUNT_FOR_TUNING` | `5` | Min SONHO logs to unblock W5.10 |
| `SONHO_LOG_FIELD_DREAM` | `"Dream"` | Required field name |
| `SONHO_LOG_FIELD_OBSERVATION` | `"Observation"` | Required field name |
| `SONHO_LOG_FIELD_GAP` | `"Gap"` | Required field name |
| `SONHO_LOG_FIELD_ACTION` | `"Action"` | Required field name |

**Defensive defaults:** per ADR-019 R6, `load_constants._defensive_default()`
must mirror JSON exactly. **No Python `DEFAULT_SONHO_*` constants** per ADR-019 R2.

---

## Consequences

### Positive

- **Stable feedback loop.** The 5-phase cycle (SONHO logging → prompt
  iteration → drift verification → kill switch safety → human review)
  is repeatable and auditable.
- **SONHO-driven tuning is auditable.** Every tuning change cites the
  SONHO log in the commit body (R3) — empirical evidence is explicit
  and reversible per `feedback-precision-calibration-2026-08-28`.
- **No Python constants regression.** R1 + new invariant (m) close the
  observe.py:44, 58 loophole. Tuning edits go through JSON SOT only.
- **Kill switch safety net.** R7 references ADR-029 R1-R12 — operators
  have a 3-mechanism safety net for unexpected tuning behavior.
- **Slow-iteration cadence.** R4 caps tuning at 1 update/week — prevents
  over-correction + preserves causality for SONHO log correlation.
- **Planner-boundary enforcement.** R2 protects IKIGAI_TOOLS = 12 — no
  scope expansion via new tools. Tuning is policy, not new tools.
- **Wave 5 architectural foundation.** W5.1 → W5.2 → W5.6 → W5.10.
  Without this ADR, W5.6 + W5.10 cannot start.

### Negative

- **Operator overhead.** W5.6 + W5.10 require manual SONHO logging +
  weekly tuning cadence. Operator TUI SONHOs tab (W5.9) reduces friction
  but does not eliminate it.
- **5+ SONHO logs gating.** Per `algorithm-gate-dropped-2026-09-03.md`,
  the SONHO-log-count gate was DROPPED for general algorithm work — but
  W5.10 retains the 5+ log threshold as a quality signal (the logs are
  evidence, not a counter). Deliberate re-introduction for W5.10 only.
- **Drift detector growth.** R5 + invariant (m) add to the drift
  detector's invariant count (currently 24). Cumulative growth across
  Wave 3-5 is +6 invariants. Acceptable trade-off for safety.
- **observe.py:44, 58 refactor deferred.** This ADR specifies invariant
  (m) but defers implementation to W5.10's first cadence iteration.
  observe.py:44, 58 inline defaults remain until W5.10 ships.

### Neutral

- **5-phase + 8-rule structure.** Mirrors ADR-029's contract+rule pattern
  (S1-S5 + R1-R12) but is lighter (no 5-contract surface area).
- **SONHO log path is pre-existing.** Canonical path
  `vault/.../01-q3-2026/04-relatórios-diários/` already exists per the
  data-first methodology. W5.6 does NOT create new vault paths.
- **W5.6 + W5.10 are separate tasks.** This ADR is policy-only. W5.6
  ships `/sonho-log` slash command + drift invariant. W5.10 ships the
  iterative procedure + invariant (m) implementation + first cadence.

---

## Alternatives Considered

### Alt A — Allow Python `DEFAULT_*` for new algorithm tuning

Status quo pre-W3.2. Drift between `state.py` and node bodies was the
exact problem W3.2 fixes. **Rejected:** ADR-019 R2 already forbids this.

### Alt B — Allow inline numeric thresholds in node bodies

The current `observe.py:44, 58` loophole. **Rejected:** ADR-013
single-source-of-truth + ADR-019 R2 forbid two-source drift. New
invariant (m) closes the loophole.

### Alt C — Tuning via new IKIGAI_TOOLS (count 13+)

Add a new `@MCP.tool` for each tuning iteration. **Rejected:** R2 forbids
new tools. Tuning is policy (prompt + JSON), not new tools.

### Alt D — Auto-clear kill switch during tuning

Auto-disengage the kill switch during a tuning iteration cycle.
**Rejected:** ADR-029 R11 forbids auto-clear (manual recovery required).

### Alt E — Tuning iteration without SONHO log evidence

Allow tuning iterations without empirical evidence. **Rejected:** R3
mandates SONHO log citation. Empirical evidence is the precondition per
`feedback-precision-calibration-2026-08-28`.

---

## References

### Load-bearing prior ADRs

- **ADR-013 — Canonical scope discipline** (Accepted 2026-08-31) — R1 + R2
  inherit the "planner-only" invariant + IKIGAI_TOOLS = 12 enforcement
- **ADR-019 — QHE → prompt-template constants** (Accepted 2026-09-04 W3.2,
  `1ef638c`) — Pattern precedent: JSON SOT + defensive default + drift
  invariant. R1 + R5 + R6 mirror ADR-019 R2 + R3 + R1+R6.
- **ADR-026 — Sub-agent dispatch protocol** (DRAFT 2026-09-04 `3cc9799`) —
  Sub-agents can be invoked for SONHO log analysis (W5.10 step 1).
- **ADR-028 — Cross-cycle memory layer** (DRAFT 2026-09-04 `120b536`, R1
  amended `d602a4d`) — SONHO logs accumulate across cycles via the
  cross-cycle memory layer.
- **ADR-029 — Kill switch + review queue** (Accepted 2026-09-04 W5.1) —
  R7 references ADR-029 R1-R12 as the canonical safety net. §F4 specifies
  kill switch integration.

### Load-bearing memories

- `memory/algorithm-scope-reframed-2026-08-30.md` — IKIGAI = planner with
  stochastic PAE feedback; 3 components OUT OF IKIGAI (PAV desativated);
  2 OUT OF BACKEND (prompt-template).
- `memory/algorithm-gate-dropped-2026-09-03.md` — Algorithm gate dropped.
  Algorithm work allowed on explicit demand. PAV math stays archived.
- `memory/algorithm-decisions-defer-2026-08-28.md` — User's 3rd reversal.
  Reversibility + telemetry + day-to-day conflicts framework.
- `memory/algorithm-issues-registry.md` — 31 inconsistencies catalogued
  (2026-07-02). Header SUPERSEDED 2026-08-30 per scope reframe.

### Code references

- `src/ikigai/src/agents/v2/nodes/observe.py:44, 58` — inline-default loophole
  this ADR closes (R1 + invariant m)
- `src/ikigai/src/agents/v2/prompts/algorithm_constants.json` — JSON SOT per
  ADR-019
- `src/ikigai/src/agents/v2/prompts/load_constants.py` — loader + defensive
  default mirror per ADR-019 R6
- `src/ikigai/src/agents/v2/nodes/observe.py:50-55, 61-64` — existing correct
  usage of `_c("QHE_PUSH_THRESHOLD")` etc.
- `src/ikigai/src/ikigai/security/transition_validator.py:38` — SONHO
  `actor="user"` invariant (per ADR-029 R8)
- `src/ikigai/src/ikigai/vault/vault_write.py:41-67` — `vault_write(
  vault_root, vault_path, frontmatter_fields, body, actor=...)` signature
- `data/review_queue/` — append-only filesystem queue (per ADR-029 S5 +
  W5.6 SONHO log location)

### Drift detector references

- `src/ikigai/tests/test_canonical_scope.py` — `test_ikigai_tools_count_is_12`
  (a), `test_review_queue_append_only` (b), `test_load_constants_*` (c),
  `test_no_algorithm_constants_in_agent_code` (l) + subagent + memory +
  kill switch extensions. Currently 24/24 PASS.
- `src/ikigai/tests/test_drift_invariants.py` — invariant (e) for vault_write
  wrapper (W4.7 retroactive).
- NEW: `test_no_inline_thresholds_in_node_bodies` (m, W5.10 ship).

### Roadmap / spec references

- `docs/superpowers/specs/2026-09-04-dcode-harness-PLAN.md` §3 —
  W5.2 task spec (this ADR)
- `docs/superpowers/specs/2026-09-04-dcode-harness-TASKS.md` —
  W5.2 acceptance criteria (lines 401-403); §W5.6 lines 457+; §W5.10
  algorithm tuning procedure spec (4-8 weeks)

### Wave 5 ship context

After W5.2 ships: W5.1 ✅ ACCEPTED at `59dd445`; W5.1.1 ✅ implementation
+ W4.7 retroactive; W5.2 🎯 THIS ADR; W5.3 ADR-020..024 (5 ADRs); W5.4
ADR-014 follow-up; W5.5 Plan C re-dispatch; W5.6 SONHO ritual; W5.7 mesh
show SONHO traversal; W5.8 drift invariant (d); W5.9 Operator TUI SONHOs
tab; W5.10 Empirical algorithm tuning; W5.11 Real-world debugging;
W5.12 Spec fills; W5.13 Spec orphan cleanup; W5.14 Implementation orphan
specs. Total 15 tasks; after W5.2: 3 of 15 SHIP-COMPLETE.

---

*ADR-030 — DRAFT 2026-09-04 — Wave 5 W5.2 — Empirical algorithm tuning
feedback loop policy — gates W5.6 + W5.10 — user review pending*
