"""The individual checks: mypy, Ruff, naming conventions and pytest.

Every check runs inside the environment of the package that owns the files,
with that package's own configuration. Nothing is aggregated across packages:
the packages have different module identities and different tool versions, so
a combined run is not a valid measurement.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from code_review_model import (
    ROOT,
    CheckResult,
    CheckStatus,
    PackageSpec,
    run,
    tool,
)
from code_review_topology import (
    ROOT_TEST_CWD,
    ROOT_TEST_ENV,
    ROOT_TEST_PREFIX,
    Bucket,
    ReviewEnvironmentError,
    check_cwd,
    package_cwd,
    root_env_python,
)

# The rule set every package in the matrix uses. The repository root has no
# Ruff configuration of its own, and Ruff 0.16 changed its DEFAULT rule set
# (414 rules), which would make a root lint neither reproducible across
# versions nor comparable with the packages. Pinning the packages' rule set
# for the root bucket keeps the whole monorepo on one policy.
CANONICAL_SELECT = "E,F,W,I,N,UP,B,A,C4,PT,RUF"
CANONICAL_IGNORE = "E501"
CANONICAL_LINE_LENGTH = "100"
CANONICAL_TARGET_VERSION = "py311"

_MYPY_LINE = re.compile(r"^(?P<path>[^:]+):(?P<line>\d+):(?P<col>\d+):\s+(?P<rest>.*)$")


def _rel_to_repo(path: str, cwd: Path) -> str:
    p = Path(path)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(ROOT.resolve()).as_posix()
        except ValueError:
            return p.as_posix()
    return (cwd / p).resolve().relative_to(ROOT.resolve()).as_posix()


def _manager_prefix(spec: PackageSpec | None) -> list[str]:
    """The command prefix that runs a tool inside the package's environment."""
    if spec is None:
        # The root has no environment of its own — the published tree has no
        # root `pyproject.toml` and no root `uv.lock` (ADR-037 cut), so the
        # pre-cut `uv run --frozen --extra dev` cannot resolve in a clone.
        # The ONE published environment is the Ikigai package; the review
        # runs its tools through its interpreter (`python -m <tool>`), so the
        # pinned versions are the ones the lock declares.
        return [root_env_python(), "-m"]
    if spec.manager == "poetry":
        return [tool("poetry"), "run"]
    if spec.manager == "uv":
        return [tool("uv"), "run"]
    if spec.manager == "ruff-only":
        # A `ruff-only` package has NO environment of its own: the CI matrix
        # lints it with a pip-installed Ruff, and the published tree ships no
        # manifest and no lock for it. Asking the reviewer's shell for a bare
        # `ruff` therefore made the review depend on the reviewer's PATH —
        # and the review job installs no Ruff at all, so the whole report
        # died with `FileNotFoundError: 'ruff'`.
        #
        # The ONE published environment pins the very same Ruff the matrix
        # installs (`ruff==0.17.3`, see src/ikigai/poetry.lock), so the tool
        # runs through that interpreter — `python -m ruff` — and the review
        # measures the version the gate measures, on every host, in every
        # clone.
        return [root_env_python(), "-m"]
    return []


def _package_env(spec: PackageSpec | None) -> dict[str, str]:
    return dict(spec.env) if spec else {}


def _lint_scope(bucket: Bucket) -> list[str]:
    """The files a bucket's lint/format check must cover.

    Both the changed sources AND the changed tests of the bucket. Test files
    are part of the change: a lint or formatting debt on a line the change
    added is the change's debt, and excluding tests would let it escape the
    gate entirely. The order is stable (sources first, then tests) so the
    command line is reproducible.
    """
    return [*bucket.files, *bucket.tests]


def _relative_files(bucket: Bucket, files: list[str]) -> list[str]:
    """Paths relative to the package directory (mypy/pytest resolve them there)."""
    prefix = (bucket.spec.path + "/") if bucket.spec else ""
    out = []
    for f in files:
        out.append(f[len(prefix) :] if prefix and f.startswith(prefix) else f)
    return out


