# PAV TUI Screen Survey — DATA-FIRST perspective

> Goal: render every PAV TUI screen against the actual markdown plans the user writes.
> The TUI is read-write for daily ops, but its read surfaces must mirror the strategy artefacts
> (`templates/`, weekly review, quarterly plan, IKIGAi). When a TUI screen does not surface what
> the user already wrote down on paper, the TUI is silently under-using the data we have.

> Note: `life-ops/operational/CLAUDE.md` says **7** screens. The actual `SCREENS` dict in
> `apps/tui/src/operational/tui/app.py` contains **8 main + Help modal** = 9. We index all 9 here.

---

## 1. The 9 screens (current state)

| # | Screen | Purpose (1 line) | Data shown | Actions available | Daily-use frequency |
|---|--------|------------------|------------|-------------------|---------------------|
| 1 | `dashboard` | Today's snapshot — 4 KPIs + 3 sparklines + regime + pomo grid + next step | `DaySnapshot` (sleep h, pomodoros done/meta, energy 1-10, focus 1-10, regime, pomo grid, computed `next_step`) | (none screen-local; global `1`–`8` + `q` + `Ctrl+H` + auto-refresh every 2 s) | **HIGH** |
| 2 | `daily_flow` | Today's blocks split by MANHA/TARDE/NOITE | `time_blocks` repo filtered by today's date + period | `prev_period`, `next_period`, `toggle_tab` (←/→/t) | **HIGH** |
| 3 | `pomodoro_timer` | Active FSM-driven timer (WORK/BREAK/LONG_BREAK) | `PomodoroTracker` runtime + `pomodoros` repo (persisted rounds) | `start_timer`, `pause_timer`, `skip_break`, `abort_timer` (s/p/./a) + 4 buttons | **MEDIUM** |
| 4 | `habits` | All habits with streak + Q_HE + 30-day completion chart | `habits` repo + `routine_logs` repo (current streak, best streak, Q_HE) | `add_habit`, `edit_habit`, `delete_habit`, `filter_habits` (a/e/d/f — **all stub notifications**) | LOW |
| 5 | `journal` | Recent journal entries with live search filter | `journals` repo (entry_text, desvios, licoes, energia, foco) | `focus_search`, `new_entry`, `filter_entries` (//n/f — create is a stub) | MEDIUM |
| 6 | `metrics` | Historical sleep/energy/focus charts, 7d or 30d window | `sleep_records`, `journals` (for energy/focus) over last N days | `7d` / `30d` toggle button | LOW |
| 7 | `policy` | Current regime + last 8 decisions + hysteresis thresholds | `policy_decisions`, `policy_setpoints` repos | `show_history`, `show_setpoints` (h/s — both notify-stubs) | LOW |
| 8 | `analytics` | 180-day storytelling — growth score, weekly Q_HE arc, regime timeline, correlations, scenarios, OLS forecast | 6-month CSV dataset via `operational.core.analytics` | (no user actions) | NONE |
| 9 | `help` | Ctrl+H modal — full keybinding reference | Static text only | `dismiss` (Esc / button / Ctrl+H) | LOW (only when stuck) |

---

## 2. Data shown per screen vs the markdown templates

| TUI screen | Equivalent markdown template section | Gap? |
|-----------|--------------------------------------|------|
| `dashboard` | `daily.md` ("Hoje" — KPIs + regime + next step) + `template_diario.md` Cabeçalho | partial — KPIs yes, but "Plano para Amanhã" from yesterday is missing |
| `daily_flow` | `daily.md` Blocos (MANHA/TARDE/NOITE) + `template_diario.md` Cronograma | NO — block list is fine |
| `pomodoro_timer` | (no direct template — operational artefact) | NO |
| `habits` | `template_diario.md` Hábitos + `template_semanal.md` Revisão de hábitos | YES — no link to "dream → goal → habit" chain from `okr.md` |
| `journal` | `daily.md` Journal + `template_diario.md` Reflexões | YES — entries are flat; no link to weekly review id |
| `metrics` | `template_semanal.md` Métricas + `health.md` | YES — leading/lagging indicators not distinguished; no aggregation by período |
| `policy` | `template_semanal.md` Veredicto + `okr.md` Regimes | YES — last weekly review verdict is not surfaced |
| `analytics` | `report.md` quarterly (sonar/agg) | YES — does not break down by onda / sprint |
| `help` | (no template) | NO |

---

## 3. The gap (where TUI doesn't surface markdown plans)

The TUI reads from persistent state (`~/.time-tasker/`) but never joins back to the
*prose artefacts* the user wrote. Concretely:

- **Daily Flow** does not show today's "Plano para Amanhã" lifted from **yesterday's**
  daily report. (`daily.md` Section 4 is the canonical slot — TUI reads `time_blocks`
  only, never the markdown `out/`)
- **Pomodoro** screen does not show the **regime transition history** from the quarterly plan
  (`okr.md` / `template_trimestral.md`); pomo runs live, but its regime context lives in prose
- **Habits** screen does not show the **dream → goal → habit chain** (`okr.md` Dream section,
  `template_mensal.md` Goal, `template_diario.md` Habits) — habits are listed but never
  linked to the upstream strategic intent
- **Policy** screen does not surface the **verdict from last weekly review** (Estado Atual /
  blockers from `template_semanal.md`) — verdicts are inert text, never shown next to current
  regime
- **Metrics** screen does not aggregate **leading vs lagging indicators** from `sonhos.md`
  / `template_trimestral.md` — only raw sleep / energy / focus
- **Dashboard** does not show the **5-vector IKIGAi scoring over time** from
  `vibe-ops/base/IKIGAi.md` (Passion / Skill / Market / Revenue / Course)
- **Analytics** does not break down by **onda** (the quarterly theme from `okr.md`) — it
  treats the 180 days as a flat timeline
- **Journal** does not link to the **weekly review it belongs to** — entries are a flat
  reverse-chronological list with no parent reference

---

## 4. The over-engineering audit (per screen)

Widgets = unique `yield` / `mount` calls in the screen's `compose()` + dynamic children.
Actions = user-invokable methods exposed via `BINDINGS` or buttons (not counting global hotkeys).

| Screen | Widgets composed | Dynamic children | Actions (screen-local) | Observed in user practice? |
|--------|------------------|-------------------|------------------------|----------------------------|
| `dashboard` | 12 (Header, 4× KPI, 3× Chart, RegimeBar, PomoGrid, next-step Static, Footer) | 0 | 0 user actions (auto-refresh only) | YES — likely first screen of the day |
| `daily_flow` | 6 (Header, Tabs[3], period-content, empty-msg, Footer) | 1 per block (`TimeBlockDisplay`) | 3 | PARTIAL — shown during planning; data entry happens via CLI |
| `pomodoro_timer` | 11 (Header, title, Digits, status, fsm, state-label, 4× Button, Footer) + dynamic countdown ticks | 0 | 4 (s/p/./a + 4 buttons; state machine is well exercised) | YES during work blocks |
| `habits` | 6 (Header, filters, chart-label, PlotextChart, empty-msg, Footer) | 1 per habit (`HabitStreakDisplay`) | 4 (a/e/d/f — **all notify-stubs**, no real handler) | NO — read-only browse; CRUD is CLI |
| `journal` | 7 (Header, Input, date-filter, period-filter, entries-list, empty-msg, Footer) | 1 per entry (Static) | 3 (//n/f — `n` is notify-stub) | PARTIAL — search works, create is CLI |
| `metrics` | 13 (Header, 2× Button, 4× Label, 4× Chart, sleep-debt, Footer) | 0 | 1 (7d/30d toggle) | LOW — historical, passive |
| `policy` | 8 (Header, 2× title, RegimeBar, setpoint-detail, decisions-list, hysteresis, Footer) | 0 | 2 (h/s — **both notify-stubs**) | LOW — read-only introspect |
| `analytics` | 9 (Header, header-static, 6× panel Static, Footer) | 0 | 0 | **NO** — bound to the 6-month CSV dataset that ships as separate fixture; user never opens it in normal flow |
| `help` | 9 (Container + 6 section statics + Button) | 0 | 1 (dismiss) | LOW (only when stuck) |

**Stubs total**: 5 (`habits.add`, `habits.edit`, `habits.delete`, `journal.new`, `policy.history`, `policy.setpoints` via notify → `use CLI`)

---

## 5. Recommendations for v0.5 (data-first path)

| Screen | Verdict | Rationale |
|--------|---------|-----------|
| `dashboard` | **KEEP** | The "Today" entry point — mirrors `daily.md`. Daily-use HIGH. |
| `daily_flow` | **KEEP** | Mirrors `daily.md` Blocos. Must add: "Plano para Amanhã" read from yesterday's report. |
| `pomodoro_timer` | **KEEP** | Operational artefact; FSM is the load-bearing primitive. |
| `habits` | **SIMPLIFY** | Replace dynamic `HabitStreakDisplay` list with **read-only stream grouped by category** (the spec is daily, not edit-here). Surface the dream→goal→habit chain (read from `okr.md` frontmatter). Keep 30-day completion chart. Drop a/e/d/f bindings (they're stubs). |
| `journal` | **SIMPLIFY** | Drop `f` (stub). Keep search (`/`) and read-only list. Add a `weekly_review_id` backlink when the entry falls inside a weekly-review window. New entry stays CLI. |
| `metrics` | **DEFER** | The CLI `pav metrics` + markdown weekly digest already cover this. Cut from v0.5; revisit after the v0.5 manual-only loop validates daily usage. |
| `policy` | **DEFER** | Read-only "what's my regime?" is one line; the FSM itself is exercised via CLI. Surface the weekly verdict in `dashboard` instead. |
| `analytics` | **DEFER** (or DELETE) | Bound to a 180-day CSV fixture; never observed in user practice. The 6-month storytelling belongs in a markdown report, not in the daily-driver TUI. |
| `help` | **KEEP** | Low-cost safety net for the 1–2 screens we keep. |

---

## 6. What replaces each deferred screen in the manual workflow

| Deferred TUI screen | Markdown / CLI replacement |
|---------------------|----------------------------|
| `metrics` | `pav metrics` (CLI JSON) → paste into `template_semanal.md` Section "Métricas" |
| `policy` | `pav policy show` (CLI) + the "Verdicto" block in `template_semanal.md` |
| `analytics` | `pav report weekly` generates the markdown digest directly into `out/` |
| `habits` (CRUD stubs) | `pav habit create / edit / delete` (CLI Typer commands already exist) |
| `journal` (create stub) | `pav journal create --text ...` |

---

## 7. The minimum viable TUI surface (v0.5)

Three screens — the daily-driver surfaces that mirror markdown plans:

1. **Dashboard** — today's snapshot + "Plano para Amanhã" lifted from yesterday's daily report
2. **Daily Flow** — MANHA/TARDE/NOITE blocks + the "Plano para Amanhã" header
3. **Pomodoro Timer** — the one operational primitive that earns its own screen

Plus the **Help modal** (Ctrl+H) — unchanged.

**Cut:** `habits`, `journal`, `metrics`, `policy`, `analytics`. Net: **6 screens removed**, 3
kept (+ Help). Roughly halve the TUI surface area in `apps/tui/src/operational/tui/screens/`.

---

## 8. Open question for the human

**Which 1–2 screens do you ACTUALLY open daily?**

The TUI surface exists because real data lives there. But our best evidence about *which*
data you reach for first is:

- `git log -- apps/tui/src/operational/tui/screens/` — which screens are you actually touching?
- `~/.time-tasker/` access patterns — which repo is read the most?
- the **3 most-edited markdown templates** in `strategics/` or `docs/templates/` — those
  tell us what the TUI *should* mirror

If the answer is "Dashboard + Pomodoro" → v0.5 ships 2 screens + help + a richer `pav
home` interactive menu to cover the rest. If "Dashboard + Daily Flow" → Pomodoro becomes a
CLI subcommand. The honest answer is what unlocks the v0.5 cut — please reply with the
1–2 screens + the three markdown templates you touch most this week.
