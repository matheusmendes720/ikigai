# Integration Backlog — Operational ↔ External Systems

> **Status:** Future / speculative. No code changes are planned in the
> current sprint. This document captures every external integration
> possibility the project has touched on (in PRDs, ADRs, or related
> sub-projects) and the work required to make each one production-ready.
>
> **Read first:** `docs/architecture/02-PERSISTENCE-LAYER.md` to
> understand the 3 storage backends, then this backlog for the
> *connectors* that will eventually read from / write to them.

---

## Table of Contents

1. [Strategic Context](#1-strategic-context)
2. [Integration Scorecard](#2-integration-scorecard)
3. [Tier 1 — Direct Taskwarrior Integration](#3-tier-1--direct-taskwarrior-integration)
4. [Tier 1 — ikigai / vibe-ops Bridge](#4-tier-1--ikigai--vibe-ops-bridge)
5. [Tier 2 — Biometric / Health Data](#5-tier-2--biometric--health-data)
6. [Tier 2 — Calendar / Time Blocking](#6-tier-2--calendar--time-blocking)
7. [Tier 3 — Knowledge / PKM](#7-tier-3--knowledge--pkm)
8. [Tier 3 — Observability / Telemetry](#8-tier-3--observability--telemetry)
9. [Tier 4 — Distant / Aspirational](#9-tier-4--distant--aspirational)
10. [Cross-Cutting Concerns](#10-cross-cutting-concerns)
11. [Decision Framework](#11-decision-framework)
12. [References](#12-references)

---

## 1. Strategic Context

The project sits at the intersection of three strategic axes already
documented in the parent monorepo:

- **Cluster 1 — Personal Productivity** (PAV operational system, this
  repo). Goal: track time, sleep, habits, focus. Already ships.
- **Cluster 2 — Project Execution** (PMO ↔ Taskwarrior, in
  `life-ops/life-tatics`). Goal: manage multi-day tasks across
  projects.
- **Cluster 3 — Studies & Lifelong Learning** (PKM, in `vibe-ops/`).
  Goal: connect what we study to why we study it (ikigai).

Operational (this repo) is the *sensory layer* — it captures the
micro-level signals (sleep, focus, blocks). To become a real OS, it
needs to:

- **Push data outward** to Cluster 2 (so a finished Pomodoro becomes a
  Taskwarrior UDA update)
- **Pull data inward** from Cluster 3 (so today's study goal adjusts
  the PUSH/MAINTAIN/REDUCE/RECOVER policy)
- **Ingest data from the body** (biometrics) so the cybernetic loop
  includes HRV, REM, etc.

This backlog enumerates every connector, the work needed, the
priority, and the cost in days.

---

## 2. Integration Scorecard

| Tier | System | Direction | Priority | Effort | Status | Sprint |
|------|--------|-----------|----------|--------|--------|--------|
| 1 | Taskwarrior (binary) | push | P0 | 1-2d | ⬜ not started | next |
| 1 | ikigai / vibe-ops | pull | P0 | 2-3d | ⬜ not started | next |
| 2 | Garmin Connect | pull | P1 | 2-3d | ⬜ not started | +2 |
| 2 | Oura Ring | pull | P1 | 2-3d | ⬜ not started | +2 |
| 2 | Apple Health | pull | P1 | 2-3d | ⬜ not started | +2 |
| 2 | Google Calendar | pull/push | P1 | 3-4d | ⬜ not started | +3 |
| 2 | Cron / Task Scheduler | push | P1 | 1d | ⬜ not started | +3 |
| 3 | Obsidian vault | push | P2 | 1-2d | ⬜ not started | +4 |
| 3 | Logseq | push | P2 | 1-2d | ⬜ not started | +4 |
| 3 | Anki SRS | pull | P2 | 1-2d | ⬜ not started | +5 |
| 3 | Prometheus metrics | push | P2 | 1d | ⬜ not started | +5 |
| 3 | OpenTelemetry traces | push | P2 | 2d | ⬜ not started | +5 |
| 4 | GitHub Issues | push | P3 | 2-3d | ⬜ not started | +6 |
| 4 | Linear | push | P3 | 2-3d | ⬜ not started | +6 |
| 4 | Notion | push | P3 | 2-3d | ⬜ not started | +7 |
| 4 | Email (SMTP/IMAP) | pull | P3 | 1-2d | ⬜ not started | +7 |
| 4 | Calendar (CalDAV) | pull | P3 | 2-3d | ⬜ not started | +7 |
| 4 | Slack / Discord webhook | push | P3 | 1d | ⬜ not started | +8 |

**Legend:**
- **Direction:** pull = ingest data into operational / push = emit
  data to external system
- **Priority:** P0 = critical for the cybernetic loop / P1 = high
  value / P2 = nice to have / P3 = speculative
- **Effort:** estimated days of work (1 dev, 8h)
- **Sprint:** relative order ("next" = first backlog batch, "+2" =
  after the first batch, etc.)

---

## 3. Tier 1 — Direct Taskwarrior Integration

### 3.1 Background

Taskwarrior is already the project management substrate for Cluster 2
(life-tatics, life-ops/life-tatics/). The binary `task` lives in
`PATH` and is invoked via subprocess. The `tasklib` Python wrapper is
in the `vibe-ops/specs/` dependency list.

Currently the operational repo has zero awareness of Taskwarrior.
But every Pomodoro in `PomodoroRound` *should* eventually feed
back to a Taskwarrior annotation or UDA.

### 3.2 Work Required

1. **Add `tasklib` to `pyproject.toml`** (or a new
   `src/operational/connectors/taskwarrior.py` module).
2. **Create `TaskwarriorBridge` class** with:
   ```python
   class TaskwarriorBridge:
       def __init__(self, data_dir: Path = Path("~/.taskrc")): ...
       def list_active(self) -> list[Task]: ...
       def annotate(self, task_id: str, key: str, value: str) -> None: ...
       def complete(self, task_id: str) -> None: ...
       def add_uda(self, name: str, type: str, label: str) -> None: ...
   ```
3. **Define UDAs** in `~/.taskrc`:
   ```
   uda.pomodoros_completed.type=numeric
   uda.pomodoros_completed.label=Pomos
   uda.focus_score.type=numeric
   uda.focus_score.label=Foco
   uda.last_session.type=date
   uda.last_session.label=Última
   ```
4. **Hook into `PomodoroRound.upsert()`** in `cli/state.py` to push
   updates on every state transition.
5. **Add `operational task sync` subcommand** to manually flush
   pending events.
6. **Tests** in `tests/integration/test_taskwarrior_bridge.py` using
   a mock `tasklib.Task` with `monkeypatch`.

### 3.3 Risks

- **Taskwarrior is single-writer** — concurrent `task` commands from
  the OS could lose data. Use a lock file.
- **UDA schema changes** are disruptive. Bump a version tag in the
  data.
- **No network fallback** — Taskwarrior is local-only; works.

### 3.4 Effort: 1-2 days

### 3.5 Definition of Done

- [ ] `taskwarrior_bridge.py` exists
- [ ] `operational task list` shows active Taskwarrior tasks
- [ ] Completing a Pomodoro in operational updates
      `task <id> modify pomodoros_completed:N`
- [ ] Tests pass with a mock taskwarrior env
- [ ] Documentation updated

---

## 4. Tier 1 — ikigai / vibe-ops Bridge

### 4.1 Background

The `vibe-ops/` sub-project in the parent monorepo contains the
**ikigai cybernetic engine**. It defines a 4-quadrant
"reason-for-being" model (passion / mission / vocation / profession)
and computes setpoints for what to study/work on each day.

`vibe-ops/src/cybernetics/daily_loop.py` runs a Target-Sensor-Adjuster
loop. Currently it operates on a separate SQLite database
(`vibe_ops.db`) and does not consult the operational system.

### 4.2 Work Required

1. **Define the data contract** — what operational fields does the
   ikigai engine need? Probably:
   - Today's `DaySnapshot` (sleep, focus, energy, quadrant)
   - This week's `WeeklyReport` summary
   - Last 7 days of `DayContext` (orçado vs realizado trend)
2. **Create `src/operational/connectors/ikigai.py`**:
   ```python
   class IkigaiBridge:
       def __init__(self, vibe_db: Path = Path("vibe-ops/vibe_ops.db")): ...
       def get_today_setpoints(self) -> IkigaiSetpoints: ...
       def get_weekly_thesis(self) -> str: ...
       def report_day(self, snapshot: DaySnapshot) -> None: ...
   ```
3. **Expose via CLI**:
   - `operational ikigai pull` — fetch today's setpoints
   - `operational ikigai push` — push today's snapshot
   - `operational ikigai sync` — bidirectional
4. **Schema mapping** — convert operational's `DaySnapshot` to
   vibe-ops' `DailyLog` (Pydantic).
5. **Tests** with a fixture SQLite vibe_ops.db.

### 4.3 Risks

- **Schema drift** — vibe-ops is in active R&D (per
  `vibe-ops/IMPLEMENTATION_LOG.md`). Use Protocol-based duck typing.
- **Transactional consistency** — operational and vibe-ops both have
  their own JSON/SQLite. Use a periodic sync, not per-event.
- **Circular imports** — operational cannot import from vibe-ops.
  The bridge must be unidirectional (operational reads vibe-ops
  schema from a vendored copy of the types).

### 4.4 Effort: 2-3 days

### 4.5 Definition of Done

- [ ] `ikigai_bridge.py` exists
- [ ] `operational ikigai pull` returns today's setpoints
- [ ] `operational ikigai push` writes a DailyLog to vibe-ops
- [ ] Tests pass
- [ ] Cybernetic loop can read operational state

---

## 5. Tier 2 — Biometric / Health Data

### 5.1 Background

Sleep quality and recovery are core inputs to the operational
system. Currently they're self-reported (`SleepRecord.quality_score`
1-10). The next level is **objective** measurement from wearables.

### 5.2 Garmin Connect

1. **Library:** `garminconnect` (unofficial Python wrapper)
   - `pip install garminconnect`
2. **Module:** `src/operational/connectors/garmin.py`
3. **Auth flow:** OAuth token cached in
   `~/.config/garminconnect/token.json`. Need first-time
   interactive login.
4. **Data to pull:**
   - Sleep duration (replaces self-reported `bedtime`/`wake_time`)
   - Sleep stages (deep/light/REM) — populates `deep_sleep_pct`,
     `rem_sleep_pct`
   - HRV (rMSSD) — new field on `SleepRecord`?
   - Resting heart rate
   - Body battery
5. **CLI:** `operational biometric pull garmin --days 7`
6. **Tests:** mock the `garminconnect.Client` API.

### 5.3 Oura Ring

1. **Library:** `oura-python` (official)
   - `pip install oura-python`
2. **Module:** `src/operational/connectors/oura.py`
3. **Auth:** Personal Access Token (env var `OURA_PAT`)
4. **Data:** daily sleep, readiness, activity. Similar schema to
   Garmin.
5. **CLI:** `operational biometric pull oura --days 7`
6. **Tests:** mock the Oura API client.

### 5.4 Apple Health (iOS/macOS)

1. **No good Python library.** Need to either:
   - Use `health-auto-export` (REST bridge) — third-party iOS app
   - Parse `export.zip` from Health app manually
2. **Module:** `src/operational/connectors/apple_health.py`
3. **Data:** `HKCategoryTypeIdentifierSleepAnalysis` and HRV
4. **CLI:** `operational biometric pull apple-health --zip path/to/export.zip`
5. **Effort:** higher than Garmin/Oura due to parsing complexity.

### 5.5 Schema additions

Add to `SleepRecord` (entities/metric.py:101):
```python
hrv_ms: int | None = None
resting_hr_bpm: int | None = None
body_battery: int | None = None
source_detail: str | None = None  # "garmin:12345" for trace
```

Add a new `BiometricReading` entity for non-sleep data:
```python
class BiometricReading(BaseModel):
    id: UEID
    date: date
    metric: Literal["HRV", "RHR", "BODY_BATTERY", "STEPS", "SPO2"]
    value: float
    source: Literal["GARMIN", "OURA", "APPLE_HEALTH", "MANUAL"]
    created_at: datetime
```

### 5.6 Effort: 2-3 days per source

### 5.7 Risks

- **Auth tokens are sensitive** — store in OS keyring, not JSON
- **API rate limits** — Garmin: 1000 req/day; Oura: 5000/day. Plenty
- **Timezone handling** — Garmin reports in local time; Oura in UTC.
  Normalize via `pytz` or stdlib `zoneinfo`.

---

## 6. Tier 2 — Calendar / Time Blocking

### 6.1 Background

`TimeBlock` is already the operational abstraction for "I did X from
A to B". But it's currently only written manually. Real calendar
integration would pull events from external calendars and convert
them into `TimeBlock` records automatically.

### 6.2 Google Calendar

1. **Library:** `google-api-python-client` + `google-auth-oauthlib`
2. **Module:** `src/operational/connectors/google_calendar.py`
3. **Auth:** OAuth2 flow, token cached in
   `~/.config/operational/google_token.json`
4. **Data:** events with start/end, attendees, conference URLs
5. **Mapping:**
   - Calendar event → `TimeBlock` with `label=event.summary`
   - Mark `routine_id=None` (external, not internal routine)
   - Compute `period` from `event.start.hour`
6. **CLI:** `operational calendar pull google --days 7`
7. **Push:** `operational calendar push google` — write
   `TimeBlock`s back as events (e.g. Pomodoro blocks become
   "Focus time" events)

### 6.3 CalDAV (Nextcloud, Radicale, Fastmail)

1. **Library:** `caldav` (pure Python)
2. **Module:** `src/operational/connectors/caldav.py`
3. **Auth:** username + app password (env vars)
4. **URL:** `https://caldav.example.com/user/calendar/`
5. **Data:** VEVENT components
6. **CLI:** `operational calendar pull caldav --url ...`

### 6.4 Cron / Task Scheduler

1. **Trigger operational commands automatically**
2. **Module:** `src/operational/connectors/scheduler.py`
3. **For Windows:** PowerShell scheduled task
4. **For Unix:** crontab fragment
5. **Suggested schedules:**
   - Daily 23:55: `operational reflect auto --date today`
   - Weekly Sunday 23:59: `operational report weekly --save`
6. **CLI:** `operational scheduler install` — registers all default
   schedules

### 6.5 Effort

- Google Calendar: 3-4d (OAuth is finicky)
- CalDAV: 2-3d
- Cron/Task Scheduler: 1d

### 6.6 Risks

- **OAuth scopes** — request only what's needed
- **Token expiry** — handle refresh automatically
- **Conference URLs** — don't leak in logs; mask as `***zoom***`

---

## 7. Tier 3 — Knowledge / PKM

### 7.1 Background

Studies are a major quadrant of the cybernetic loop. Currently
operational has zero awareness of what is being studied — only
`pomodoros_completos` aggregates generic work.

The parent monorepo has `vibe-ops/src/pipeline/knowledge_telemetry.py`
and a `vibe-ops/specs/spec-cluster-plan-inputs.md` describing the PKM
side. This backlog item covers the operational side of that bridge.

### 7.2 Obsidian vault

1. **Library:** stdlib only — Obsidian is just Markdown + YAML
   frontmatter.
2. **Module:** `src/operational/connectors/obsidian.py`
3. **Data source:** `~/path/to/vault/**/*.md`
4. **What to write:**
   - Daily journal entry → `Journal/<date>.md` with frontmatter
   - Pomodoro log → `Sessions/<date>-<id>.md`
   - Day reflection → `Reflections/<date>.md` with OKRs
5. **Frontmatter template:**
   ```yaml
   ---
   type: daily_journal
   date: 2026-06-08
   operational_id: jou_2026_06_08
   pomodoros: 12
   quadrant: Q1
   sleep_hours: 8.0
   ---
   ```
6. **CLI:** `operational obsidian push --vault ~/Documents/Vault`

### 7.3 Logseq

1. **Similar to Obsidian** but uses bullet format (`- ` blocks)
2. **Module:** `src/operational/connectors/logseq.py`
3. **Output:** `journals/2026_06_08.md` (Logseq naming convention)

### 7.4 Anki SRS

1. **Library:** `anki` package + AnkiConnect plugin
2. **Module:** `src/operational/connectors/anki.py`
3. **Use case:** When a Pomodoro focuses on "Studying Anki deck X",
   pull the review stats (cards reviewed, retention rate) into a
   `StudySession` record.
4. **Effort:** 1-2d (AnkiConnect is well-documented)

### 7.5 Effort

- Obsidian: 1-2d
- Logseq: 1-2d (reuses 80% of Obsidian logic)
- Anki: 1-2d

### 7.6 Risks

- **Vault corruption** — never modify existing files, only append
- **YAML escaping** — be paranoid with quotes
- **Date format drift** — Logseq vs Obsidian use different defaults

---

## 8. Tier 3 — Observability / Telemetry

### 8.1 Background

The operational system has a "black box" crash logger
(`ui/logging_setup.py` → `logs/crash_report.log`). The next level is
**structured metrics** that can be scraped by external observability
stacks.

### 8.2 Prometheus

1. **Library:** `prometheus-client`
2. **Module:** `src/operational/connectors/prometheus.py`
3. **Endpoint:** `http://localhost:9464/metrics`
4. **Metrics to expose:**
   - `operational_sleep_hours` (gauge, per day)
   - `operational_pomodoros_total` (counter, per day)
   - `operational_quadrant` (gauge, 1-4, per day)
   - `operational_focus_score_avg` (gauge, per day)
   - `operational_commands_total{command=...}` (counter)
5. **CLI:** `operational metrics serve --port 9464`
6. **Tests:** scrape endpoint with `requests`, assert response

### 8.3 OpenTelemetry

1. **Library:** `opentelemetry-api`, `opentelemetry-sdk`,
   `opentelemetry-exporter-otlp`
2. **Module:** `src/operational/connectors/otel.py`
3. **Spans:**
   - `cli.command.invoke` (parent)
   - `cli.repo.upsert` (child)
   - `core.snapshot.compute` (child)
   - `ui.render` (child)
4. **Exporters:** OTLP/gRPC, console, or file
5. **CLI:** `operational otel enable --exporter otlp`
6. **Effort:** 2d (lots of instrumenting points)

### 8.4 Risks

- **Cardinality explosion** — be careful with label values
- **Performance overhead** — sampling in production

---

## 9. Tier 4 — Distant / Aspirational

### 9.1 GitHub Issues

1. **Use case:** A routine that's "in progress" syncs to a GitHub
   Issue with the same name. When complete, the issue is closed.
2. **Library:** `PyGithub`
3. **Mapping:**
   - `Routine` ↔ GitHub Issue
   - `RoutineLog` ↔ Issue comment
4. **Effort:** 2-3d

### 9.2 Linear

1. **Use case:** Same as GitHub Issues but for Linear users.
2. **Library:** `linear-sdk`
3. **Effort:** 2-3d

### 9.3 Notion

1. **Use case:** Push daily journal entries to a Notion database.
2. **Library:** `notion-client`
3. **Effort:** 2-3d

### 9.4 Email (SMTP/IMAP)

1. **Use case:** Read subject lines for a "send me tasks by email"
   workflow. Or send daily summaries.
2. **Library:** stdlib `smtplib` + `imaplib`
3. **Effort:** 1-2d

### 9.5 Slack / Discord webhook

1. **Use case:** Daily summary posted to a private channel.
2. **Library:** stdlib `urllib` + JSON
3. **Effort:** 1d

---

## 10. Cross-Cutting Concerns

These apply to **every** integration:

### 10.1 Configuration

All connector config goes through `LifeConfig` (or
`operational/config.py` if standalone). Use `pydantic-settings` for
env-var binding:

```python
class ConnectorConfig(BaseModel):
    garmin_email: str | None = None
    garmin_password: SecretStr | None = None  # never log this
    oura_pat: SecretStr | None = None
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
```

**Never log secrets.** Use Rich's masking in `ui/logging_setup.py`.

### 10.2 Error Handling

Every connector method must catch network errors and re-raise as a
`ConnectorError` (new domain exception):

```python
class ConnectorError(DomainError):
    """External system unreachable or returned invalid data."""
    def __init__(self, system: str, message: str, **ctx): ...
```

The CLI catches `ConnectorError` and renders an `error_panel` with
"retry" and "skip" actions.

### 10.3 Idempotency

Connectors must be **idempotent** — re-running a sync must not
duplicate data. Use:
- `created_at` timestamps on the source side
- Last-sync timestamp stored in `~/.time-tasker/connectors_state.json`
- Optimistic concurrency on Pydantic `UEID`

### 10.4 Rate Limiting

Build a token-bucket rate limiter into the base `Connector` class:

```python
class Connector:
    def __init__(self, rate_per_minute: int = 60): ...
    async def _rate_limited(self, fn): ...
```

### 10.5 Testing

- All connectors get a `MockConnector` subclass in
  `tests/connectors/mock_<name>.py`
- Integration tests use a fixture env var
  `OPERATIONAL_TEST_MODE=mock` to swap real → mock at runtime
- Live integration tests (`tests/integration/live/`) are opt-in via
  `pytest --live` to avoid accidental API calls

### 10.6 Schema Migrations

Every connector import may add new fields to entities. Follow the
**additive schema migration rule:**
- New fields: nullable, default `None`
- New entity types: registered in `state.py`, `csv_loader.py: MODEL_MAP`
- Removed fields: deprecated for 1 sprint, then removed

### 10.7 Versioning

Every connector sync writes a header to logs:

```
[2026-06-08 14:30:22] CONNECTOR taskwarrior sync v1.2.3 (schema=3)
```

Store the last-known schema version per connector. If the source
schema version changes, warn the user.

---

## 11. Decision Framework

When evaluating a new integration, ask:

| Question | If NO, defer |
|----------|--------------|
| Will it change the cybernetic loop? | Yes? P0. No? P2-P3. |
| Is the data source already in our control? | No? P3 (privacy risk). |
| Is the API stable? | No? Wait 1 quarter. |
| Do we already have a Python wrapper? | No? Add 1d to effort estimate. |
| Will it work fully offline? | No? (e.g. cloud-only API) P3. |
| Is it actively used by the user? | No? Drop it. |

**The rule of thumb:** if it doesn't feed the
Target-Sensor-Adjuster loop, it's a P3.

---

## 12. References

### Project documents

- `docs/architecture/02-PERSISTENCE-LAYER.md` — 3 backends, Repository Protocol
- `docs/architecture/05-DATA-FLOW.md` — request → controller → service → ui
- `docs/data/03-CONTRACTS.md` — layer-bridge contracts
- `docs/debug/COMMON-PITFALLS.md` — known integration issues

### Parent monorepo

- `../../vibe-ops/architecture/ADR-001-data-flow-topology.md` — the bigger picture
- `../../vibe-ops/specs/spec-cluster-plan-inputs.md` — PKM side
- `../../vibe-ops/pipeline/knowledge_telemetry.py` — what to push
- `../SPEC.md` — `life-tatics` (Cluster 2) integration
- `../../CLAUDE.md` — agent guide (full monorepo)
- `../../CONCEPTUAL_MODEL.md` — 5 tensions, 4 regimes
- `../../SYSTEMS_TOPOLOGY.md` — middleware map

### External SDKs (when ready to start)

- Taskwarrior: `tasklib` on PyPI, `taskwarrior.org`
- Garmin: `garminconnect` (unofficial, MIT)
- Oura: `oura-python` (official, MIT)
- Google Calendar: `google-api-python-client`
- Apple Health: `health-auto-export` (3rd-party iOS bridge)
- Obsidian: stdlib only (Markdown + YAML)
- Anki: `anki` + AnkiConnect HTTP API
- Prometheus: `prometheus-client`
- OpenTelemetry: `opentelemetry-python`

---

## Appendix A — Integration Architecture Diagram

```
                       ┌─────────────────────────────┐
                       │      OPERATIONAL (this)      │
                       │   src/operational/connectors │
                       └──────────────┬───────────────┘
                                      │
        ┌─────────────┬───────────────┼───────────────┬──────────────┐
        │             │               │               │              │
   ┌────▼────┐   ┌────▼────┐   ┌──────▼──────┐  ┌────▼────┐  ┌─────▼─────┐
   │Taskwar. │   │ ikigai  │   │  Biometric  │  │ Calendar│  │  PKM      │
   │ (push)  │   │ (pull)  │   │   (pull)    │  │ (both)  │  │  (push)   │
   └────┬────┘   └────┬────┘   └──────┬──────┘  └────┬────┘  └─────┬─────┘
        │             │               │               │              │
        ▼             ▼               ▼               ▼              ▼
   ┌─────────┐  ┌──────────┐   ┌──────────┐   ┌──────────┐  ┌──────────┐
   │  UDA    │  │  Daily   │   │ Sleep    │   │ Calendar │  │  Vault   │
   │ + annot │  │  Log     │   │ Record   │   │  Event   │  │  .md     │
   └─────────┘  └──────────┘   └──────────┘   └──────────┘  └──────────┘
   Cluster 2     Cluster 3      Cluster 1      Cluster 1     Cluster 3


   ┌─────────────────────────────────────────────────────────────┐
   │                  OBSERVABILITY (push)                        │
   │   ┌─────────────┐   ┌──────────────┐   ┌──────────────┐     │
   │   │ Prometheus  │   │  OpenTelemetry│   │   Logs       │     │
   │   └─────────────┘   └──────────────┘   └──────────────┘     │
   └─────────────────────────────────────────────────────────────┘
```

---

## Appendix B — When NOT to Integrate

This is equally important. **Don't integrate if:**

- The data source is unreliable (you'll debug the connector, not your
  data)
- The API requires constant maintenance (versioning is a tax)
- The user already has a manual workflow that works
- The integration would create a privacy concern (e.g. uploading
  sleep data to a third party without informed consent)
- The benefit is purely aesthetic ("it would be cool to see my Oura
  score in operational") and doesn't feed the cybernetic loop

The operational system is **already feature-complete** for personal
use. Every integration is a **trade-off** between added value and
added complexity. Apply YAGNI ruthlessly.

---

*Last updated: 2026-06-08 — initial backlog created from current
state of parent monorepo. Future revisions should add rows, not edit
existing ones (append-only).*
