# Meta-Learning Note for IKIGAi Agents

> **Audience:** Future AI agents (Claude Code, Codex, Cursor, Kiro, OpenCode, Hermes, etc.) working
> on the IKIGAi / life-ops / vibe-ops ecosystem.
> **Status:** Living document — update between cohorts, never mid-cohort.
> **Cluster:** Meta · IKIGAi Sys-00 (governance) · PIVOT marker active 2026-07-02.

---

## 1. Why this note exists

The PAV (Produtividade Algorítmica Visual) productivity kernel in `life-ops/operational/` was
designed top-down: full Pydantic v2 entity graph, 4-state regime FSM with hysteresis, Q_HE
composite scoring, 9 TUI screens, 14 persistent repositories, 2500+ tests — all before observing
how the human actually plans their week. The result is a system that is technically elegant but
ratio-mismatched to lived behavior: ~80% of the engineering surface lights up less than once a
week, while the workflows the user repeats 3-5 times per day have no dedicated surface at all.
For the second half of 2026 we are pivoting to **data-first emergent methodology**: the human
fills planning templates by hand (`vibe-ops/planning/_templates_periodos_v2/`), and code only
emerges after 5+ manual logs surface a stable pattern. This file is the handoff for that pivot.
Every agent touching this repo must read it before proposing design changes.

---

## 2. The PAV over-engineering trap

Concrete symptoms visible in `life-ops/operational/` as of mid-2026:

- **9 TUI screens** defined (`dashboard`, `daily_flow`, `habits`, `journal`, `metrics`,
  `pomodoro_timer`, `policy`, `help`, plus the home menu) when daily use is dominated by exactly
  one — `dashboard`. The other 8 are visited weekly at best.
- **14 `_PersistentRepo` instances** wired in `apps/cli/src/operational/cli/state.py` —
  `Routine, RoutineLog, TimeBlock, JournalEntry, Habit, SleepRecord, PomodoroRound,
  PolicyDecision, PolicySetpoints, AjusteFino, DayContext, DailyReflection, LunchRecord,
  TransicaoRegistrada` — when the human actively fills data into ~4 of them (Habit, Journal,
  TimeBlock, PomodoroRound). The other 10 sit at zero or near-zero volume.
- **2518+ pytest tests** (markers: unit, integration, property, e2e, tui) guarding infrastructure
  that is invoked once per sprint. The signal-to-noise ratio for catching real regressions is
  drowned in tests asserting invariants of files nobody opens.
- **Complex Q_HE composite** (`habit_engine.py`) — `H(t) = 1 − e^(−λ·streak)`,
  `E = R·(1 − H(t))`, and a weighted blend — when the human just wants to log "drank water,
  today". One bell-curve composite is solving for a precision the user does not request.
- **4-state regime FSM with asymmetric hysteresis** (`policy_engine.py`: PUSH → MAINTAIN →
  REDUCE → RECOVER, with day-counter dwell requirements) when the human manually overrides
  policy recommendations ~70% of the time. A machine-tuned state machine is gating actions the
  user is going to take manually anyway.
- **14 entity contracts** frozen at the schema layer (`Pydantic v2`, `frozen=True`,
  `extra="forbid"`) — by spec, changes to any entity ripple through CLI commands, TUI screens,
  parsers, AND reports. The blast radius of a single new field is an afternoon's worth of
  changes across three layers, even when the field is half-utilized.
- **145+ markdown planning templates** designed but unfilled — the patient has the prescription
  but has not taken it.

The general shape is: **a richly engineered system with no observed usage signal to justify the
breadth.** The pivot below is the corrective action.

---

## 3. The data-first pivot

For the second half of 2026 (July through December), the operating procedure is:

1. **Manual first.** The human fills the planning templates in
   `vibe-ops/planning/_templates_periodos_v2/` by hand — `00-quartely-planning.md`,
   `01-sonho.md`, `02-avaliacao-trimestral.md`, `03-onda.md`, `04-revisao-semanal.md`,
   `05-relatorio-diario.md`, plus the sprint templates. No code reads, parses, validates, or
   writes any of these until patterns emerge from manual use.
2. **Pattern threshold.** Code only emerges after **5+ manual logs** of the same shape have
   accumulated for a given entity or workflow. Until that threshold is crossed, the workflow
   stays a markdown surface + a checklist.
