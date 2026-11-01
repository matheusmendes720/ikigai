# .github

CI workflows, the PR-review orchestrator and the repository's GitHub metadata.
Earns its file: score 13 (21 files, 74% code, 82 symbols, 61 referencing files)
— a distinct domain (automation, not product code).

## OVERVIEW
Two workflows plus a Python review orchestrator — the only consumer of `.github/scripts/`.

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| CI pipeline | `workflows/ci.yml` | 5 jobs: `code-review-checks`, `quality-gates`, `mcp-gateway-contract`, `review-queue-worker-contract`, `backtest-pipeline` |
| OpenWiki regeneration | `workflows/openwiki-update.yml` | daily 08:00 UTC (05:00 BRT); MiniMax gateway + LangSmith tracing |
| Review orchestrator CLI | `scripts/code_review.py` | `--base --files --type-only --test-only --missing --gate --json --package` |
| Shared process/env layer | `scripts/code_review_model.py` | `ROOT`, `CheckStatus`, `CheckResult`, `ReviewReport`, `PackageSpec`, `tool()`, `run()` |
| Package matrix | `scripts/code_review_topology.py` | `PACKAGES` (5), `Bucket`, `build_buckets()`, `diff_touched_lines()` |
| Individual checks | `scripts/code_review_checks.py` | mypy / ruff / ruff-format / naming / pytest / missing-tests (564 lines) |
| Worktree helper | `scripts/git_worktree_manager.py` | `--list --add --remove --prune` |
| Project board | `scripts/project_board.py`, `scripts/project_board_setup.py` | Projects v2 via GitHub CLI / GraphQL |
| Git hook installer | `scripts/setup_hooks.py` | **does not compile — see ANTI-PATTERNS** |
| Issue forms | `ISSUE_TEMPLATE/bug_report.yml`, `feature_request.yml` | + `issue_metrics.py` (needs PyGithub) |
| Labels | `labels.yml` | canonical label set |
| Wiki pages | `wiki/home.md`, `Getting-Started.md`, `Sidebar.md`, `table-of-contents.md` | published repo docs |

## CONVENTIONS
- **Package isolation is the design.** The repo root is not a package. Every
  check runs inside the owning package's own env with its own mypy/Ruff
  config. `PackageSpec` mirrors the `quality-gates` matrix exactly: ikigai,
  vibe-ops, interfaces-cli, src-contracts, src-mesh.
- **Ruff policy is pinned for the root bucket** —
  `CANONICAL_SELECT="E,F,W,I,N,UP,B,A,C4,PT,RUF"`, `IGNORE=E501`, line-length
  100, `py311` — because Ruff 0.16 changed its default rule set.
- **Diff attribution.** Only findings on lines the diff *added* fail; pre-existing debt is reported separately and never blocks the change.
- **Env hygiene.** `run()` strips `PYTHONPATH` / `PYTHONHOME` / `MYPYPATH` from
  the inherited environment before applying the package env, so a foreign
  `pydantic_core` cannot shadow the package's.
- **Windows tool resolution.** `tool()` prefers `~/.local/bin/<name>.exe` on
  `nt`; a missing manager is *reported*, never fatal. The root bucket uses
  `uv run --frozen` — a review must never rewrite a lock.

## ANTI-PATTERNS
- **Never invoke mypy with a path.** The package's canonical target is
  authoritative (`-p src.ikigai.src`); a path invocation gives Ikigai a second
  module identity and mypy aborts with "Source file found twice under
  different module names".
- **Never rewrite a lockfile** during a review → `uv run --frozen`. Never
  inherit the reviewer's own env (`PYTHONPATH`/`PYTHONHOME`/`MYPYPATH`).
- **Never treat unparsable output as a pass.** Unparsable mypy output = FAIL;
  pytest rc=5 ("no tests ran") = FAIL.
- The naming check inspects **function-local names only** (flagging module
  names produced 52 false positives), and the pytest parser reads only the
  tail — the summary comes last.
- **Three of the four modules `code_review.py` imports are untracked**:
  `code_review_checks.py`, `code_review_model.py` and `code_review_topology.py`
  are on disk but absent from `git ls-files`, while `code_review.py` is
  tracked. A fresh clone therefore fails the `code-review-checks` CI job with
  a `ModuleNotFoundError`. `git add -f` them before trusting CI.
- **Three of the ten `.github/scripts` modules do not compile** (verified with
  `py_compile`): `setup_hooks.py:81` defines `def install_post-commit_hook():`
  (hyphen in the function name) and `test_review.py:65,121` /
  `type_review.py:69` pass `text=True` twice. Do not wire them into a job
  until they are fixed.
- Docstrings advertise `python -m github.scripts.<mod>`, but no `github`
  package exists and `.github` is not importable — the working form is
  `python .github/scripts/<mod>.py`. Likewise `code_review.py`'s docstring
  advertises `--open` while argparse defines `--open-issues`.
- `project_board.assign_issue_to_column()` is a stub that prints a message
  (Projects v2 needs GraphQL). `setup_hooks.py`'s commit-msg hook only
  *warns* on a non-matching branch name.
- `.github/scripts/__pycache__/` holds 4 stale `.pyc` artifacts in-tree.

## COMMANDS
```bash
python .github/scripts/code_review.py --base main --review-format
python .github/scripts/code_review.py --base main --test-only --missing
python .github/scripts/code_review.py --base main --gate
python .github/scripts/git_worktree_manager.py --list
python .github/scripts/project_board.py --sync-labels
```
