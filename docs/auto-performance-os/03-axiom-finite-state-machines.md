# 03 — Axiom: Finite-State Machines

> **Category:** §1 Axiomatic base
> **Audience:** Self + future agents
> **Source material:** pomodoro_machine.py (7 states), policy_engine.py (4 states), 7 IKIGAi lifecycle FSMs

---

## §1 — Plain-language intuition

A complex behavior is just a set of named **states** — idle, working, on break, paused — and the **rules** for moving from one to another. You can't be "working" and "on break" at the same time, but you can transition from one to the other. A state machine is the formal way to write this down.

## §2 — Formal statement

A finite-state machine (FSM) is a tuple `(S, Σ, δ, s₀, F)`:

| Symbol | Meaning |
|:------:|:--------|
| `S` | Finite set of states (closed enum) |
| `Σ` | Input alphabet — the set of events/triggers |
| `δ: S × Σ → S` | Transition function — what state you end up in |
| `s₀ ∈ S` | Initial state |
| `F ⊆ S` | Accepting/terminal states |

A transition is **valid** iff `(current_state, event) ∈ valid_transitions`. Invalid transitions are rejected (raise `ValueError`, log audit, or return error — depends on the implementation).

## §3 — Non-technical rationale

Life is mostly discrete. You're either in a pomodoro WORK block or a BREAK — not "halfway". You're either in regime PUSH or MAINTAIN or REDUCE or RECOVER — not "kinda pushing". Modeling these as **explicit states with explicit transition rules** makes the system:

- **Testable** — every transition is a unit test (PRD-CORE-POMODORO-SCENARIO has 134 tests just for the pomodoro SM)
- **Predictable** — the user can reason about what's next (after `WORK → BREAK` always comes `WORK` again unless it's the last round)
- **Auditable** — every transition emits an event record (the pomodoro machine emits 10 events per full session)

The cost is verbosity: 4-state policy FSM needs 7+ transition rules. The benefit is that **complex behaviors compose from simple, named pieces**.

## §4 — Cross-references (downstream consumers)

- **10-postulate-pomodoro-rhythm** — domain claim built on this axiom
- **14-engine-policy-engine-fsm** — implements 4-state PUSH/MAINTAIN/REDUCE/RECOVER FSM
- **15-engine-pomodoro-machine** — implements 7-state IDLE/WORK/BREAK/LONG_BREAK/PAUSED/SKIPPED/COMPLETE SM
- **16-meta-regime-fsm** — IKIGAi 4-state FSM with hysteresis
- **17-meta-phase-pivot-fsm** — IKIGAi 5-phase FSM with iterative convergence
- **Lifecycle FSMs:** task_sm, project_sm, habit_sm, routine_sm, goal_sm, objective_sm, deliverable_sm, dream_sm (`src/ikigai/src/ikigai/state_machines/`)

## §5 — Sources

- `src/operational/packages/core/src/operational/core/pomodoro_machine.py` — 7-state SM, 11 transitions (canonical reference)
- `src/operational/packages/core/src/operational/core/policy_engine.py` — 4-state FSM with hysteresis
- `src/ikigai/src/ikigai/core/heuristics/regime.py` — IKIGAi regime FSM
- `src/ikigai/src/ikigai/core/heuristics/phase_pivot.py` — IKIGAi phase FSM
- `src/operational/docs/adr/PRD-CORE-POMODORO-SCENARIO.md` §3.1 — state diagram + transition table
- `src/operational/docs/adr/PRD-CORE-POLICY-CONSOLIDATOR.md` §4 — FSM evaluation rules
- Hopcroft, J. E., Motwani, R., & Ullman, J. D. (2006). *Introduction to Automata Theory, Languages, and Computation*. 3rd ed. Pearson.