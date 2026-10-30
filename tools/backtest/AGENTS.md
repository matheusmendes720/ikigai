# tools/backtest/ — Backtest Harness & Vault Engine

**Score:** 9 (14 files, 100% code, 189 module-level symbols, 121 exports)
**Role:** the backtest/scoring pipeline and the production vault-mutation engine.

## OVERVIEW

Fourteen standalone CLIs, each `main(argv)` + `__main__`. Despite the directory name
this is **not** test-only: `vault_propagation.py` is the repo's vault-write engine, and
`audit_drift` is the most-referenced symbol in the tree (~106 references across 20 files).
No `__init__.py` — PEP 420 namespace package, imported as `tools.backtest.*`.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Vault write engine | `vault_propagation.py` | 828 LOC; `audit_drift`, `apply_toggle`, `preview_toggle`, `append_event` |
| Drift taxonomy | `vault_propagation.py` | 7 kinds: `unmarked_done`, `unmarked_open`, `phantom_task`, `planned_orphan`, `priority_mismatch`, `tag_mismatch`, `due_date_mismatch` |
| Vault-link regexes | `vault_propagation.py` | `CHECKBOX_VAULT_RE` (3 link forms), `PRIORITY_TAG_RE`, `TAGS_TAG_RE`, `DUE_TAG_RE` |
| Scenario generation | `seed_q3_scenarios.py` | `TASKDOG_TOOLS` (27), `CATEGORY_COUNTS` (7), `CATEGORY_EXPECTED_TOOLS` (7) |
| Tool coverage | `taskdog_exhaustiveness.py` | `build_coverage_report`; flags under-covered tools |
| Role anchors | `role_anchors.py` | `ROLE_ANCHORS` (11), `build_scenario_anchor_map`, `coverage_report` |
| Harness | `backtest_harness.py` | 1007 LOC; `CATEGORY_ACTIONS` dispatch, `TASKDOG_SERVER=http://127.0.0.1:8000` |
| Judge | `judge_llm.py` | `WEIGHTS`: anchor 0.40 / tool coverage 0.30 / scenario 0.20 / schema 0.10 |
| Report / diff | `backtest_report.py`, `backtest_drift.py` | `render_report`, `diff_scores`/`diff_anchors`/`diff_tools`/`diff_gaps` |
| Baseline store | `baseline_archive.py`, `baseline_integrity.py`, `baseline_sign.py` | `DEFAULT_BASELINES_DIR`, `SHA256SUMS`, `SHA256SUMS.gpg` |
| Drift baseline | `drift_baseline.py`, `drift_regression.py` | `ALL_KINDS` (7); `check` fails CI if a kind grows >10% |

## CONVENTIONS

- Canonical pipeline (`scripts/backtest/run_backtest.sh`): seed -> exhaustive coverage ->
  role anchors -> harness -> judge -> report -> drift -> archive -> integrity -> sign.
  Scenario defaults chain through `vault/drafts/q3-scenarios*.yaml`.
- Every module opens with a milestone docstring (`"""M114f — vault_diff.py (renamed
  semantically from vault_propagation.py)"""`) and 5 of 14 close with an `Honest scope:`
  paragraph stating what the tool does **not** prove.
- 7 modules insert the repo root into `sys.path` and suppress `E402`; the rest import
  `tools.backtest.*` lazily or rely on the caller's `sys.path`.
- `append_event` writes one JSONL record to `vault/.vault_events.jsonl` with
  `invariant: "VAULT_WRITE_INVARIANT"`, tz-aware `ts`, `event`, `rel_path`,
  `target_line`, `expected_text`, `actor`, `reason`, `ok`. Event names:
  `vault.toggle_applied`, `vault.toggle_refused`, `vault.reopen_applied`,
  `vault.reopen_refused`, `vault.audit`, `vault.refactor`.
- `audit_drift` is read-only. `apply_toggle` / `apply_reopen` are guarded: they require
  `preview_toggle` / `preview_reopen` to succeed first (`require_preview_ok=True`).
- `toggle_checkbox` refuses if the target line does not match `expected_text` — it will
  not flip an unrelated checkbox.

## ANTI-PATTERNS

- NEVER mutate `vault/` from anywhere except `append_event` and the guarded
  `apply_toggle`/`apply_reopen`. There is **no** auto-trigger on `life task done`;
  vault updates are an explicit agent decision.
- NEVER delete or rewrite audit-log lines. Rollback writes a *new* event; it never
  edits the log.
- NEVER change a drift-kind constant. `DRIFT_*` values are the shared vocabulary
  between `audit_drift`, the baselines, and the CI regression gate.
- NEVER let the harness abort mid-corpus. `backtest_harness.py` catches broad
  exceptions deliberately so one bad scenario does not kill the run.
- NEVER compare absolute drift counts. Baselines grow; `drift_regression.py` compares
  deltas and thresholds.
- NEVER regenerate `vault/drafts/q3-scenarios*.yaml` without an Action Plan and an
  explicit "go" — the vault is append-only.

## KNOWN DEFECTS

- `vault_propagation.py`'s docstring titles itself `vault_diff.py` and its CLI examples
  say `python tools/backtest/vault_diff.py` (5 occurrences). The real filename is
  `vault_propagation.py`.
- `taskdog_exhaustiveness.py`'s docstring says "each of the 26 taskdog-mcp tools";
  `TASKDOG_TOOLS` actually holds 27 entries.
