# .github

CI workflows, the PR-review orchestrator and the repository's GitHub metadata.
A distinct domain: automation, not product code.

## OVERVIEW
Two workflows and a Python review orchestrator — the only consumer of `.github/scripts/`.

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| CI pipeline | `workflows/ci.yml` | 2 jobs: `code-review-checks` (the review gate) and `quality-gates` (a 5-package matrix) |
| Review orchestrator CLI | `scripts/code_review.py` | `--base --files --type-only --test-only --missing --gate --json --package` |
| Shared process/env layer | `scripts/code_review_model.py` | `ROOT`, `CheckStatus`, `CheckResult`, `ReviewReport`, `PackageSpec`, `tool()`, `run()` |
| Package matrix | `scripts/code_review_topology.py` | `PACKAGES` (5), `Bucket`, `build_buckets()`, `diff_touched_lines()` |
| Individual checks | `scripts/code_review_checks.py` | mypy / ruff / ruff-format / naming / pytest / missing-tests |
| Worktree helper | `scripts/git_worktree_manager.py` | `--list --add --remove --prune` |
| Project board | `scripts/project_board.py`, `scripts/project_board_setup.py` | Projects v2 via GitHub CLI / GraphQL |
| Labels | `labels.yml` | canonical label set |
| PR template | `PULL_REQUEST_TEMPLATE.md` | what a pull request must say |

## CONVENTIONS
- **Package isolation is the design.** The repo root is not a package. Every
  check runs inside the owning package's own env with its own mypy/Ruff
  config. `PackageSpec` mirrors the `quality-gates` matrix exactly: **ikigai**,
  **src-contracts**, **src-data**, **src-services**, **src-transport**.
- **The root bucket has no package, so it runs in the published environment.**
  The one published environment is the `ikigai` Poetry project: the review
  resolves `poetry env info --executable` and calls the tool through that
  interpreter, with the working directory at the repository root (where the
  root `mypy.ini` is declared). Before the pivot the root bucket ran
  `uv run --frozen --extra dev` against a root project that existed on the
  owner's disk and in no clone — it failed with rc=2, and the gate reported
  nothing at all.
- **Ruff policy is pinned for the root bucket** —
  `CANONICAL_SELECT="E,F,W,I,N,UP,B,A,C4,PT,RUF"`, `IGNORE=E501`, line-length
  100, `py311` — because Ruff 0.16 changed its default rule set.
- **Diff attribution.** Only findings on lines the diff *added* fail; pre-existing debt is reported separately and never blocks the change.
- **Env hygiene.** `run()` strips `PYTHONPATH` / `PYTHONHOME` / `MYPYPATH` from
  the inherited environment before applying the package env, so a foreign
  `pydantic_core` cannot shadow the package's.
- **Windows tool resolution.** `tool()` prefers `~/.local/bin/<name>.exe` on
  `nt`; a missing manager is *reported*, never fatal.

## ANTI-PATTERNS
- **Never invoke mypy with a path.** The package's canonical target is
  authoritative (`-p src.ikigai.src`); a path invocation gives Ikigai a second
  module identity and mypy aborts with "Source file found twice under
  different module names".
- **Never rewrite a lockfile** during a review. Never inherit the reviewer's
  own env (`PYTHONPATH`/`PYTHONHOME`/`MYPYPATH`).
- **Never treat unparsable output as a pass.** Unparsable mypy output = FAIL;
  pytest rc=5 ("no tests ran") = FAIL.
- The naming check inspects **function-local names only** (flagging module
  names produced 52 false positives), and the pytest parser reads only the
  tail — the summary comes last.
- **All four modules `code_review.py` imports are tracked** (`code_review.py`,
  `code_review_checks.py`, `code_review_model.py`, `code_review_topology.py`),
  so a fresh clone runs the `code-review-checks` job. Keep new sibling modules
  tracked as well — an untracked helper breaks CI with a `ModuleNotFoundError`.
- Docstrings advertise `python -m github.scripts.<mod>`, but no `github`
  package exists and `.github` is not importable — the working form is
  `python .github/scripts/<mod>.py`. Likewise `code_review.py`'s docstring
  advertises `--open` while argparse defines `--open-issues`.
- `project_board.assign_issue_to_column()` is a stub that prints a message
  (Projects v2 needs GraphQL).

## COMMANDS
```bash
python .github/scripts/code_review.py --base main --review-format
python .github/scripts/code_review.py --base main --test-only --missing
python .github/scripts/code_review.py --base main --gate
python .github/scripts/git_worktree_manager.py --list
python .github/scripts/project_board.py --sync-labels
```
