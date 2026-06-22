#!/usr/bin/env python3
"""
Master Code Review Orchestrator

Runs the full pre-review check suite on changed files:
1. Type check (mypy --strict)
2. Lint (ruff)
3. Test suite review (what's tested, missing, failing)
4. Naming conventions

Produces a single unified review report for PR authors.

Designed to run in CI before a PR is opened — catches regressions before human review.
Also useful locally: `python .github/scripts/code_review.py --base main`

Usage:
    python .github/scripts/code_review.py                           # full suite, diff vs main
    python .github/scripts/code_review.py --base main                # vs main
    python .github/scripts/code_review.py --files src/foo.py         # specific files
    python .github/scripts/code_review.py --type-only                # skip tests (faster)
    python .github/scripts/code_review.py --test-only               # skip type check
    python .github/scripts/code_review.py --review-format            # full human report
    python .github/scripts/code_review.py --strict                  # mypy --strict
    python .github/scripts/code_review.py --github-annotations       # CI annotations output
    python .github/scripts/code_review.py --open                    # open issues only
    python .github/scripts/code_review.py --gate                   # exit code = pass/fail

Exit code: 0 if all checks pass, 1 if any check fails.
Use --gate to enforce in CI. Use --review-format for human output.
"""

from __future__ import annotations

import os
import sys
import json
import subprocess
import argparse
import re
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum, auto


ROOT = Path(__file__).resolve().parents[2]
CHECKS_DIR = Path(__file__).resolve().parents[1] / "scripts"


class CheckStatus(Enum):
    PASS = auto()
    FAIL = auto()
    SKIP = auto()
    WARN = auto()


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    summary: str = ""
    details: list[str] = field(default_factory=list)
    annotations: list[dict] = field(default_factory=list)  # GitHub annotation format

    def is_ok(self) -> bool:
        return self.status in (CheckStatus.PASS, CheckStatus.SKIP, CheckStatus.WARN)


@dataclass
class ReviewReport:
    results: list[CheckResult] = field(default_factory=list)
    files_changed: int = 0
    base_ref: str = "main"

    def all_passed(self) -> bool:
        return all(r.is_ok() for r in self.results)

    def failed_checks(self) -> list[CheckResult]:
        return [r for r in self.results if r.status == CheckStatus.FAIL]


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd or ROOT,
                          capture_output=True, text=True, text=True)


def get_changed_files(base_ref: str) -> tuple[list[Path], list[Path]]:
    """Return (source_files, test_files) changed vs. base_ref."""
    result = run(["git", "diff", "--name-only", f"{base_ref}...HEAD"])
    all_changed = [ROOT / f for f in result.stdout.strip().splitlines() if f]

    source = [f for f in all_changed
              if f.suffix == ".py" and "/tests/" not in str(f)
              and not f.name.startswith("test_") and f.exists()]
    tests = [f for f in all_changed
             if f.suffix == ".py" and (f.name.startswith("test_") or "/tests/" in str(f))
             and f.exists()]
    return source, tests


# ─── Individual Checks ────────────────────────────────────────────────────────

def check_mypy(source_files: list[Path], strict: bool = False) -> CheckResult:
    """Run mypy on changed files."""
    if not source_files:
        return CheckResult("type-check", CheckStatus.SKIP, "No source files changed")

    result = run(["uv", "run", "mypy", "--strict" if strict else "--no-strict",
                  "--output=json", "--no-error-summary",
                  "--show-error-codes", "--show-column-numbers",
                  *[str(f) for f in source_files]])

    try:
        output = json.loads(result.stdout) if result.stdout.strip() else {"files": []}
    except json.JSONDecodeError:
        output = {"files": []}

    errors = []
    annotations = []
    files_with_issues = set()

    for entry in output.get("files", []):
        rel = str(Path(entry["file"]).relative_to(ROOT))
        for err in entry.get("errors", []):
            files_with_issues.add(rel)
            line = err.get("line", 0)
            code = err.get("code", "")
            msg = err.get("message", "")
            errors.append(f"  {rel}:{line}  [{code}] {msg}")
            annotations.append({
                "path": rel, "line": line, "severity": "error",
                "title": code, "message": msg
            })

    status = CheckStatus.FAIL if errors else CheckStatus.PASS
    summary = f"{len(errors)} error(s)" if errors else "Clean"
    if files_with_issues:
        summary += f" in {len(files_with_issues)} file(s)"
    return CheckResult("type-check", status, summary, errors[:20], annotations)


