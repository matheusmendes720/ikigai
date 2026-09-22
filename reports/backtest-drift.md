# Backtest Drift Report

_Generated: 2026-09-22T02:21:21_

## ➡️  STABLE — total score delta = +0.00

| Dimension | Baseline | Current | Δ |
|-----------|----------|---------|---|
| `anchor_pass_rate_pct` | 95.8 | 95.8 | +0.00 = |
| `tool_coverage_pct` | 94.7 | 94.7 | +0.00 = |
| `schema_valid_pct` | 100.0 | 100.0 | +0.00 = |
| `scenario_pass_rate_pct` | 89.0 | 89.0 | +0.00 = |
| `total_score` | 94.5 | 94.5 | +0.00 = |

## Per-anchor drift (sorted by largest regression)

| # | Anchor | Baseline | Current | Δ | n_baseline | n_current |
|---|--------|----------|---------|---|------------|-----------|
| 1 | constitutional_sot_reader | 94% | 94% | +0% = | 55 | 55 |
| 10 | diagnostic_reporter | 100% | 100% | +0% = | 7 | 7 |
| 11 | cultural_voice_compliance | 94% | 94% | +0% = | 59 | 59 |
| 2 | dual_frame_temporal_tracker | 94% | 94% | +0% = | 59 | 59 |
| 3 | five_level_hierarchy_mapper | 94% | 94% | +0% = | 59 | 59 |
| 4 | tagging_system_conversant | 100% | 100% | +0% = | 11 | 11 |
| 5 | time_horizon_aware | 93% | 93% | +0% = | 58 | 58 |
| 6 | vault_write_mcp_enforcer | 100% | 100% | +0% = | 11 | 11 |
| 7 | taskdog_vault_propagation_driver | 92% | 92% | +0% = | 6 | 6 |
| 8 | plan_update_on_the_fly_reflector | 100% | 100% | +0% = | 10 | 10 |
| 9 | cross_routine_executor | 93% | 93% | +0% = | 55 | 55 |

## Tool coverage drift

**Newly covered**: 0


**Newly missing**: 0


**Unchanged**: 27

## Gap drift

Baseline gaps: 7 | Current gaps: 7 | Δ = +0

**New gaps (0)**:

- (none)

**Resolved gaps (0)**:

- (none)

**Persistent gaps (7)**:

- ⚠ `tool_server_missing` — taskdog_bulk_archive
- ⚠ `tool_server_missing` — taskdog_bulk_complete
- ⚠ `tool_server_missing` — taskdog_get_execution_rate
- ⚠ `tool_server_missing` — taskdog_get_executive_summary
- ⚠ `tool_server_missing` — taskdog_get_q_high_e_low_metrics
- ⚠ `tool_server_missing` — taskdog_search_tasks
- ⚠ `tool_under_exercised` — taskdog_remove_dependency

## Interpretation

Score stable at Δ+0.00. Run-to-run variance is bounded by task state at run time.

- **Anchor regressions** (top of table) deserve immediate investigation.
- **Newly missing tools** suggest a scenario dropped a tool from `expected_tools`, or the harness lost an action.
- **New gaps** are more actionable than persistent gaps (they're new regressions).
- **Persistent gaps** are stable failures — schedule them as separate workstreams.

