# sys_ikigai/security

Safety primitives: the kill switch (ADR-029), the `vault_write` enforcement
wrapper, and the PAE phase-transition validator. Earns its file: distinct
domain (safety layer), complexity score 8.

## OVERVIEW
Every vault write is expected to traverse `vault_write_wrapper`, which checks
the kill switch, the rate limit, the actor, the phase transition and the
caller whitelist before delegating to `vault_write`.

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| Kill switch state + firing | `kill_switch.py` | 494 lines; `check_kill_switch`, `fire_kill_switch`, `recover_kill_switch`, `build_kill_switch_event` |
| Write enforcement | `vault_write_wrapper.py` | `make_wrapped_vault_write`, `install_wrapper` |
| Phase transition rules | `transition_validator.py` | `validate_phase_transition` |
| Tuning constants (SOT) | `algorithm_constants.json` | canonical kill-switch tuning, ADR-019 R1 |
| Package doc | `__init__.py` | documentation only, no exports |

## CONVENTIONS
- Three activation mechanisms, priority-ordered: env var
  `IKIGAI_KILL_SWITCH=1`, then `<vault_root>/.kill_switch.md` with
  `status: active`, then `<data_root>/.kill_switch`.
- All tuning constants live in `algorithm_constants.json` (this package — the
  canonical single source of truth, ADR-019 R1). No Python
  `DEFAULT_KILL_SWITCH_*` constants are permitted (ADR-019 R2 + ADR-029).
- Wrapper layering, in order: kill switch -> rate limit -> actor validation ->
  phase-transition validator -> legal-caller whitelist -> audit pre-write ->
  `vault_write` -> audit post-write.
- `LEGAL_CALLERS` (`memory_write_atomic`, `dispatch_sub_agents`,
  `tag_and_persist`, `skill_orchestrator`) is the only set allowed to bypass
  kill-switch enforcement.
- Kill-switch events are appended to `data/review_queue/`; that log is
  append-only.
- `vault_write_wrapper` is purely additive over `vault/vault_write.py` — it
  adds enforcement, never a second audit implementation.

## ANTI-PATTERNS
- Never call `vault_write` directly from agent code — go through the wrapper.
  Drift invariant (e) checks this.
- SONHO phase transitions require `actor="user"`; the validator raises
  `PermissionError` otherwise. Other tiers accept any actor.
- The CLI must never set the kill switch programmatically (R5/R11). Activation
  lives in this package only; `interfaces/cli/kill_switch.py` is a consumer.
- An audit-log write failure must not prevent the kill switch from firing.
- Do not add a `src/contracts/` schema or an `algorithm_constants.json` entry
  from this package — the CLI-side consumer stays schema-free.
- `transition_validator` imports `src.contracts.base.BasePlanContract` and
  `src.contracts.common.PaeCyclePhase` — keep the dotted `src.*` import form.

## COMMANDS
```bash
python -m pytest src/ikigai/tests/test_kill_switch.py -v
python -m pytest tests/ikigai/security/test_transition_validator.py -v
```