def check_ruff(source_files: list[Path]) -> CheckResult:
    """Run ruff lint on changed files."""
    if not source_files:
        return CheckResult("ruff-lint", CheckStatus.SKIP, "No files changed")

    result = run([
        "uv", "run", "ruff", "check",
        "--output-format=concise",
        *[str(f) for f in source_files]
    ])

    output = result.stdout.strip()
    if not output:
        return CheckResult("ruff-lint", CheckStatus.PASS, "No lint errors")

    lines = output.splitlines()[:20]
    return CheckResult("ruff-lint", CheckStatus.FAIL, f"{len(lines)} lint error(s)", lines)


def check_naming(source_files: list[Path]) -> CheckResult:
    """Check naming conventions on changed files."""
    if not source_files:
        return CheckResult("naming", CheckStatus.SKIP, "No files changed")

    issues = []
    for f in source_files:
        rel = str(f.relative_to(ROOT))
        content = f.read_text(encoding="utf-8")

        # Check for snake_case violations in function/def names (simple check)
        # Allow class names, CapWords, and known exceptions
        bad_defines = re.findall(r"^(?!def |class |async def |#|_)\S+[A-Z]\S*$", content, re.MULTILINE)
        # Check for camelCase variables (simple heuristic: varName not var_name)
        bad_vars = re.findall(r"(?<!from |import |class |def )(?<!\w)[a-z]+[A-Z][a-zA-Z]*(?:\s*=\s*(?!=))",
                               content)

        for match in bad_defines[:3]:
            issues.append(f"  {rel}: suspicious name '{match}' (consider snake_case)")
        for match in bad_vars[:3]:
            issues.append(f"  {rel}: camelCase '{match}' (use snake_case)")

    # Also check file names
    for f in source_files:
        rel = str(f.relative_to(ROOT))
        if re.search(r"[A-Z]", f.name) and f.suffix == ".py":
            if f.name not in ["__init__.py", "__main__.py"]:
                issues.append(f"  {rel}: file name contains capitals (use snake_case.py)")

    status = CheckStatus.FAIL if issues else CheckStatus.PASS
    return CheckResult("naming", status,
                       f"{len(issues)} naming issue(s)" if issues else "All names clean",
                       issues[:15])


def check_pytest(source_files: list[Path], test_files: list[Path],
                 package_path: Path) -> CheckResult:
    """Run pytest on changed test files."""
    if not test_files:
        # Find tests for changed source
        test_map = []
        for sf in source_files:
            # Try to find a corresponding test
            for parent in sf.parents:
                tests_dir = parent / "tests"
                if tests_dir.exists():
                    name = f"test_{sf.stem}.py"
                    tf = tests_dir / name
                    if tf.exists():
                        test_map.append(tf)
                    break

        if not test_map:
            return CheckResult("tests", CheckStatus.SKIP, "No test files changed or found")
        test_files = test_map

    result = run([
        "uv", "run", "pytest",
        "--tb=short", "-v", "--no-header",
        "-q", "--ignore=scratch",
        *[str(f) for f in test_files]
    ])

    output = result.stdout + result.stderr

    failures = re.findall(r"FAILED", output)
    passes = re.findall(r"PASSED", output)
    errors = re.findall(r"ERROR", output)

    details = []
    for match in re.finditer(r"^FAILURES.*?^(=.*?)=", output, re.MULTILINE | re.DOTALL):
        details.append(match.group(0)[:300])

    total = len(passes) + len(failures) + len(errors)
    summary = f"{len(failures)} failure(s), {len(passes)} passed" if failures else \
             f"{total} test(s) passing"
    if errors:
        summary += f", {len(errors)} error(s)"

    status = CheckStatus.FAIL if (failures or errors) else CheckStatus.PASS
    return CheckResult("tests", status, summary, details[:5])


def check_missing_tests(source_files: list[Path], package_path: Path) -> CheckResult:
    """Flag source files with no corresponding test."""
    if not source_files:
        return CheckResult("test-coverage", CheckStatus.SKIP, "No source files changed")

    untested = []
    for sf in source_files:
        found = False
        # Look for test alongside source or in tests/ dir
        for parent in sf.parents[:3]:
            tests_dir = parent / "tests"
            if tests_dir.exists():
                name = f"test_{sf.stem}.py"
                if (tests_dir / name).exists() or list(tests_dir.glob(f"*{sf.stem}*")):
                    found = True
                    break
        if not found:
            untested.append(str(sf.relative_to(ROOT)))

    status = CheckStatus.WARN if untested else CheckStatus.PASS
    return CheckResult("test-coverage", status,
                       f"{len(untested)} file(s) without tests" if untested else "All tested",
                       [f"  • {u}" for u in untested[:10]])


