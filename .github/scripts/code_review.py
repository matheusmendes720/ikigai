#!/usr/bin/env python3
"""Master Code Review Orchestrator.

Runs the pre-review check suite on the files a change touched:

1. Type check (mypy, per package, in that package's own environment)
2. Lint + formatting (Ruff, per package, with that package's own config)
3. Test suite review (what is tested, what is missing, what fails)
4. Naming conventions (AST based, not a regex)

The repository is a monorepo of independent packages, and this orchestrator
respects that boundary. Each package has its own environment, its own module
identity and its own tool configuration, so every check runs inside the
package that owns the files:

  * mypy runs per file, in the package directory, with the package's own
    configuration. A combined invocation across packages is not possible
    (`vibe-ops` is not a valid Python package name, and the Ikigai package
    would be analysed under a second, competing module identity).
  * Ruff runs in the package directory, so it picks up that package's
    configuration.
  * Findings are attributed to the diff: only an error on a line the change
    added is a failure. Pre-existing debt is reported separately and does not
    block the change.

Exit code: 0 if all checks pass, 1 if any check fails.
Use --gate to enforce in CI.

Usage:
    python .github/scripts/code_review.py                           # full suite, diff vs main
    python .github/scripts/code_review.py --base master              # vs master
    python .github/scripts/code_review.py --files src/foo.py         # specific files
    python .github/scripts/code_review.py --type-only                # skip tests (faster)
    python .github/scripts/code_review.py --test-only               # skip type check
    python .github/scripts/code_review.py --review-format            # full human report
    python .github/scripts/code_review.py --github-annotations       # CI annotations output
    python .github/scripts/code_review.py --open                    # open issues only
    python .github/scripts/code_review.py --gate                   # exit code = pass/fail
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from code_review_checks import (
    check_missing_tests,
    check_mypy,
    check_naming,
    check_pytest,
    check_ruff,
    check_ruff_format,
)
from code_review_model import CheckStatus, ReviewReport, run
from code_review_topology import (
    Bucket,
    build_buckets,
    diff_touched_lines,
    resolve_base_ref,
)

ROOT = Path(__file__).resolve().parents[2]


def _all_lines(rel: str) -> set[int]:
    """Every line of a file — used when reviewing explicitly named files."""
    try:
        text = (ROOT / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    return set(range(1, len(text.splitlines()) + 1))


def collect_changed_files(base_ref: str) -> tuple[list[str], str]:
    """Repo-relative paths of the .py files the change touched, plus the ref used."""
    resolved = resolve_base_ref(base_ref)
    if resolved is None:
        raise SystemExit(
            f"code_review: cannot resolve base ref {base_ref!r}. "
            f"Neither {base_ref!r} nor 'origin/{base_ref}' exists in this checkout. "
            f"Refusing to report a vacuous review."
        )

    result = run(["git", "diff", "--name-only", f"{resolved}...HEAD"])
    if result.returncode != 0:
        raise SystemExit(
            f"code_review: `git diff --name-only {resolved}...HEAD` failed "
            f"(rc={result.returncode}): {result.stderr.strip()}"
        )
    files = [f.strip().replace("\\", "/") for f in result.stdout.splitlines() if f.strip()]
    return [f for f in files if f.endswith(".py") and (ROOT / f).exists()], resolved


def collect_explicit_files(paths: list[str]) -> list[str]:
    out = []
    for p in paths:
        path = Path(p)
        if not path.is_absolute():
            path = ROOT / path
        try:
            rel = path.resolve().relative_to(ROOT.resolve()).as_posix()
        except ValueError:
            continue
        if rel.endswith(".py") and path.exists():
            out.append(rel)
    return out


def build_report(
    buckets: list[Bucket],
    base_ref: str,
    files_changed: int,
    type_only: bool,
    test_only: bool,
    strict: bool,
    missing: bool,
) -> ReviewReport:
    report = ReviewReport(base_ref=base_ref, files_changed=files_changed)

    for bucket in buckets:
        if not test_only:
            report.results.append(check_mypy(bucket, strict=strict))
        if not type_only and not test_only:
            report.results.append(check_ruff(bucket))
            report.results.append(check_ruff_format(bucket))
            report.results.append(check_naming(bucket))
        if not type_only:
            report.results.append(check_pytest(bucket))
            if missing:
                report.results.append(check_missing_tests(bucket))

    return report


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
        lines.append(f"  {icon} [{r.status.name}] {r.name:<28} {r.summary}")

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

    preexisting = [d for r in report.results for d in r.preexisting]
    if preexisting:
        lines.append("-" * 70)
        lines.append(
            f"  NOTE: {len(preexisting)} pre-existing finding(s) — not caused by this change:"
        )
        for d in preexisting[:10]:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Master code review orchestrator")
    parser.add_argument("--base", default="main", help="Base branch (default: main)")
    parser.add_argument(
        "--files",
        nargs="+",
        metavar="F",
        help="Specific files to review (overrides --base diff)",
    )
    parser.add_argument("--type-only", action="store_true", help="Run type check only")
    parser.add_argument("--test-only", action="store_true", help="Run test suite check only")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Deprecated — each package's own mypy configuration is canonical",
    )
    parser.add_argument("--review-format", action="store_true", help="Full human-readable report")
    parser.add_argument(
        "--github-annotations",
        action="store_true",
        help="Output GitHub Actions annotations format",
    )
    parser.add_argument(
        "--open-issues",
        action="store_true",
        help="Show only open issues (errors + warnings)",
    )
    parser.add_argument(
        "--missing",
        action="store_true",
        help="Also report source files without a matching test (alias used by CI)",
    )
    parser.add_argument("--gate", action="store_true", help="Exit code = pass/fail (for CI)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument(
        "--package",
        default="",
        help="Review only this package path (default: every package the diff touches)",
    )
    args = parser.parse_args()

    if args.strict:
        print(
            "code_review: --strict is ignored. Each package has its own mypy "
            "configuration and that configuration is canonical; a global "
            "--strict would contradict the CI matrix.",
            file=sys.stderr,
        )

    if args.files:
        rel_files = collect_explicit_files(args.files)
        # Explicitly named files are reviewed in full: every line counts as
        # touched, so nothing can hide outside the diff.
        touched = {rel: _all_lines(rel) for rel in rel_files}
        base_ref = args.base
    else:
        rel_files, base_ref = collect_changed_files(args.base)
        touched = diff_touched_lines(base_ref)

    if not rel_files:
        print("code_review: no Python files in the diff — nothing to review")
        return 0

    buckets = build_buckets(rel_files, touched)
    if args.package:
        wanted = args.package.strip("/")
        buckets = [b for b in buckets if b.spec and b.spec.path == wanted]

    report = build_report(
        buckets,
        base_ref=base_ref,
        files_changed=len(rel_files),
        type_only=args.type_only,
        test_only=args.test_only,
        strict=args.strict,
        missing=args.missing or args.open_issues,
    )

    if args.github_annotations:
        print(format_github_annotations(report))
    elif args.review_format:
        print(format_review_report(report))
    elif args.json:
        print(
            json.dumps(
                {
                    "all_passed": report.all_passed(),
                    "base_ref": report.base_ref,
                    "files_changed": report.files_changed,
                    "checks": [
                        {
                            "name": r.name,
                            "status": r.status.name,
                            "summary": r.summary,
                            "details": r.details,
                            "preexisting": r.preexisting,
                        }
                        for r in report.results
                    ],
                },
                indent=2,
            )
        )
    else:
        if report.all_passed():
            print(f"✅ All checks passed ({len(rel_files)} file(s))")
        else:
            for r in report.failed_checks():
                print(f"❌ {r.name}: {r.summary}")

    if args.gate:
        return 0 if report.all_passed() else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
