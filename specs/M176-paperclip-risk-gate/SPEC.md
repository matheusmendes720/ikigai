---
name: M176-paperclip-risk-gate
description: Paperclip risk gate — fail-CLOSED on dangerous keyword match (18 defaults). Third auto-throttle, parallels M173/M175.
status: DONE
owner: matheus-mendes
created: 2026-10-11
constitution_refs:
  - tests_are_the_contract
  - state_on_disk_not_conversation
  - composition_over_inheritance
estimated_cost_usd: 0.00
---

# M176 — Paperclip Risk Gate (Auto-Throttle #3)

**Status:** DONE
**Date:** 2026-10-11
**Author:** matheus-mendes (with Claude Code assist)

---

## TL;DR

M176 adds a **risk gate** as the third auto-throttle in the Paperclip
architecture, complementing `CostGate` (M173) and `WallClockGate` (M175).
The gate scans the resolved spec text + the agent prompt for dangerous
keyword patterns (`rm -rf`, `git push --force`, `.env`, `api_key=`,
fork-bomb, etc.) and **fails-CLOSED** — refuses to invoke the agent
when any match is found. Drift net grows **73 → 74** (+1 new invariant).

The risk gate complements the existing two gates by catching a
different failure mode:

| Gate | Catches | Semantics |
|---|---|---|
| `CostGate` (M173) | Daily spend is over budget — burn-rate ceiling. | fail-OPEN |
| `WallClockGate` (M175) | Single task has been running too long — runaway / infinite-retry ceiling. | fail-OPEN |
| `RiskGate` (M176) | Spec/prompt asks for destructive or credential-leaking action. | fail-**CLOSED** |

The asymmetry is deliberate: cost overrun wastes money, wall-clock
overrun wastes time, but a `rm -rf /` or `git push --force` mistake
**destroys state**. The risk gate must refuse.

---

## What changed

```
src/ikigai/src/agents/paperclip/policy.py          # +RiskGate, +DEFAULT_RISK_KEYWORDS, +ENV_RISK_KEYWORDS
src/ikigai/src/agents/paperclip/nodes/implement.py # +RiskGate consultation BETWEEN wall-clock and adapter
src/ikigai/src/agents/paperclip/tests/test_risk_gate.py  # NEW (5 tests)
src/ikigai/tests/test_paperclip_drift.py           # +1 drift invariant
.claude/loop/roadmap.md                            # +M176 entry
specs/M176-paperclip-risk-gate/SPEC.md             # this file
```

**Total: 1 new test file + 4 modified files. Drift net 73 → 74.**

The `CostGate` and `WallClockGate` classes are **untouched** —
`RiskGate` is appended to `policy.py` at module-bottom and re-exported
via `__all__`. The three gates coexist; node `implement.py` calls them
sequentially (cost first, wall-clock second, risk third).

---

## Architecture decisions

### D12 — Risk gate is fail-CLOSED (asymmetric to M173/M175)

The risk gate is the first **fail-CLOSED** gate in the Paperclip
auto-throttle chain. The rationale is asymmetric: cost overrun wastes
money (a recoverable loss); wall-clock overrun wastes time (a
recoverable loss); but a `rm -rf /` or `git push --force` mistake
**destroys state** (often irrecoverable). Fail-CLOSED semantics mean
ANY match refuses the call, with no "missing field → allow" escape
hatch (unlike cost/wall-clock where missing data defaults to allowed).

Concretely, an empty `text_to_check` returns `allowed=True` (nothing
to scan), but ANY non-empty text with ANY keyword substring match
returns `allowed=False`.

### D13 — Keyword list is configurable, defaults are dangerous-keyword-list

`DEFAULT_RISK_KEYWORDS` is an 18-tuple of substring tokens covering
four categories:

* **Destructive shell** — `rm -rf`, `rm -fr`, `drop database`,
  `drop schema`, `truncate table`.
* **Git / VCS** — `git push --force`, `git push -f`,
  `git push --force-with-lease` (unsafe variant; user override
  required), `git reset --hard`.
* **Secrets / credentials** — `.env`, `secrets`, `private_key`,
  `id_rsa`, `~/.ssh`, `password=`, `api_key=`.
* **Persistence** — `chmod 777`, fork-bomb `:(){:|:&};:`.

Override via env `PAPERCLIP_RISK_KEYWORDS` (comma-separated).
**Empty/unset env falls back to the default** — the gate never
silently empties its dangerous-keyword list (that would defeat
the gate). An explicit empty override (`keywords=[]` to the
constructor) IS honored as the documented escape hatch for tests
that need to disable the gate.

### D14 — Match is case-insensitive substring

`text_to_check.lower()` is the haystack; keywords are tested as
lowercased substrings. This catches `DROP DATABASE`, `Rm -Rf`, and
other case-variant forms without enumerating each one in the
keyword list.

