# tools/ — Local CLI Tooling

**Score:** 9 (20 files, 100% code, 225 module-level symbols, 141 exports, 42 importing files)
**Role:** standalone developer CLIs. Not a package: no `__init__.py`, not in the wheel.

## OVERVIEW

Two independent families of standalone scripts, both importable as
`tools.backtest.*` / `tools.vault.*` via PEP 420 namespace packages, and both run as
`python tools/<family>/<module>.py <args>`. They are **not** shipped: root
`pyproject.toml` declares only `packages = ["life", ...]`.

## STRUCTURE

```
tools/
├── backtest/   # backtest harness, judges, baselines, drift + the vault engine -> backtest/AGENTS.md
└── vault/      # 6 CLI wrappers over tools/backtest/vault_propagation.py
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Backtest pipeline modules | `backtest/` | 14 modules -> `backtest/AGENTS.md` for the module map |
| Vault mutation engine | `backtest/vault_propagation.py` | the write path; `audit_drift` is the repo's most-referenced symbol |
| Vault CLI wrappers | `vault/*.py` | `apply_toggle_cli`, `reopen_cli`, `rollback`, `search`, `audit_drift_cli`, `log_rotation` |
| `life v2` wiring | `interfaces/cli/v2.py` | registers `vault-preview/apply/toggle/reopen/rollback/search`, `audit-drift` |
| Baseline store | `reports/baselines/` | `SHA256SUMS` manifest, `SHA256SUMS.gpg` signature |

## CONVENTIONS

- Every module is a standalone CLI: `main(argv)` plus `if __name__ == "__main__": sys.exit(main(...))`.
  `tools/vault/` splits into three `main()` shapes — `main(argv)` with argparse
  (`rollback`, `search`, `log_rotation`), `main(cmd, *, ...)` (`apply_toggle_cli`), and
  keyword-only `main(*, ...)` (`reopen_cli`, `audit_drift_cli`).
- Exit-code contract across `tools/vault/`: `0` success, `1` refused / no match, `2` usage
  or runtime error. `tools/backtest/` uses argparse subparsers with `required=True`.
- `--dry-run` means "print, do not write" — present in the harness, judges, drift and
  rotation tools. Baseline archive/integrity/sign and `drift_baseline` have no dry-run.
- Repo-root resolution differs per module: `Path(__file__).resolve().parents[2]`
  (`vault/search.py`) vs `.parent.parent.parent` (`vault/rollback.py`) vs CWD-relative
  `Path("vault") / ".vault_events.jsonl"` (`vault/log_rotation.py` — only works from repo root).
- 7 modules patch `sys.path` themselves and suppress `E402`; `tools/vault/` instead
  imports `tools.backtest.*` lazily inside functions to keep `life v2 --help` fast.
- `tools/backtest/` and `tools/vault/` never import each other at module scope; the
  dependency runs `vault/` -> `backtest/`, one way.
- Module docstrings carry the milestone tag (`"""M131 — apply_toggle_cli.py`) and 5
  `tools/backtest/` modules close with an `Honest scope:` paragraph stating what the
  tool does *not* prove.

## ANTI-PATTERNS

- NEVER write to `vault/` from these tools outside `vault_propagation.append_event`.
  The audit log `vault/.vault_events.jsonl` is append-only and every record carries
  `invariant: "VAULT_WRITE_INVARIANT"`.
- NEVER let `--dry-run` create or modify a file. It is a read-only preview.
- NEVER accept an absolute path or `..` traversal for a vault plan path;
  `_resolve_plan_path` raises `ValueError`.
- NEVER invert a rollback. `vault.rollback_applied` has no inverse handler — only
  `vault.toggle_applied` and `vault.reopen_applied` can be undone.
- NEVER treat `tools/backtest/` as test-only. `vault_propagation.py` is the production
  vault-write engine; `tools/vault/` is only a CLI facade over it.
- NEVER use `tools.backtest.judge_llm` against a real LLM in CI. Without
  `--use-llm` **and** `ANTHROPIC_API_KEY` the judge always stubs.
- NEVER commit the baseline passphrase. `reports/baselines/.passphrase` is gitignored.
