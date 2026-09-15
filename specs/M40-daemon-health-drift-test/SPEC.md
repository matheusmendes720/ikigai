---
name: M40-daemon-health-drift-test
description: Drift test asserting M39 daemon watchdog infrastructure stays healthy
constitution_refs:
  - tests_are_the_contract
  - state_on_disk_not_conversation
  - spec_driven_not_vibe_driven
status: DONE
owner: loop-orchestrator
created: 2026-09-15
---

# M40 — Daemon-Health Drift Test

## Goal

Add a drift test that asserts the M39 daemon watchdog infrastructure stays
healthy and won't silently regress. Locks in:
- daemon-watchdog.sh exists + executable
- schedules.json registers it with sane thresholds
- watchdog script contains the alert logic

## Acceptance Criteria

- [ ] `test_daemon_health_infrastructure` passes
- [ ] Drift net 68/68 PASS preserved (was 67)
- [ ] No code touched (only 1 test + 1 SPEC added)