3. **Templates are the contract.** YAML frontmatter (`type`, `period`, `date_start`, `date_end`,
   `verdict`, `verdict_score`, plus per-entity keys) is the persistent contract. When code is
   added, it reads and writes these files — never invents a parallel data structure.
4. **Boulder scope = observation first.** Future boulder-style plans should budget the first
   week of a wave to **manual logging + reflection**, not engineering. Engineering sprints
   start in week 2 of the wave.
5. **Cohort boundaries are stable.** Refactor between waves. Never mid-wave.

This pivot is meant to surface what the user actually does repeatedly, so that code invests its
budget in those surfaces, not in abstractions anticipating hypothetical use.

---

## 4. Behavioral rules for future agents

Rules are **imperative**, not advisory. An agent that violates them without a documented
sentinel case (see §6) has missed this note.

- **Before designing an entity, observe how the user logs the activity manually for 2 weeks.**
  If the manual log does not surface a stable shape, the entity does not get a Pydantic class
  yet.
- **Before adding a CLI command, count how many times the user did the underlying workflow
  manually in the last 30 days.** If that count is below 3, the CLI command waits.
- **Before writing a test, confirm there is real production data behind it.** Tests that
  exercise mock-only flows are deleted, not "fixed".
- **Refuse any feature request that lacks a "manual work-around" demonstration.** A request of
  the form "build me X" must be accompanied by "and here is how I did X by hand five times."
- **Templates are immutable once in use; refactor only between cohorts (between waves).** A
  template that has been filled at least once cannot be redesigned mid-wave.
- **When the user says "log this," prefer appending to a markdown file over adding to a
  structured repo.** A text append is auditable; a structured repo entry requires a schema
  decision.
- **Prefer narrowing the surface over widening it.** Remove a screen / repo / command before
  adding its replacement.
- **Every new module must declare its data lineage.** If a value is computed, the source values
  and the algorithm must be on the screen at most 1 click away.
- **Do not introduce new dependencies mid-wave.** Even "small" deps shift upgrade pressure.
- **The IKIGAi 5-vector scoring (passion / skill / market / revenue / course) is not yet
  validated by manual use.** Treat it as a hypothesis, not a fact. See §7.

---

## 5. Anti-patterns to avoid

- **Matrix explosion.** More rows × more columns × more derived metrics than the user can hold
  in working memory (7 ± 2). The KPI dashboard of death is the canonical failure.
- **Premature CLI surface.** Adding `pav <subcommand>` for a workflow that is logged <3
  times/month. CLI surfaces have ongoing maintenance cost (argparse, `--json`, help text,
  tests) — they are liabilities, not features, until proven otherwise.
- **Abstract math theories without user-grounded motivation.** Q_HE composites, regret
  bounds, Bayesian priors, RICE, weighted blends — these are attractive because they are
  rigorous, but rigorous is only valuable when there is a downstream decision that the rigor
  improves. If the user is going to override the output anyway, the rigor is theater.
- **Frozen schemas as a power move.** `frozen=True, extra="forbid"` is correct for **mature**
  data shapes. It is wrong for **emergent** shapes, where the cost of getting the schema wrong
  is paid forward at every consumer.
- **Test counts as a goal.** "We have 2500 tests" is not a milestone; "we have N tests, each
  one guarding a behavior the user has actually exercised" is.
- **Refactor by analogy.** Seeing a pattern in a popular library and mirroring it without
  asking "does our context have the same forces?"
- **Auto-pivoting the user into a regime.** A policy engine that silently tightens the user's
  schedule, especially when the user has not asked for it, is hostile automation.
- **Frontmatter drift.** Adding more YAML keys to the same template without removing any.
  Frontmatter is a contract; contracts decay if they grow unboundedly.
- **"Tools" that are really just dashboards.** A TUI screen that shows a chart the user has
  never asked to see is a screen taking up time and attention.
- **Premature bidirectional sync.** A write-back loop from analysis to data before manual
  observation is complete produces drift that is invisible until it is structural.

---

## 6. When to break the rules

Sentinel cases — situations where the data-first rule does not apply and a design-first
approach is justified:

- **Performance** — When a manual workflow is timed and documented at >5s per execution, AND
  repetition is ≥ daily, optimization is justified. Document the before/after.