def _absolute_files(bucket: Bucket, files: list[str]) -> list[str]:
    """Absolute paths — for a bucket that runs outside the repository root.

    The root bucket runs in the published environment, whose working
    directory is the package directory. A relative path would be resolved
    against the wrong root, and the check would measure a file that does not
    exist instead of the one the change touched.
    """
    return [str((ROOT / f).resolve()) for f in files]


def _bucket_files(bucket: Bucket, files: list[str]) -> list[str]:
    """The paths a bucket's tools receive, in the form their cwd needs."""
    if bucket.spec is None:
        return _absolute_files(bucket, files)
    return _relative_files(bucket, files)


# ─── mypy ─────────────────────────────────────────────────────────────────────


def parse_mypy_output(stdout: str) -> tuple[list[dict], list[str]]:
    """Parse mypy output into (records, fatal_problems).

    mypy 1.11+ writes JSON Lines: one JSON object per line. Older versions
    wrote a single JSON document with a "files" array. Both are accepted;
    anything else is a fatal problem, because a run that could not be parsed
    did not measure anything.
    """
    problems: list[str] = []
    text = stdout.strip()
    if not text:
        return [], problems

    try:
        doc = json.loads(text)
    except json.JSONDecodeError:
        doc = None

    if isinstance(doc, dict) and "files" in doc:
        records: list[dict] = []
        for entry in doc["files"]:
            for err in entry.get("errors", []):
                records.append(
                    {
                        "file": entry.get("file", ""),
                        "line": err.get("line", 0),
                        "column": err.get("column", 0),
                        "message": err.get("message", ""),
                        "code": err.get("code", ""),
                        "severity": err.get("severity", "error"),
                    }
                )
        return records, problems

    records = []
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            problems.append(f"mypy emitted non-JSON output: {raw[:300]}")
            continue
        if not isinstance(rec, dict) or "severity" not in rec:
            problems.append(f"mypy emitted an unexpected record: {raw[:300]}")
            continue
        records.append(rec)
    return records, problems


def check_mypy(bucket: Bucket, strict: bool = False) -> CheckResult:
    """Type check the changed sources of one bucket, inside its own env."""
    name = f"type-check/{bucket.name}"
    if not bucket.files:
        return CheckResult(name, CheckStatus.SKIP, "No source files changed")
    if bucket.spec and bucket.spec.manager == "ruff-only":
        return CheckResult(
            name,
            CheckStatus.SKIP,
            f"{bucket.name} is ruff-only in the CI matrix — not type checked",
        )

    cwd = Path(check_cwd(bucket.spec))
    try:
        prefix = _manager_prefix(bucket.spec)
    except ReviewEnvironmentError as exc:
        return CheckResult(name, CheckStatus.FAIL, str(exc), [str(exc)])

    cmd = [
        *prefix,
        "mypy",
        "--output=json",
        "--no-error-summary",
        "--show-error-codes",
        "--show-column-numbers",
    ]
    if bucket.spec is None:
        # The root bucket has no package identity of its own. Following imports
        # would pull in files from the other buckets and contaminate the
        # attribution of the findings; ignoring missing imports keeps the
        # analysis on the files that were actually changed.
        cmd += ["--ignore-missing-imports", "--follow-imports=silent"]
        cmd += _absolute_files(bucket, bucket.files)
    else:
        # The package's canonical target is authoritative. A path-based
        # invocation gives the Ikigai package a SECOND module identity and
        # mypy then aborts with "Source file found twice under different
        # module names" — a false failure that measures nothing.
        cmd += list(bucket.spec.mypy_target) or _relative_files(bucket, bucket.files)

    result = run(cmd, cwd=cwd, env=_package_env(bucket.spec))
    stdout = result.stdout or ""

    if not stdout.strip():
        if result.returncode == 0:
            return CheckResult(name, CheckStatus.PASS, "Clean")
        detail = (result.stderr or "").strip()[:2000]
        return CheckResult(
            name,
            CheckStatus.FAIL,
            f"mypy produced no output (rc={result.returncode}) — nothing was checked",
            [detail] if detail else [],
        )

    records, problems = parse_mypy_output(stdout)
    if problems:
        return CheckResult(
            name,
            CheckStatus.FAIL,
            "mypy output could not be parsed — nothing was checked",
            problems[:10],
        )

    errors = []
    annotations = []
    preexisting = []
    for rec in records:
        if rec.get("severity") != "error":
            continue
        rel = _rel_to_repo(str(rec.get("file", "")), cwd)
        line = int(rec.get("line") or 0)
        code = str(rec.get("code") or "")
        msg = str(rec.get("message") or "")
        entry = f"  {rel}:{line}  [{code}] {msg}"
        if line and line in bucket.touched.get(rel, set()):
            errors.append(entry)
            annotations.append(
                {"path": rel, "line": line, "severity": "error", "title": code, "message": msg}
            )
        else:
            preexisting.append(entry)

    if errors:
        summary = f"{len(errors)} error(s) introduced by this change"
        return CheckResult(
            name, CheckStatus.FAIL, summary, errors[:20], annotations, preexisting[:10]
        )
    summary = "Clean" if not preexisting else "Clean (no new errors)"
    return CheckResult(name, CheckStatus.PASS, summary, [], [], preexisting[:10])


