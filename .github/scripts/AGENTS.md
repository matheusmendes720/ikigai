# .github/scripts — the PR review orchestrator

Score 9 — distinct domain: the CI gate's own implementation. A sibling-module
graph, not a package: the scripts put their own directory on `sys.path`.

## OVERVIEW
The review gate: it runs each package's own mypy/ruff/pytest inside that
package's environment, and reports the findings the diff introduced.

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| CLI entry point | `code_review.py` | `main()`, `collect_changed_files()`, `build_report()`, `format_review_report()`, `format_github_annotations()` |
| Shared process/env layer | `code_review_model.py` | `ROOT`, `CheckStatus` (PASS/FAIL/SKIP/WARN), `CheckResult`, `ReviewReport`, `PackageSpec`, `tool()`, `run()` |
| Package matrix | `code_review_topology.py` | `PACKAGES` (5), `Bucket`, `build_buckets()`, `diff_touched_lines()`, `resolve_base_ref()` |
| The six checks | `code_review_checks.py` | mypy / ruff / ruff-format / naming / pytest / missing-tests |
| Deploy helpers | `deploy_extract_script.py`, `deploy_dry_run.py` | extract the remote heredoc from `deploy.yml`; substitute placeholders for a dry run |
| Worktrees | `git_worktree_manager.py` | `--list --add --remove --prune` |
| Board | `project_board.py`, `project_board_setup.py` | Projects v2 via GraphQL / `gh` |

## CONVENTIONS
- **Package isolation is the design.** The repo root is not a package. Every
  check runs inside the owning package's own env with its own mypy/Ruff
  config. `PackageSpec` mirrors the `quality-gates` matrix exactly:
  `ikigai`, `src-contracts`, `src-data`, `src-services`, `src-transport`.
- **The root bucket has no package, so it runs in the published environment**
  — the `ikigai` Poetry project: the review resolves
  `poetry env info --executable` and calls the tool through that interpreter,
  with the cwd at the repo root (where the root `mypy.ini` lives).
- **Ruff policy is pinned for the root bucket** —
  `CANONICAL_SELECT="E,F,W,I,N,UP,B,A,C4,PT,RUF"`, `CANONICAL_IGNORE="E501"`,
  line-length 100, `py311` — because Ruff 0.16 changed its default rule set.
- **Diff attribution.** Only findings on lines the diff ADDED fail;
  pre-existing debt is reported separately and never blocks the change.
- **Env hygiene.** `run()` strips `PYTHONPATH` / `PYTHONHOME` / `MYPYPATH`
  from the inherited environment before applying the package env, so a foreign
  `pydantic_core` cannot shadow the package's.
- **Windows tool resolution.** `tool()` prefers `~/.local/bin/<name>.exe` on
  `nt`; a missing manager is *reported* (rc 126/127), never fatal.
- Python 3.11, stdlib-only apart from `yaml` / `PyGithub`.

## ANTI-PATTERNS
- **Never invoke mypy with a path.** The package's canonical target is
  authoritative (`-p src.ikigai.src`); a path invocation gives Ikigai a second
  module identity and mypy aborts with "Source file found twice under
  different module names".
- **Never treat unparsable output as a pass.** Unparsable mypy output = FAIL;
  pytest rc=5 ("no tests ran") = FAIL; a missing executable = FAIL with the
  reason attached, not a traceback.
- **Never rewrite a lockfile during a review; never inherit the reviewer's env.**
- **Keep every sibling module tracked.** An untracked helper breaks a fresh
  clone's `code-review-checks` job with `ModuleNotFoundError`. The canonical
  suite imports these modules
  (`src/ikigai/tests/test_code_review_gate_integrity.py`).
- **The docstrings lie about the invocation.** `python -m github.scripts.<mod>`
  does not work (there is no `github` package and `.github` is not
  importable) — the working form is `python .github/scripts/<mod>.py`.
  `code_review.py`'s docstring advertises `--open` while argparse defines
  `--open-issues`.
- The naming check inspects **function-local names only** (module names gave 52
  false positives); the pytest parser reads only the tail, and takes the max.
- **A gate that cannot explain itself is a red gate that lies**: a FAILED
  check always produces an annotation — a failure with no file to point at is
  the one nobody can debug.
- **A missing base ref must fail loudly** — `resolve_base_ref` returns `None`
  and the caller raises, instead of reporting "ALL CHECKS PASSED" for an empty
  diff.
- `project_board.assign_issue_to_column()` is a stub that only prints
  (Projects v2 needs GraphQL).

## COMMANDS
```bash
python .github/scripts/code_review.py --base main --review-format
python .github/scripts/code_review.py --base main --type-only --github-annotations --gate
python .github/scripts/code_review.py --base main --test-only --missing --review-format --gate
python .github/scripts/code_review.py --package src/services --gate
python .github/scripts/deploy_extract_script.py /tmp/deploy.sh
python .github/scripts/project_board.py --sync-labels
```
