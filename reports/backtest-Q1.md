# Backtest Q1 — 2026-09-22 → 2026-10-19

_Generated: 2026-09-22T02:14:49_

## TL;DR

**94.5 / 100** — backtest of 73 deterministic scenarios through real taskdog-server.

| Metric | Value |
|--------|-------|
| Scenarios PASS | 65 |
| Scenarios SKIP | 8 (lifecycle-blocked, expected) |
| Scenarios ERROR | 0 |
| Tools exercised | 20 unique |
| Anchors met | 11 of 11 |
| Elapsed | 3.325s |

## Score breakdown

| Dimension | Weight | Score |
|-----------|--------|-------|
| Anchor pass rate | 0.40 | 95.8% |
| Tool coverage | 0.30 | 94.7% |
| Schema valid | 0.10 | 100.0% |
| Scenario pass rate | 0.20 | 89.0% |
| **TOTAL** | 1.00 | **94.5/100** |

## Per-anchor coverage

| # | Anchor | Scenarios | PASS | SKIP | ERROR | Pass rate |
|---|--------|-----------|------|------|-------|-----------|
| 7 | taskdog_vault_propagation_driver | 6 | 5 | 1 | 0 | 92% ⚠ |
| 9 | cross_routine_executor | 55 | 47 | 8 | 0 | 93% ⚠ |
| 5 | time_horizon_aware | 58 | 50 | 8 | 0 | 93% ⚠ |
| 1 | constitutional_sot_reader | 55 | 48 | 7 | 0 | 94% ⚠ |
| 2 | dual_frame_temporal_tracker | 59 | 52 | 7 | 0 | 94% ⚠ |
| 3 | five_level_hierarchy_mapper | 59 | 52 | 7 | 0 | 94% ⚠ |
| 11 | cultural_voice_compliance | 59 | 52 | 7 | 0 | 94% ⚠ |
| 4 | tagging_system_conversant | 11 | 11 | 0 | 0 | 100% ✓ |
| 6 | vault_write_mcp_enforcer | 11 | 11 | 0 | 0 | 100% ✓ |
| 8 | plan_update_on_the_fly_reflector | 10 | 10 | 0 | 0 | 100% ✓ |
| 10 | diagnostic_reporter | 7 | 7 | 0 | 0 | 100% ✓ |

## Per-tool coverage

Coverage matrix: which tools the corpus expected vs. which the harness called.

| Tool | Expected | Actual | Covered |
|------|----------|--------|---------|
| `taskdog_bulk_archive` | 3 | 0 | ✗ |
| `taskdog_bulk_complete` | 3 | 0 | ✗ |
| `taskdog_create_subtask` | 0 | 4 | ✗ |
| `taskdog_get_execution_rate` | 3 | 0 | ✗ |
| `taskdog_get_executive_summary` | 3 | 0 | ✗ |
| `taskdog_get_q_high_e_low_metrics` | 3 | 0 | ✗ |
| `taskdog_remove_dependency` | 3 | 0 | ✗ |
| `taskdog_search_tasks` | 4 | 0 | ✗ |
| `taskdog_add_dependency` | 4 | 4 | ✓ |
| `taskdog_archive` | 3 | 3 | ✓ |
| `taskdog_cancel` | 3 | 3 | ✓ |
| `taskdog_complete_task` | 3 | 3 | ✓ |
| `taskdog_create_note` | 3 | 3 | ✓ |
| `taskdog_create_task` | 8 | 8 | ✓ |
| `taskdog_get_burndown` | 3 | 3 | ✓ |
| `taskdog_get_cognitive_debt_metrics` | 3 | 3 | ✓ |
| `taskdog_get_daily_allocations` | 7 | 7 | ✓ |
| `taskdog_get_metrics` | 3 | 3 | ✓ |
| `taskdog_get_task` | 3 | 3 | ✓ |
| `taskdog_list_notes` | 3 | 3 | ✓ |
| `taskdog_list_tasks` | 11 | 32 | ✓ |
| `taskdog_pause` | 3 | 3 | ✓ |
| `taskdog_reopen` | 3 | 3 | ✓ |
| `taskdog_set_deadline` | 3 | 3 | ✓ |
| `taskdog_set_priority` | 3 | 3 | ✓ |
| `taskdog_set_tags` | 3 | 3 | ✓ |
| `taskdog_update_task` | 3 | 3 | ✓ |

