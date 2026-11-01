# tools

Offline analysis and vault-mutation CLIs. Earns its file: score 9 (100% code,
169 symbols, 268 referencing files) — a distinct domain (operator tooling, not
runtime product code).

## OVERVIEW
Two independent subtrees, neither importable as a package (no `__init__.py`;
PEP 420 namespace packages). `tools/backtest/` is the deterministic backtest
and drift pipeline; `tools/vault/` is the CLI façade over the vault write path.
Both are invoked as `python tools/<dir>/<module>.py`, which puts the repo root
on `sys.path` — that is what makes `from tools.backtest.X import ...` resolve.

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| Vault ⇄ taskdog drift audit | `backtest/vault_propagation.py` | 828 lines; `audit_drift` is 236 lines / 56 branches — the choke point of the whole pipeline |
| Checkbox toggle / reopen (the write path) | `backtest/vault_propagation.py` | `preview_toggle`/`apply_toggle`, `preview_reopen`/`apply_reopen` |
| Drift snapshot + regression gate | `backtest/drift_baseline.py`, `backtest/drift_regression.py` | `exit 1` on regression = CI gate |
| Backtest harness | `backtest/backtest_harness.py` | 1007 lines, 20 `_act_*` action handlers |
| Vault search CLI | `vault/search.py` | full-text + glob + frontmatter `kind` filter |
| Vault rollback | `vault/rollback.py` | reverses `vault.toggle_applied` / `vault.reopen_applied` |
| Audit-log rotation | `vault/log_rotation.py` | archives, never deletes |
| Thin CLIs over the write path | `vault/apply_toggle_cli.py`, `reopen_cli.py`, `audit_drift_cli.py` | façades; all logic stays in `vault_propagation` |

## CONVENTIONS
- **Milestone-tagged module docstrings.** Every module opens
  `"""M<num> — <name>.py ..."""` (`M114a`–`M139`, `M163`–`M190`). The M-number is
  the tracker ID and reappears in inline comments, so history is traceable
  without git blame.
- **Absolute imports only.** Cross-module imports are
  `from tools.backtest.<mod> import ...`; there is no relative-import form.
- **CLI-per-tool layout.** Each module is a standalone `argparse` program with
  `main()` and usually `--dry-run`; output goes to files under `reports/`,
  not stdout-only. Subcommand style (`argparse` subparsers) is used only by
  `baseline_archive`, `baseline_integrity`, `baseline_sign`, `drift_baseline`.
- **The vault write path is preview-gated.** `apply` refuses unless the
  matching `preview` succeeded; `--force-preview-skip` exists for trusted
  scripts only. Every mutation appends to `vault/.vault_events.jsonl`.
- `tools/vault/reopen_cli.py` reuses `_resolve_plan_path` from
  `tools/vault/apply_toggle_cli.py` — do not fork a second copy.

## ANTI-PATTERNS
- **Never flip an unrelated checkbox.** `apply_toggle`/`apply_reopen` require
  an exact line match; a mismatch is a refusal, not a fuzzy write.
- **Never mutate `vault/.vault_events.jsonl` in place.** It is append-only.
  `rollback.py` writes a NEW `vault.rollback_applied` event;
  `log_rotation.py` MOVES old events into `<path>.<N>.archived.jsonl`.
- **Never compare absolute drift counts.** Baselines grow with the corpus, so
  `drift_regression.py` compares relative growth (>10% by default) and treats a
  new drift kind appearing 0 → >0 as a regression.
- **Never let the LLM judge become mandatory.** `llm_judge.py` falls back to
  the deterministic stub when `IKIGAI_FAKE_LLM=1`, `ANTHROPIC_API_KEY` is
  unset, or the model raises `ModelError`/`ConnectionError`.
- **Never abort the harness mid-corpus.** Failures are captured per scenario
  (`# noqa: BLE001 — harness must not abort mid-corpus`).
- `vault_propagation.py`'s docstring still says `python
  tools/backtest/vault_diff.py`; that file does not exist — the module was
  renamed to `vault_propagation.py`. Treat the documented command as stale.
- `tools/backtest/__pycache__/` carries `.pyc` for CPython 3.11, 3.12 and 3.14
  of the same 13 modules — stale three-way version drift checked into the
  tree.

## COMMANDS
```bash
python tools/backtest/vault_propagation.py --audit
python tools/backtest/drift_regression.py check --threshold 0.10   # exit 1 = regression
python tools/vault/search.py "termo" --glob 'drafts/*.md' --format json
python tools/vault/rollback.py list --since 24
python tools/vault/log_rotation.py status
```