### D15 — Reason lists ALL matches, not just the first

When multiple keywords match, the reason string lists every matched
keyword (quoted via `repr()`). Operators triaging a block see the
full picture — they may need to rewrite multiple dangerous intents,
not just the first.

---

## Verification

```bash
# 1. Risk gate tests — must show 5/5 PASS
python -m pytest src/ikigai/src/agents/paperclip/tests/test_risk_gate.py -v

# 2. Full paperclip suite + drift — must show 49 PASS (43 prior + 5 new + 1 drift)
python -m pytest src/ikigai/src/agents/paperclip/tests/ src/ikigai/tests/test_paperclip_drift.py -v

# 3. Drift net — must show 74 passed (was 73 + 1 new M176)
python -m pytest src/ikigai/tests/test_drift_invariants.py \
                  src/ikigai/tests/test_drift_extended_invariants.py \
                  src/ikigai/tests/test_canonical_scope.py \
                  src/ikigai/tests/test_paperclip_drift.py

# 4. Lint + format
python -m ruff check src/ikigai/src/agents/paperclip/ src/ikigai/tests/test_paperclip_drift.py
python -m ruff format --check src/ikigai/src/agents/paperclip/ src/ikigai/tests/test_paperclip_drift.py

# 5. Sanity: importable, default blocks dangerous input
python -c "from src.ikigai.src.agents.paperclip.policy import RiskGate; g = RiskGate(text_to_check='rm -rf /'); print(g.check())"
# Expect: (False, "dangerous keyword match: 'rm -rf' ...")
```

---

## Acceptance

- [x] `src/ikigai/src/agents/paperclip/policy.py` extended with
      `RiskGate` class — fail-CLOSED, 18 default keywords, env-driven
      override — **without modifying `CostGate` / `WallClockGate`**
- [x] `policy.__all__` exports `RiskGate`, `DEFAULT_RISK_KEYWORDS`,
      `ENV_RISK_KEYWORDS`
- [x] `nodes/implement.py` consults `RiskGate` AFTER `WallClockGate`
      and BEFORE the agent invocation; on block returns
      `error_type="RiskGateExceeded"`
- [x] 5 new tests in `test_risk_gate.py` covering: clean text,
      dangerous keyword, case-insensitive, multiple matches, env override
- [x] 1 new drift invariant in `test_paperclip_drift.py`:
      `test_paperclip_risk_gate_exists`
- [x] Drift net: **73 → 74** (+1)
- [x] `ruff check` + `ruff format --check` clean on changed files
- [x] `RiskGate` importable from
      `src.ikigai.src.agents.paperclip.policy` with non-empty default
      `keywords` tuple
- [x] No existing logic modified — `CostGate` and `WallClockGate`
      untouched, `implement` wire-up appends a new block (does not
      edit the existing cost/wall-clock blocks)

---

## Lessons

1. **Asymmetric fail-CLOSED is the right default for destructive
   actions.** The risk gate's design rationale is the "destroys
   state" failure mode — cost/wall-clock gates protect against
   waste; the risk gate protects against irreversible harm. A
   uniform "fail-open for missing data" philosophy does not apply.

2. **Default keyword list is conservative; override is opt-in.** The
   19-tuple covers the four main dangerous-intent categories
   (destructive shell, git/VCS, secrets/credentials, persistence).
   An operator who needs to enable a flagged-but-legitimate command
   (e.g. `git push --force-with-lease` on a private fork) can
   remove it from the env override — the gate does not block by
   accident without an explicit override.

3. **Multiple-match reason echoes every match.** When a spec
   contains both `rm -rf` and `git push --force`, the reason string
   lists both — not just the first. The operator triaging the
   block needs the full picture; partial disclosure forces a
   follow-up cycle.

---

## Related

* [M173 cost gate](file:///C:/Users/mathe/code_space/life-oss/life/specs/M169-paperclip/SPEC.md)
  — the first auto-throttle, fail-OPEN
* [M175 wall-clock gate](file:///C:/Users/mathe/code_space/life-oss/life/specs/M175-paperclip-wall-clock-gate/SPEC.md)
  — the second auto-throttle, fail-OPEN
* [M169 Paperclip spec](file:///C:/Users/mathe/code_space/life-oss/life/specs/M169-paperclip/SPEC.md)
  — the 4th LangGraph graph that owns all three gates
* [M174 auto-spawner](file:///C:/Users/mathe/code_space/life-oss/life/specs/M174-paperclip-auto-spawner/SPEC.md)
  — the spawner script that may eventually trigger the gates (the
  gates do not yet block the spawner's `--once` path; that's a
  future wiring — the spawner dispatches to the graph which then
  runs the gates inside `implement_node`)
