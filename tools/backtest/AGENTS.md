# tools/backtest

The deterministic backtest + drift pipeline. Earns its own file: score 9 (100%
code, 140 symbols, 71 exports, 29 referencing files including `tests/` and
`.github/workflows/ci.yml`) — a distinct domain from the rest of `tools/`.

## OVERVIEW
Scenario → harness → judge → report, with a parallel drift branch (snapshot →
baseline archive → integrity manifest → signature → regression gate).
Everything here runs without an LLM unless explicitly asked for one.

## WHERE TO LOOK
| Stage | Module | Role |
|-------|--------|------|
| Scenario seed | `seed_q3_scenarios.py` | `TASKDOG_TOOLS`, `CATEGORY_COUNTS`, `CATEGORY_EXPECTED_TOOLS` |
| Coverage padding | `taskdog_exhaustiveness.py` | one scenario per tool × category |
| Role anchors | `role_anchors.py` | `ROLE_ANCHORS`, `coverage_report`, gap-scenario synthesis |
| Harness | `backtest_harness.py` | `run_scenarios`, `CATEGORY_ACTIONS`, `TOOL_ACTIONS`, `TOOLS_NEED_TASK_ID` |
| Rule-based judge | `judge_llm.py` | deterministic scoring of harness results |
| LLM judge | `llm_judge.py` | optional second opinion over the rule-based judgment |
| Report | `backtest_report.py` | `render_report` (142 lines) → markdown |
| Drift | `vault_propagation.py` | `audit_drift` + 7 `DRIFT_*` kinds |
| Drift baseline | `drift_baseline.py` | `DEFAULT_DRIFT_DIR`, `ALL_KINDS`, `FILENAME_RE` |
| Regression gate | `drift_regression.py` | relative comparison, `exit 1` on regression |
| Drift diff | `backtest_drift.py` | current vs baseline snapshot |
| Baseline archive | `baseline_archive.py` | first-wins same-day archive |
| Baseline integrity | `baseline_integrity.py` | `sha256sum -c` compatible manifest |
| Baseline signing | `baseline_sign.py` | GPG sign / verify / rotate passphrase |

## CONVENTIONS
- **7 drift kinds, one tuple of constants.** `DRIFT_UNMARKED_DONE`,
  `DRIFT_UNMARKED_OPEN`, `DRIFT_PHANTOM_TASK`, `DRIFT_PLANNED_ORPHAN`,
  `DRIFT_PRIORITY_MISMATCH`, `DRIFT_TAG_MISMATCH`,
  `DRIFT_DUE_DATE_MISMATCH`. `ALL_KINDS` and `FILENAME_RE` are shared by
  `drift_baseline.py` and `drift_regression.py` — renaming the snapshot
  filename format silently breaks the regression loader.
- **Audit marker.** `INVARIANT_MARKER = "VAULT_WRITE_INVARIANT"` is the §7
  per-algorithm-attribution marker for the only code path allowed to mutate
  vault content outside explicit human edits.
- **Harness transports.** The harness talks to a real `taskdog-server` at
  `http://127.0.0.1:8000` and falls back to the `taskdog` CLI;
  `--skip-server-check` bypasses the pre-flight probe.
- `backtest_harness.py` is the widest module in the tree (30 functions, 20 of
  them `_act_*` HTTP/CLI action handlers). `audit_drift` is the complexity
  concentration (56 branches) and the most-referenced symbol (21 refs across
  4 modules).

## ANTI-PATTERNS
- **Never auto-trigger a vault update on `life task done`.** The vault is the
  source of truth, taskdog is the operational timeline; vault updates are an
  explicit agent decision made during Rotina Inicial/Final.
- **Never let `baseline_archive` write twice in one day.** It is first-wins
  per day (M118); a second run still produces reports but no second archive.
- 11 of the 37 files in the `scripts/` + `tools/backtest/` scope are one-shot
  codemods or live probes with no in-tree test coverage.

## COMMANDS
```bash
python tools/backtest/seed_q3_scenarios.py --out vault/drafts/q3-scenarios.yaml
python tools/backtest/taskdog_exhaustiveness.py --out vault/drafts/q3-scenarios.exhaustive.yaml
python tools/backtest/role_anchors.py --out vault/drafts/q3-scenarios.with-anchors.yaml
python tools/backtest/backtest_harness.py --out reports/backtest-Q1-results.json
python tools/backtest/judge_llm.py --harness-results reports/backtest-Q1-results.json
python tools/backtest/backtest_report.py --out reports/backtest-Q1.md
python tools/backtest/drift_baseline.py snapshot
python tools/backtest/drift_regression.py check --threshold 0.10 --json
python tools/backtest/baseline_integrity.py verify
python tools/backtest/baseline_sign.py status
```