# ─── Ruff ─────────────────────────────────────────────────────────────────────


def check_ruff(bucket: Bucket) -> CheckResult:
    """Lint the changed sources of one bucket with that bucket's Ruff config."""
    name = f"ruff-lint/{bucket.name}"
    scope = _lint_scope(bucket)
    if not scope:
        return CheckResult(name, CheckStatus.SKIP, "No source files changed")

    cwd = Path(check_cwd(bucket.spec))
    files = _bucket_files(bucket, scope)
    try:
        prefix = _manager_prefix(bucket.spec)
    except ReviewEnvironmentError as exc:
        return CheckResult(name, CheckStatus.FAIL, str(exc), [str(exc)])

    cmd = [*prefix, "ruff", "check", "--output-format=concise"]
    if bucket.spec is None:
        cmd += [
            "--select",
            CANONICAL_SELECT,
            "--ignore",
            CANONICAL_IGNORE,
            "--line-length",
            CANONICAL_LINE_LENGTH,
            "--target-version",
            CANONICAL_TARGET_VERSION,
        ]
    cmd += files

    result = run(cmd, cwd=cwd, env=_package_env(bucket.spec))
    if result.returncode not in (0, 1):
        return CheckResult(
            name,
            CheckStatus.FAIL,
            f"ruff could not run (rc={result.returncode})",
            [(result.stderr or result.stdout or "").strip()[:2000]],
        )

    new_findings = []
    preexisting = []
    for raw in result.stdout.splitlines():
        m = _MYPY_LINE.match(raw.strip())
        if not m:
            continue
        rel = _rel_to_repo(m.group("path"), cwd)
        line = int(m.group("line"))
        rest = m.group("rest")
        code = rest.split(" ", 1)[0] if rest else ""
        msg = rest[len(code) :].strip() if rest else ""
        entry = f"  {rel}:{line}  [{code}] {msg}"
        if line in bucket.touched.get(rel, set()):
            new_findings.append(entry)
        else:
            preexisting.append(entry)

    if new_findings:
        return CheckResult(
            name,
            CheckStatus.FAIL,
            f"{len(new_findings)} lint error(s) introduced by this change",
            new_findings[:20],
            [],
            preexisting[:10],
        )
    return CheckResult(
        name,
        CheckStatus.PASS,
        "No lint errors" if not preexisting else "No new lint errors",
        [],
        [],
        preexisting[:10],
    )


