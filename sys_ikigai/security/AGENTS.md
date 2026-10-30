# AGENTS.md — `sys_ikigai/security`

> Earned its file: score 9/20 — distinct domain (the single enforcement point for vault writes).
> Parent: `sys_ikigai/AGENTS.md`. Scope: this directory only.

## OVERVIEW

The write gate. `vault_write_wrapper.py` is the **single enforcement point** for actor
discipline on every vault write (ADR-029 §S2 + R2); `kill_switch.py` provides the emergency
abort; `transition_validator.py` blocks illegal phase transitions. 4 modules, ~1k LOC.

## WHERE TO LOOK

| File | Role |
|------|------|
| `vault_write_wrapper.py` | `make_wrapped_vault_write(vault_root_provider, data_root_provider, review_queue_dir_provider, *, rate_limit_tracker=None)` returns a `vault_write`-compatible callable. `install_wrapper()` monkeypatches `vault_write` at import time so every import gets the guarded version. Raises `KillSwitchAbort`, `KillSwitchRateLimitExceeded`, `KillSwitchActorViolation`, `KillSwitchBypassDetected`. |
| `kill_switch.py` | `check_kill_switch(vault_root, data_root)`, `build_kill_switch_event(...)`, `fire_kill_switch(event, review_dir, vault_root)`. Precedence: env var `IKIGAI_KILL_SWITCH=1` → `vault/.kill_switch.md` → `data/.kill_switch`. Writes a recovery file and appends to the audit log. |
| `transition_validator.py` | `validate_phase_transition(...)` — blocks `tier == "SONHO"` writes when `actor != "user"` unless a legal caller overrides. |

## THE ENFORCEMENT LADDER (order is load-bearing)

```
caller → 1 kill switch → 2 rate limit → 3 actor validation → 4 transition validator
       → 5 legal-caller whitelist → 6 audit pre-write → 7 vault_write → 8 audit post-write
```

- **Legal callers** (`LEGAL_CALLERS`): `memory_write_atomic`, `dispatch_sub_agents`,
  `tag_and_persist`, `skill_orchestrator`. Pass one as `legal_caller=` to allow an
  `actor='agent'` write.
- **Actors** are exactly `user | agent | system` (R9).
- **Tuning constants** come from `algorithm_constants.json` (ADR-019 R1) through
  `_load_tuning_constants()`; the fallback is `(50 per hour, 3600.0 s, notify=True)`.

## CONVENTIONS (deviations from parent)

- The wrapper is **purely additive** over `vault_write` — it adds checks, never reimplements them.
- Audit records land in `.vault_audit.log` as pre- and post-write appends.

## ANTI-PATTERNS

- **Never call `vault_write` without this wrapper** — direct calls are drift-invariant
  violations in `agents/v2/*.py`.
- **Do not duplicate audit logic** from `vault_write.py` inside the wrapper (ADR-029).
- **An audit-log failure MUST NOT fail the write.** The audit append is deliberately wrapped in
  `except: pass`; the write already succeeded.
- **The rate-limit window is in-memory** — a process restart resets the counter. Treat the limit
  as best-effort, not a hard quota.
- Never bypass the kill switch for convenience; `LEGAL_CALLERS` is the only sanctioned bypass.