**Coverage**: 26 expected tools, 20 actually exercised, 7 missing.

## Tool invocation totals (from harness run)

| Tool | Times called |
|------|--------------|
| `taskdog_add_dependency` | 4 |
| `taskdog_archive` | 3 |
| `taskdog_cancel` | 3 |
| `taskdog_complete_task` | 3 |
| `taskdog_create_note` | 3 |
| `taskdog_create_subtask` | 4 |
| `taskdog_create_task` | 8 |
| `taskdog_get_burndown` | 3 |
| `taskdog_get_cognitive_debt_metrics` | 3 |
| `taskdog_get_daily_allocations` | 7 |
| `taskdog_get_metrics` | 3 |
| `taskdog_get_task` | 3 |
| `taskdog_list_notes` | 3 |
| `taskdog_list_tasks` | 32 |
| `taskdog_pause` | 3 |
| `taskdog_reopen` | 3 |
| `taskdog_set_deadline` | 3 |
| `taskdog_set_priority` | 3 |
| `taskdog_set_tags` | 3 |
| `taskdog_update_task` | 3 |

## Gaps identified

| Gap kind | Count |
|----------|-------|
| `tool_server_missing` | 6 |
| `tool_under_exercised` | 1 |

### Detail

- **[tool_server_missing]** `taskdog_bulk_archive` — Tool is in MCP spec but no HTTP endpoint on live taskdog-server. Either add endpoint, or mark tool as retired in spec.
- **[tool_server_missing]** `taskdog_bulk_complete` — Tool is in MCP spec but no HTTP endpoint on live taskdog-server. Either add endpoint, or mark tool as retired in spec.
- **[tool_server_missing]** `taskdog_get_execution_rate` — Tool is in MCP spec but no HTTP endpoint on live taskdog-server. Either add endpoint, or mark tool as retired in spec.
- **[tool_server_missing]** `taskdog_get_executive_summary` — Tool is in MCP spec but no HTTP endpoint on live taskdog-server. Either add endpoint, or mark tool as retired in spec.
- **[tool_server_missing]** `taskdog_get_q_high_e_low_metrics` — Tool is in MCP spec but no HTTP endpoint on live taskdog-server. Either add endpoint, or mark tool as retired in spec.
- **[tool_under_exercised]** `taskdog_remove_dependency` — Harness did not call this expected tool; add action coverage.
- **[tool_server_missing]** `taskdog_search_tasks` — Tool is in MCP spec but no HTTP endpoint on live taskdog-server. Either add endpoint, or mark tool as retired in spec.

## Methodology

- **Harness** (`backtest_harness.py`) runs 73 padded scenarios through real taskdog-server HTTP API.
- **Judge** (`judge_llm.py`) scores 4 dimensions: anchor pass rate, tool coverage, schema validity, scenario pass rate.
- **Anchors** = 11 role-anchor requirements from M113 v2 spec (drilled from strategics/ + algorithm-attribution-design.md).
- **Tools** = canonical 26 taskdog-mcp tool names (excludes server-missing tools from coverage denominator).
- **SKIP** = real-world blocker (task depends on upstream, lifecycle conflict); counted as 50% credit for anchor scoring.

## Next steps

- Resolve 6 `tool_server_missing` gaps: either add HTTP endpoints to taskdog-server, or mark tools as retired in `seed_q3_scenarios.py`.
- Fix 1 harness coverage gaps in `backtest_harness.py`.
- Consider adding **LLM-judge** dimension for qualitative scoring (was the response helpful, did it cite vault sources, etc.).
- Add **argument-validation** dimension: did the agent pass the right args to each tool?
- Wire `audit_drift` from M114f into the harness so anchor #7 (propagation driver) is exercised end-to-end.