def check_ruff_format(bucket: Bucket) -> CheckResult:
    """Check formatting of the changed sources of one bucket."""
    name = f"ruff-format/{bucket.name}"
    scope = _lint_scope(bucket)
    if not scope:
        return CheckResult(name, CheckStatus.SKIP, "No source files changed")

    cwd = Path(check_cwd(bucket.spec))
    files = _bucket_files(bucket, scope)
    try:
        prefix = _manager_prefix(bucket.spec)
    except ReviewEnvironmentError as exc:
        return CheckResult(name, CheckStatus.FAIL, str(exc), [str(exc)])

    cmd = [*prefix, "ruff", "format", "--check", "--diff"]
    if bucket.spec is None:
        cmd += [
            "--line-length",
            CANONICAL_LINE_LENGTH,
            "--target-version",
            CANONICAL_TARGET_VERSION,
        ]
    cmd += files

    result = run(cmd, cwd=cwd, env=_package_env(bucket.spec))
    if result.returncode == 0:
        return CheckResult(name, CheckStatus.PASS, "Already formatted")
    if result.returncode not in (1,):
        return CheckResult(
            name,
            CheckStatus.FAIL,
            f"ruff format could not run (rc={result.returncode})",
            [(result.stderr or "").strip()[:2000]],
        )

    # `ruff format --check --diff` prints a diff. A file fails when one of its
    # hunks touches a line this change added; formatting debt that predates the
    # change is reported but does not block it.
    offending: list[str] = []
    current: str | None = None
    hunk = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
    for raw in result.stdout.splitlines():
        if raw.startswith("--- "):
            current = _rel_to_repo(raw[4:].strip().split("\t")[0], cwd)
            continue
        m = hunk.match(raw)
        if not m or not current:
            continue
        start = int(m.group(1))
        count = int(m.group(2) or 1)
        touched = bucket.touched.get(current, set())
        if any(i in touched for i in range(start, start + count)):
            if current not in offending:
                offending.append(current)

    if offending:
        return CheckResult(
            name,
            CheckStatus.FAIL,
            f"{len(offending)} file(s) need formatting on changed lines",
            [f"  {r}" for r in offending[:20]],
        )
    return CheckResult(
        name,
        CheckStatus.PASS,
        "Formatting unchanged on changed lines",
        [],
    )


# ─── Naming conventions ───────────────────────────────────────────────────────


def _is_camel(name: str) -> bool:
    """True for mixedCase names (PEP 8 wants snake_case for locals)."""
    stripped = name.lstrip("_")
    if not stripped:
        return False
    if stripped.isupper():
        return False
    return any(c.isupper() for c in stripped) and any(c.islower() for c in stripped)


def _check_names_in_tree(tree: ast.AST) -> list[tuple[int, str]]:
    """Collect camelCase local names and parameters, with their line numbers.

    Only function-local names are inspected. Class names, module-level
    constants and type aliases follow different conventions (and are already
    covered by Ruff's pep8-naming rules), so flagging them here produced 52
    false positives on this repository. The line number lets the caller
    attribute the finding to the diff.
    """
    issues: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        args = node.args
        params = [*args.posonlyargs, *args.args, *args.kwonlyargs]
        for a in params:
            if a.arg in ("self", "cls"):
                continue
            if _is_camel(a.arg):
                issues.append((a.lineno, f"parameter '{a.arg}' should be snake_case"))
        vararg = args.vararg
        if vararg and _is_camel(vararg.arg):
            issues.append((vararg.lineno, f"parameter '*{vararg.arg}' should be snake_case"))
        kwarg = args.kwarg
        if kwarg and _is_camel(kwarg.arg):
            issues.append((kwarg.lineno, f"parameter '**{kwarg.arg}' should be snake_case"))
        for inner in ast.walk(node):
            if isinstance(inner, ast.Assign):
                for t in inner.targets:
                    if isinstance(t, ast.Name) and _is_camel(t.id):
                        issues.append(
                            (inner.lineno, f"local variable '{t.id}' should be snake_case")
                        )
            elif isinstance(inner, ast.AnnAssign):
                if isinstance(inner.target, ast.Name) and _is_camel(inner.target.id):
                    issues.append(
                        (inner.lineno, f"local variable '{inner.target.id}' should be snake_case")
                    )
    return issues


def check_naming(bucket: Bucket) -> CheckResult:
    """Check naming conventions with the AST instead of a regex."""
    name = f"naming/{bucket.name}"
    if not bucket.files:
        return CheckResult(name, CheckStatus.SKIP, "No source files changed")

    scope = _lint_scope(bucket)
    if not scope:
        return CheckResult(name, CheckStatus.SKIP, "No source files changed")

    issues: list[str] = []
    preexisting: list[str] = []
    for rel in scope:
        path = ROOT / rel
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError) as exc:
            issues.append(f"  {rel}: could not be parsed ({exc})")
            continue
        touched = bucket.touched.get(rel, set())
        for line, issue in _check_names_in_tree(tree):
            entry = f"  {rel}:{line}  {issue}"
            # Same attribution rule as the other checks: only a name on a line
            # the change added belongs to this change.
            if line in touched:
                issues.append(entry)
            else:
                preexisting.append(entry)

    if issues:
        return CheckResult(
            name,
            CheckStatus.FAIL,
            f"{len(issues)} naming issue(s) introduced by this change",
            issues[:20],
            [],
            preexisting[:10],
        )
    return CheckResult(
        name,
        CheckStatus.PASS,
        "All names clean" if not preexisting else "All names clean (no new issues)",
        [],
        [],
        preexisting[:10],
    )


