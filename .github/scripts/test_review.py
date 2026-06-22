#!/usr/bin/env python3
"""
Test Suite Reviewer

Analyzes the test suite for changed files: shows what's being tested,
what's missing, what's failing, and produces a review-friendly delta report.

Designed to run in CI before a PR is opened — catches test gaps before review.

Usage:
    python -m github.scripts.test_review                          # diff vs main
    python -m github.scripts.test_review --base main             # diff vs main
    python -m github.scripts.test_review --files src/foo.py      # specific files
    python -m github.scripts.test_review --coverage              # include coverage delta
    python -m github.scripts.test_review --missing                # flag untested files
    python -m github.scripts.test_review --review-format          # human review output

Requires: pytest, coverage (if --coverage)
    uv run pytest --help  # already available in project
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


ROOT = Path(__file__).resolve().parents[2]


@dataclass
class TestFile:
    path: Path
    test_count: int = 0
    test_names: list[str] = field(default_factory=list)
    has_failures: bool = False
    failure_count: int = 0
    failure_lines: list[tuple[int, str]] = field(default_factory=list)
    coverage_pct: float | None = None


@dataclass
class TestReviewResult:
    test_files: list[TestFile] = field(default_factory=list)
    total_tests: int = 0
    total_failures: int = 0
    total_errors: int = 0
    clean_files: list[str] = field(default_factory=list)
    untested_source_files: list[str] = field(default_factory=list)
    diff_source_files: list[str] = field(default_factory=list)


def get_changed_files(base_ref: str = "main") -> tuple[list[Path], list[Path]]:
    """Return (source_files, test_files) changed vs. base_ref."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
            cwd=ROOT, capture_output=True, text=True, text=True
        )
        all_changed = [ROOT / f for f in result.stdout.strip().splitlines() if f]

        source_files = [
            f for f in all_changed
            if f.suffix == ".py"
            and not f.name.startswith("test_")
            and "/tests/" not in str(f)
            and f.exists()
        ]
        test_files = [
            f for f in all_changed
            if f.suffix == ".py"
            and (f.name.startswith("test_") or "/tests/" in str(f))
            and f.exists()
        ]
        return source_files, test_files
    except Exception as e:
        sys.stderr.write(f"[WARN] Could not get changed files: {e}\n")
        return [], []


def find_test_for_source(source_file: Path) -> Path | None:
    """Locate the test file that covers a source file."""
    # Strategy 1: tests/ alongside source
    candidate = source_file.parent / "tests" / f"test_{source_file.name}"
    if candidate.exists():
        return candidate

    # Strategy 2: tests/ one level up
    if source_file.parent.name != "src":
        candidate2 = source_file.parents[1] / "tests" / f"test_{source_file.name}"
        if candidate2.exists():
            return candidate2

    # Strategy 3: tests/ in test_results dir or sibling
    test_dirs = ["tests", "test_results"]
    for parent in source_file.parents[:4]:
        for td in test_dirs:
            tdir = parent / td
            if tdir.exists():
                for pattern in [f"test_{source_file.stem}.py", f"{source_file.stem}_test.py"]:
                    for tfile in tdir.rglob(pattern):
                        return tfile
    return None


def run_pytest_for_file(test_file: Path, package_path: Path) -> TestFile:
    """Run pytest on a single test file and parse results."""
    tf = TestFile(path=test_file)

    result = subprocess.run(
        ["uv", "run", "pytest", str(test_file),
         "--tb=short", "-v", "--no-header",
         "-q", "--ignore=scratch"],
        cwd=package_path, capture_output=True, text=True, text=True
    )

    output = result.stdout + result.stderr

    # Count test results
    passed = re.findall(r"PASSED", output)
    failed = re.findall(r"FAILED", output)
    tf.test_count = len(passed) + len(failed)
    tf.has_failures = len(failed) > 0
    tf.failure_count = len(failed)

    # Extract failure details
    for match in re.finditer(r"FAILED (.+?) - (.*)$", output, re.MULTILINE):
        test_name = match.group(1)
        error_msg = match.group(2).strip().split("\n")[0]
        line_match = re.search(r"(\d+):", error_msg)
        line = int(line_match.group(1)) if line_match else 0
        tf.failure_lines.append((line, f"{test_name}: {error_msg[:120]}"))

    tf.test_names = re.findall(r"PASSED::(.+)", output)

    return tf


def find_source_files_for_package(package_path: Path) -> list[Path]:
    """Find all source Python files in a package (excluding tests/)."""
    src_root = package_path / "src"
    if not src_root.exists():
        src_root = package_path
    files = []
    for f in src_root.rglob("*.py"):
        if "/tests/" not in str(f) and not f.name.startswith("test_"):
            files.append(f)
    return files


