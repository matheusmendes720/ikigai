---
name: M80-invoke-skill-all-cadences
description: Wire invoke-skill weekly/monthly/quarterly cron entries; full automation loop closed
owner: matheus-mendes
status: DONE
milestone: M80
estimated_cost_usd: 0.10
constitution_refs:
  - correctness_over_speed
  - tests_are_the_contract
  - state_on_disk_not_conversation
---

# M80 - invoke-skill all-cadences cron wiring

## Context

M79 wired `invoke-skill-ikigai-daily`. M80 extends to all 4 IKIGAI
cadences (daily, weekly, monthly, quarterly) so the full automation
loop is closed.

## What changed

### .claude/loop/schedules.json

Added 3 new schedule entries:

| name | interval | interval_seconds |
|---|---|---|
| invoke-skill-ikigai-weekly | 10080m | 604800 (7 days) |
| invoke-skill-ikigai-monthly | 43200m | 2592000 (30 days) |
| invoke-skill-ikigai-quarterly | 129600m | 7776000 (90 days) |

Each schedule runs the corresponding `invoke-skill <name>` via the
M76 notify-wrap pipeline. MSYS path bug from M79 was re-applied
(canonical → MSYS-mangled) so daemon-manager.sh could find them.

## Acceptance

- [x] bash .claude/helpers/daemon-manager.sh list : 10/10 daemons RUNNING
  (was 7/7: added weekly, monthly, quarterly)
- [x] invoke-skill-ikigai-quarterly cron fires and writes to
       .life/logs/notifications.log: title "IKIGAI quarterly",
       rc=0 elapsed=1s
- [x] Taskdog failure path verified: quarterly manifest declares
       taskdog_create_task; with taskdog-server unreachable, the
       failure routes to review_queue (taskdog_pending_review_queue: true)
- [x] tests/ root : 318 PASS + 27 SKIP (no regression)

## Cadence summary

| Skill | Cadence | When | What |
|---|---|---|---|
| ikigai-daily | 24h | every day | surface_intentions (no post-processor) |
| ikigai-weekly | 7d | every week | taskdog_create_task: weekly priorities |
| ikigai-monthly | 30d | every month | vault_write only (no taskdog) |
| ikigai-quarterly | 90d | every quarter | taskdog_create_task: quarterly OKRs |

## Out of scope (M81+)

- Real LLM integration (currently FAKE_LLM=1)
- Per-skill notification templates (currently generic title)
- Slack/Discord adapters