# ─── pytest ───────────────────────────────────────────────────────────────────


def _pytest_count(output: str, pattern: str) -> int:
    """How many tests the pytest summary reports.

    `re.findall` returns one match per OCCURRENCE of the pattern, so counting
    the matches reported the number of summary lines ("1 passed" for a run of
    three). Only the tail is inspected: the pytest summary comes last.
    """
    found = [int(m) for m in re.findall(pattern, output[-2000:])]
    return max(found) if found else 0


def check_pytest(bucket: Bucket) -> CheckResult:
    """Run the changed tests of one bucket inside that bucket's environment."""
    name = f"tests/{bucket.name}"
    if not bucket.tests:
        return CheckResult(name, CheckStatus.SKIP, "No test files changed")
    if bucket.spec and not bucket.spec.pytest:
        return CheckResult(
            name,
            CheckStatus.SKIP,
            f"{bucket.name} has no test entry in the CI matrix",
        )

    if bucket.spec is None:
        # The repository root has no environment of its own: its pytest
        # environment cannot even collect the tests (langgraph is missing).
        # The Ikigai Poetry environment is the one that can, with the
        # repository root exposed on PYTHONPATH.
        cmd = [tool(p) if p in ("uv", "poetry") else p for p in ROOT_TEST_PREFIX]
        cwd = Path(ROOT_TEST_CWD)
        env = dict(ROOT_TEST_ENV)
        files = [str((ROOT / f).resolve()) for f in bucket.tests]
    else:
        cmd = [*_manager_prefix(bucket.spec), "pytest"]
        cwd = Path(package_cwd(bucket.spec))
        env = _package_env(bucket.spec)
        files = _relative_files(bucket, bucket.tests)

    cmd += ["-q", "--no-header", "-m", "not e2e", *files]
    result = run(cmd, cwd=cwd, env=env)
    output = (result.stdout or "") + (result.stderr or "")

    if result.returncode == 5 or "no tests ran" in output.lower():
        return CheckResult(
            name,
            CheckStatus.FAIL,
            "pytest collected no tests — nothing was verified",
            [output.strip()[:2000]],
        )

    passed = _pytest_count(output, r"\b(\d+) passed\b")
    failed = _pytest_count(output, r"\b(\d+) failed\b")
    errored = _pytest_count(output, r"\b(\d+) error\b")
    summary = f"{passed} passed"
    if failed:
        summary += f", {failed} failed"
    if errored:
        summary += f", {errored} errored"

    if result.returncode != 0:
        details = []
        for m in re.finditer(r"^(FAILED|ERROR) .*$", output, re.MULTILINE):
            details.append("  " + m.group(0)[:200])
        return CheckResult(
            name,
            CheckStatus.FAIL,
            f"{summary} (rc={result.returncode})",
            details[:20] or [output.strip()[-2000:]],
        )
    return CheckResult(name, CheckStatus.PASS, summary)


def check_missing_tests(bucket: Bucket) -> CheckResult:
    """Flag changed sources without a matching test file in the same package."""
    name = f"test-coverage/{bucket.name}"
    if not bucket.files:
        return CheckResult(name, CheckStatus.SKIP, "No source files changed")

    untested = []
    for rel in bucket.files:
        stem = Path(rel).stem
        found = False
        for t in bucket.tests:
            if stem in Path(t).stem:
                found = True
                break
        if not found:
            untested.append(rel)

    if untested:
        return CheckResult(
            name,
            CheckStatus.WARN,
            f"{len(untested)} file(s) without a matching test",
            [f"  • {u}" for u in untested[:10]],
        )
    return CheckResult(name, CheckStatus.PASS, "All changed sources have tests")