def run_missing_check(source_files: list[Path],
                     package_path: Path) -> list[str]:
    """Find source files with no corresponding test."""
    untested = []
    all_sources = find_source_files_for_package(package_path)

    # Get all test files
    test_files = set()
    for f in all_sources:
        t = find_test_for_source(f)
        if t:
            test_files.add(t)

    # Check which source files have tests
    for sf in source_files:
        t = find_test_for_source(sf)
        if t is None or not t.exists():
            untested.append(str(sf.relative_to(ROOT)))

    return untested


def main():
    parser = argparse.ArgumentParser(description="Test suite review on changed files")
    parser.add_argument("--base", default="main",
                        help="Base branch to diff against (default: main)")
    parser.add_argument("--files", nargs="+", type=Path, metavar="F",
                        help="Specific source files to check (checks their tests)")
    parser.add_argument("--review-format", action="store_true",
                        help="Human review-friendly output")
    parser.add_argument("--missing", action="store_true",
                        help="Also flag source files with no test")
    parser.add_argument("--coverage", action="store_true",
                        help="Include coverage report (requires coverage installed)")
    parser.add_argument("--json-output", action="store_true",
                        help="Machine-readable JSON output")
    parser.add_argument("--package", default="life-ops/operational",
                        help="Package path for pytest (default: life-ops/operational)")
    args = parser.parse_args()

    package_path = ROOT / args.package
    source_files: list[Path] = []
    test_files: list[Path] = []

    if args.files:
        source_files = [f if f.is_absolute() else ROOT / f for f in args.files]
        test_files = [find_test_for_source(f) for f in source_files]
        test_files = [t for t in test_files if t and t.exists()]
    else:
        source_files, test_files = get_changed_files(args.base)

    result = TestReviewResult()
    result.diff_source_files = [str(f.relative_to(ROOT)) for f in source_files]

    # Run pytest on changed test files
    for tf_path in test_files:
        tf = run_pytest_for_file(tf_path, package_path)
        result.test_files.append(tf)
        result.total_tests += tf.test_count
        result.total_failures += tf.failure_count

    # Find untested source files
    if args.missing:
        result.untested_source_files = run_missing_check(source_files, package_path)

    if args.review_format:
        lines = []
        lines.append("=" * 60)
        lines.append("TEST SUITE REVIEW REPORT")
        lines.append("=" * 60)

        changed_src = result.diff_source_files
        lines.append(f"\nChanged source files: {len(changed_src)}")
        for f in changed_src:
            lines.append(f"  • {f}")

        if result.test_files:
            lines.append(f"\nTest files run: {len(result.test_files)}")
            for tf in result.test_files:
                rel = str(tf.path.relative_to(ROOT))
                if tf.has_failures:
                    lines.append(f"  ❌ {rel}: {tf.failure_count} failure(s), {tf.test_count - tf.failure_count} passed")
                else:
                    lines.append(f"  ✅ {rel}: {tf.test_count} test(s) passing")
        else:
            lines.append("\nNo test files changed.")

        if result.untested_source_files:
            lines.append(f"\n⚠️  UNTESTED SOURCE FILES ({len(result.untested_source_files)})")
            for f in result.untested_source_files:
                lines.append(f"  • {f} — no test found")

        lines.append(f"\nSummary: {result.total_tests} test(s), "
                    f"{result.total_failures} failure(s)")
        print("\n".join(lines))

    elif args.json_output:
        print(json.dumps({
            "total_tests": result.total_tests,
            "total_failures": result.total_failures,
            "changed_source_files": result.diff_source_files,
            "untested_source_files": result.untested_source_files,
            "test_files": [
                {
                    "path": str(tf.path.relative_to(ROOT)),
                    "test_count": tf.test_count,
                    "has_failures": tf.has_failures,
                    "failure_count": tf.failure_count,
                    "failure_lines": tf.failure_lines
                }
                for tf in result.test_files
            ]
        }, indent=2))
    else:
        # Concise summary
        if result.total_failures > 0:
            print(f"❌ {result.total_failures} failure(s) in {len(result.test_files)} test file(s)")
        elif result.total_tests > 0:
            print(f"✅ {result.total_tests} test(s) passing in {len(result.test_files)} file(s)")
        else:
            print("⚠️  No test files changed or found for the diff")

        if args.missing and result.untested_source_files:
            print(f"⚠️  {len(result.untested_source_files)} source file(s) without tests")

    return 0 if result.total_failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
