"""A gate that fails silently is a gate nobody can fix.

The `Code Review — Type & Test Checks` job stayed red for days with an EMPTY
log: exit code 1, no annotation, no message, nothing to read. The cause was
two defects that hide each other.

1. **The review asked for an environment the published tree does not have.**
   The root bucket ran `uv run --frozen --extra dev`, which is the pre-cut
   ROOT project — deleted with ADR-037. On the owner's disk a gitignored root
   `pyproject.toml` was still there, so uv resolved it; in a clone it is not,
   so uv answered "Failed to spawn: `mypy`" and the check reported "mypy
   produced no output (rc=2) — nothing was checked". The gate measured the
   owner's disk in one place and the clone in another, and the clone is where
   the gate runs.

2. **A failure with no file to point at produced no annotation.** The check
   HAD something to say — the tool could not run — but
   `--github-annotations` prints annotations, and a broken tool has no file to
   annotate. So the job exited 1 and printed nothing at all.

Either defect alone is survivable. Together they make a gate that reports
"failed" without saying what failed, which is indistinguishable from a gate
that is broken — and the broken one is the one nobody debugs.

So this file holds both invariants, and each of them is falsifiable by
construction: put a root `pyproject.toml` back, point the root bucket at
`uv` again, or drop the failure annotation, and the test that covers it
fails.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
IKIGAI_PKG = THIS_FILE.parent.parent
REPO_ROOT = IKIGAI_PKG.parent.parent
REVIEW_SCRIPTS = REPO_ROOT / ".github" / "scripts"

# The review is a script, not a package: `.github` is not an importable name.
# It puts its own directory on the path when it runs, and so does this.
if str(REVIEW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REVIEW_SCRIPTS))

import code_review  # noqa: E402
from code_review_checks import _manager_prefix  # noqa: E402
from code_review_model import CheckResult, CheckStatus  # noqa: E402
from code_review_model import run as code_review_run  # noqa: E402
from code_review_topology import PACKAGES, ROOT_ENV_PACKAGE  # noqa: E402


def _tracked(repo: Path) -> set[str]:
    """The tracked file set of the repository under test."""
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo,
        capture_output=True,
        encoding="utf-8",
        errors="surrogateescape",
        check=False,
    )
    if proc.returncode != 0:  # not a git checkout — nothing to assert
        return set()
    return {path for path in proc.stdout.split("\0") if path}


def test_the_published_tree_has_no_root_python_project() -> None:
    """The root is not a package: it has no manifest and no lock.

    The root `pyproject.toml` is gitignored — it belonged to the retired
    `life` meta-package — so it was in every working copy and in no clone.
    That is what made `uv run --frozen --extra dev` work on the owner's disk
    and fail in CI: the same gate, two different trees, two different
    verdicts.

    Publishing a root project is an architectural decision (it would give the
    root an identity of its own), so it cannot happen by accident — and if it
    does, this test says so instead of letting the divergence return.
    """
    tracked = _tracked(REPO_ROOT)
    if not tracked:
        return

    offenders = [name for name in ("pyproject.toml", "uv.lock") if name in tracked]

    assert not offenders, (
        "the published tree grew a root Python project ("
        + ", ".join(offenders)
        + "). The root is not a package: a root manifest would let a review "
        "resolve an environment that exists here and in no clone — the "
        "divergence that kept this job red with an empty log."
    )


def test_every_environment_the_review_names_is_published() -> None:
    """Every environment the review reaches for has to exist in the branch.

    The review runs the tools of a package inside that package's own
    environment, and the root bucket inside the ONE environment the tree
    publishes. If any of them is not published, the review measures nothing
    in a clone — and says so only in a way nobody reads.
    """
    tracked = _tracked(REPO_ROOT)
    if not tracked:
        return

    offenders: list[str] = []

    # The one published environment the root bucket runs in.
    env_files = {
        path for path in tracked if path.startswith(f"{ROOT_ENV_PACKAGE}/")
    }
    for required in (f"{ROOT_ENV_PACKAGE}/pyproject.toml", f"{ROOT_ENV_PACKAGE}/poetry.lock"):
        if required not in tracked:
            offenders.append(f"{required} (the environment the root bucket runs in)")

    # Every package the review knows how to check.
    for spec in PACKAGES:
        prefix = f"{spec.path}/"
        if not any(path.startswith(prefix) for path in tracked):
            offenders.append(f"{spec.path}/ (a package the review checks)")

    assert not offenders, (
        "the review names environments the branch does not publish: "
        + "; ".join(offenders)
        + ". A gate that runs where nothing is published measures nothing."
    )


def test_the_root_bucket_names_no_environment_the_tree_lacks() -> None:
    """The root bucket must not ask the reviewer's shell for a tool.

    `uv run --frozen --extra dev` was the pre-cut root environment: the root
    project, which the published tree does not have. The root bucket now runs
    in the one published environment, through its interpreter — so the tools
    it runs are the ones the lock pins, not whatever the shell happens to
    have.
    """
    prefix = _manager_prefix(None)

    assert prefix, "the root bucket has no environment at all — nothing would run"
    joined = " ".join(prefix)
    assert "uv" not in joined, (
        f"the root bucket still runs through `uv` ({joined}), which resolves "
        "the pre-cut root project: it works on a disk that still carries a "
        "root manifest and fails in every clone."
    )
    assert not joined.strip().endswith(("mypy", "ruff", "pytest")), (
        f"the root bucket runs a bare tool name ({joined}), so the tool comes "
        "from the reviewer's shell instead of from a published environment."
    )


def test_no_package_runs_a_bare_tool_name() -> None:
    """No package may reach for a tool the reviewer's shell happens to have.

    The `ruff-only` packages used to run a bare `ruff`. The review job
    installs no Ruff — only the quality-gates matrix does, in its own step —
    so the whole review died with `FileNotFoundError: 'ruff'` and the log
    showed a traceback where the report should have been.

    The rule is the same for every package: the tool comes from an
    environment the tree publishes, through that environment's interpreter.
    The Ruff the lock pins (`ruff==0.17.3`) is the very Ruff the matrix
    installs, so the review measures the version the gate measures.
    """
    offenders: list[str] = []

    for spec in PACKAGES:
        prefix = _manager_prefix(spec)
        joined = " ".join(prefix)

        if not prefix:
            offenders.append(f"{spec.name}: no environment at all")
            continue
        if joined.strip().endswith(("mypy", "ruff", "pytest")):
            offenders.append(f"{spec.name}: bare tool name ({joined})")
            continue
        if spec.manager == "ruff-only" and "-m" not in prefix:
            offenders.append(
                f"{spec.name}: runs through {joined} — the tool has to come "
                "from the published environment's interpreter"
            )

    assert not offenders, (
        "the review asks the reviewer's shell for a tool: "
        + "; ".join(offenders)
        + ". A gate that depends on the PATH of whoever runs it measures a "
        "different tree on every machine — and dies where the tool is absent."
    )


def test_a_missing_executable_is_a_reported_failure_not_a_crash() -> None:
    """A tool that is not there must be REPORTED, not raise.

    `subprocess.run` raises `FileNotFoundError` for an absent executable, and
    that exception escaped every check: one missing tool took the whole
    report down, so the checks that did run said nothing and the step ended
    on a traceback. The `|| true` in the workflow then hid it.

    A missing tool is a fact about the environment. The review reports it as
    a failed check with the reason attached.
    """
    result = code_review_run(["code_review-no-such-tool-exists"])

    assert result.returncode != 0, "an absent executable must not look like success"
    assert "not found" in (result.stderr or "").lower(), (
        "the failure does not say what was missing: " + repr(result.stderr)
    )


def test_a_failed_check_never_prints_nothing() -> None:
    """A FAIL with no file to point at still has to say what failed."""
    report = code_review.ReviewReport(base_ref="main", files_changed=1)
    report.results.append(
        CheckResult(
            "type-check/root",
            CheckStatus.FAIL,
            "mypy produced no output (rc=2) — nothing was checked",
            ["error: Failed to spawn: `mypy`"],
        )
    )

    annotations = code_review.format_github_annotations(report)

    assert annotations.strip(), (
        "a failed check produced no annotation — the gate exits 1 and the log "
        "shows nothing at all"
    )
    assert "type-check/root" in annotations, (
        "the annotation does not name the check that failed: " + annotations
    )


def test_the_gate_exits_non_zero_with_a_visible_reason(monkeypatch, capsys) -> None:
    """The whole path: a red gate says WHY it is red.

    This is the shape of the failure that kept the job red for days — exit
    code 1, empty log. The check that failed had a reason; the reason never
    reached the log.
    """

    def broken_check(bucket, strict=False):  # noqa: ARG001 — the shape is the point
        return CheckResult(
            "type-check/root",
            CheckStatus.FAIL,
            "mypy produced no output (rc=2) — nothing was checked",
            ["error: Failed to spawn: `mypy`"],
        )

    monkeypatch.setattr(code_review, "check_mypy", broken_check)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "code_review.py",
            "--files",
            "src/bot/main.py",
            "--type-only",
            "--github-annotations",
            "--gate",
        ],
    )

    code = code_review.main()
    printed = capsys.readouterr().out

    assert code == 1, "a failing check has to fail the gate"
    assert printed.strip(), (
        "the gate failed and printed nothing — a red gate nobody can fix"
    )
    assert "type-check/root" in printed, (
        "the gate failed without naming the check: " + printed
    )