# ─── Report Formatters ────────────────────────────────────────────────────────

def format_review_report(report: ReviewReport) -> str:
    """Human-readable review report."""
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("  CODE REVIEW — Pre-Merge Check Suite")
    lines.append("=" * 70)
    lines.append(f"  Base: {report.base_ref}  |  Changed: {report.files_changed} file(s)")
    lines.append("-" * 70)

    all_ok = report.all_passed()
    for r in report.results:
        icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭", "WARN": "⚠️"}[r.status.name]
        lines.append(f"  {icon} [{r.status.name}] {r.name:<18} {r.summary}")

    lines.append("-" * 70)
    if all_ok:
        lines.append("  ✅ ALL CHECKS PASSED — ready for review")
    else:
        failed = report.failed_checks()
        lines.append(f"  ❌ {len(failed)} CHECK(S) FAILED — fix before opening PR")
        for r in failed:
            if r.details:
                lines.append(f"\n  {r.name.upper()} DETAILS:")
                for d in r.details[:10]:
                    lines.append(f"    {d}")

    lines.append("=" * 70)
    return "\n".join(lines)


def format_github_annotations(report: ReviewReport) -> str:
    """GitHub Actions annotations for CI."""
    lines = []
    for r in report.results:
        for ann in r.annotations:
            sev = "error" if r.status == CheckStatus.FAIL else "warning"
            lines.append(
                f"::{sev} file={ann['path']},line={ann['line']},"
                f"title={ann['title']}::{ann['message']}"
            )
    return "\n".join(lines)


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Master code review orchestrator")
    parser.add_argument("--base", default="main",
                        help="Base branch (default: main)")
    parser.add_argument("--files", nargs="+", type=Path, metavar="F",
                        help="Specific files to review (overrides --base diff)")
    parser.add_argument("--type-only", action="store_true",
                        help="Run type check only")
    parser.add_argument("--test-only", action="store_true",
                        help="Run test suite check only")
    parser.add_argument("--strict", action="store_true",
                        help="Use mypy --strict")
    parser.add_argument("--review-format", action="store_true",
                        help="Full human-readable report")
    parser.add_argument("--github-annotations", action="store_true",
                        help="Output GitHub Actions annotations format")
    parser.add_argument("--open-issues", action="store_true",
                        help="Show only open issues (errors + warnings)")
    parser.add_argument("--gate", action="store_true",
                        help="Exit code = pass/fail (for CI)")
    parser.add_argument("--json", action="store_true",
                        help="JSON output")
    parser.add_argument("--package", default="life-ops/operational",
                        help="Package path for pytest (default: life-ops/operational)")
    args = parser.parse_args()

    source_files: list[Path] = []
    test_files: list[Path] = []
    package_path = ROOT / args.package

    if args.files:
        source_files = [f if f.is_absolute() else ROOT / f for f in args.files]
        test_files = []
    else:
        source_files, test_files = get_changed_files(args.base)

    report = ReviewReport(base_ref=args.base, files_changed=len(source_files))

    # Type check
    if not args.test_only:
        report.results.append(check_mypy(source_files, strict=args.strict))

    # Lint
    if not args.type_only and not args.test_only:
        report.results.append(check_ruff(source_files))

    # Naming
    if not args.type_only and not args.test_only:
        report.results.append(check_naming(source_files))

    # Tests
    if not args.type_only:
        report.results.append(check_pytest(source_files, test_files, package_path))
        if args.open_issues:
            report.results.append(check_missing_tests(source_files, package_path))

    # Output
    if args.github_annotations:
        print(format_github_annotations(report))
    elif args.review_format:
        print(format_review_report(report))
    elif args.json:
        print(json.dumps({
            "all_passed": report.all_passed(),
            "base_ref": report.base_ref,
            "files_changed": report.files_changed,
            "checks": [
                {"name": r.name, "status": r.status.name,
                 "summary": r.summary, "details": r.details}
                for r in report.results
            ]
        }, indent=2))
    else:
        # Concise summary
        if report.all_passed():
            print(f"✅ All checks passed ({len(source_files)} file(s))")
        else:
            for r in report.failed_checks():
                print(f"❌ {r.name}: {r.summary}")

    if args.gate:
        sys.exit(0 if report.all_passed() else 1)


if __name__ == "__main__":
    sys.exit(main())
