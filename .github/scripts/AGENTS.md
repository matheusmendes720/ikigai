# .github/scripts

## OVERVIEW
PR review, project-board, worktree, and hook automation; score 9 because these helpers form a distinct operational boundary.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Run the combined PR review | `code_review.py` | Changed-file type, lint, naming, test, and missing-test checks |
| Run strict mypy review | `type_review.py` | Mypy-focused helper; currently blocked by a duplicate `text=True` keyword |
| Run test-gap review | `test_review.py` | Finds candidate tests and reports uncovered changed sources |
| Manage GitHub labels/board items | `project_board.py` | PyGithub label sync and Projects v2 assignment helper |
| Bootstrap a project board | `project_board_setup.py` | Creates columns, fields, starter issues, and wiki automation |
| Manage isolated worktrees | `git_worktree_manager.py` | Uses Git commands for list/add/remove/prune operations |
| Install repository hooks | `setup_hooks.py` | Writes commit hooks and delegates pre-commit installation |

## CONVENTIONS
- Resolve the repository as `Path(__file__).resolve().parents[2]`; helpers run from arbitrary working directories.
- Changed-file reviews use `git diff --name-only <base>...HEAD` and distinguish source files from test files.
- Review output has both concise human summaries and structured JSON/annotation modes where supported.
- The master orchestrator delegates type and test concerns to focused modules but currently retains its own changed-file discovery.
- Project scripts use PyGithub; board mutations use the GitHub CLI and authenticated Projects v2 operations.
- Worktree changes are Git subprocess operations; do not replace them with an in-memory Git model.

## ANTI-PATTERNS
- NEVER treat the `python -m github.scripts.*` examples in docstrings as the supported invocation; this directory is not an importable `github` package. Run the file path directly.
- DO NOT rely on `type_review.py` until its duplicate `text=True` keyword is removed; the file currently fails to parse.
- DO NOT run `setup_hooks.py` as-is expecting the canonical root setup: it still points pre-commit installation at the obsolete `life-ops/operational` path.
- DO NOT restore the archived `src/operational` default in `code_review.py`; pass the active package/path explicitly.
- DO NOT use `project_board.py` to move issues as a completed implementation; its current assignment path only prints the required Projects v2 operation.
- NEVER commit tokens or put them on command lines; use the documented environment variables.
- Review only changed files relative to the requested base; do not silently widen the diff to the whole repository.