- **Security** — Anything involving credentials, filesystem writes outside the workspace, or
  external services must follow security-first design regardless of usage volume. No shortcuts.
- **Regulatory / compliance** — Audit trails, GDPR, financial records: the structure is dictated
  by law, not by observed use. Document the regulatory source.
- **Real-time correctness** — When a delayed feedback loop would cause data loss or corruption
  (e.g. concurrent writes to the same plan), correctness trumps observation. Document the
  hazard.
- **Interoperability locks** — When a contract change would break a downstream consumer that is
  out of our control (e.g. an exported CSV schema consumed by a script we cannot edit), the
  contract changes only with a migration plan, not by manual experiment.

For each sentinel case, the agent must write a one-paragraph justification in the PR /
boulder-evidence file before writing the code. "It's faster" or "users will like it" do not
count.

---

## 7. Open questions for the human

Future agents must NOT assume the following. Each is a hypothesis pending manual validation:

1. **Are the 5 IKIGAi vectors the right ones?** (passion / skill / market / revenue / course)
   Alternatives observed in adjacent frameworks: 4-vector (purpose / people / profit / planet),
   6-vector (adds "vitality" or "play"), 3-vector (essence / gift / service). The
   manual-experiment protocol of §3 will surface which axes the human reaches for. Until then,
   the 5-vector is a working hypothesis, not a fact.

2. **Is the 5×3×3 proportion (teste-de-fogo) actually 5 × 3 × 3 or some other product?**
   The current template encodes `Execucao (5 dias) : Analise (3 semanas) : Planejamento (3
   meses)` and a 5-dimension Teste de Fogo. The product-form of the formula
   (`verdict_score = (media_teste_fogo * 0.5) + (leading_cumprido * 0.3) +
   (histerese_sustentada * 0.2)`) is one of several; the human may settle on a multiplicative
   or a max-of-factors shape after manual use.

3. **Should the dream template be a 1-year or 3-year horizon?** The current
   `01-sonho.md`-shaped entity inherits from a dream horizon that is **unvalidated**. Q3 2026
   is the first manual instance; the answer comes from filling it.

4. **What does the user actually do during a 30-min pomodoro vs. a 90-min deep block?**
   The Pomodoro state machine has 8 states and a scenario classifier. Two open questions:
   (a) does the user actually distinguish 30- and 90-min blocks, or does the form collapse to
   "focused vs. unfocused"; (b) does the post-block ritual ever run, or is it always deferred?

5. **Is there a daily mode (morning setup + evening review) or only a weekly cadence?**
   The `05-relatorio-diario.md` exists, but actual daily filling has not been observed. Until
   ~14 daily logs accumulate, the daily mode is a surface, not a behavior.

6. (Bonus, less critical) **The `_findings.md` / `_progress.md` / `_logs/{date}.md` triple**
   from the planning-with-files proposal — is the 3-file-per-Dream structure load-bearing, or
   does it collapse to one file when the human hits it manually?

Future agents should not pre-decide any of these. They should let the 5-log threshold resolve
them in turn.

---

## 8. How to read this note

1. **Read §1 first.** Confirm the pivot is still active. If the human has reverted to
   design-first (rare; check `.omo/boulder.json` for any "PAV-pivot-revert" marker), stop
   following §3-§5 and resume standard practice.
2. **Read §2.** Recognize the anti-patterns before you propose something that looks like them.
3. **Read §4 aloud as a checklist** before proposing any design change. If you can't tick
   every box, your proposal is not ready.
4. **Hold §7 in mind** as a list of things you must NOT pretend to know.
5. **Cite §6** if you are about to break one of the rules — the one-paragraph justification
   goes into the boulder evidence file.
6. **Treat §8 (this section) as ritual, not waste.** The 60 seconds it takes is cheaper than
   the hours it saves.

If the human overrides this note in chat ("I know the rules, please do X") — respect that
override for that single request, but the note stands for the next request. Each override is a
data point; consider whether it is rising to the level of "this rule should change," and if so,
update this file at the **end** of the wave, never mid-wave.

---

*Last revised: 2026-07-02 · Wave boundary · Pivot active · Owner: human · Owner-of-record:
IKIGAi Sys-00 (governance) · Will be revisited between waves.*
