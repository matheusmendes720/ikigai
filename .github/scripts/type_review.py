#!/usr/bin/env python3
"""
Type-Check Reviewer

Runs mypy on changed files only (vs. main branch) and produces a review-friendly
report grouped by severity: error > warning > note.

Designed to run in CI before a PR is opened — catches type regressions before review.

Usage:
    python -m github.scripts.type_review                        # diff vs main
    python -m github.scripts.type_review --base main           # diff vs main
    python -m github.scripts.type_review --files src/foo.py    # specific files only
    python -m github.scripts.type_review --strict              # mypy --strict
    python -m github.scripts.type_review --review-format        # human review output

Requires: mypy
    pip install mypy types-PyYAML
"""

from __future__ import annotations

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict


ROOT = Path(__file__).resolve().parents[2]
CHANGED_FILES_CACHE = ROOT / ".github" / ".type_review_changed_files"


@dataclass
class Diagnostic:
    file: str
    line: int
    severity: str  # error, warning, note
    code: str
    message: str
    full_message: str


@dataclass
class TypeReviewResult:
    diagnostics: list[Diagnostic] = field(default_factory=list)
    files_analyzed: int = 0
    files_with_errors: int = 0
    errors: int = 0
    warnings: int = 0
    notes: int = 0
    clean_files: list[str] = field(default_factory=list)

    def has_errors(self) -> bool:
        return self.errors > 0

    def is_clean(self) -> bool:
        return self.errors == 0 and self.warnings == 0


def get_changed_files(base_ref: str = "main") -> list[Path]:
    """Return Python files changed vs. base_ref."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD", "--", "*.py"],
            cwd=ROOT, capture_output=True, text=True, text=True
        )
        files = [ROOT / f for f in result.stdout.strip().splitlines() if f]
        # Filter to files that still exist
        return [f for f in files if f.exists()]
    except Exception as e:
        sys.stderr.write(f"[WARN] Could not get changed files: {e}\n")
        return []


def run_mypy_on_files(files: list[Path], strict: bool = False, json_output: bool = True
                      ) -> dict:
    """Run mypy on a list of files and return JSON output."""
    if not files:
        return {"files": [], "errors": []}

    args = [
        "uv", "run", "mypy",
        "--no-error-summary",
        "--no-pretty",
        "--show-error-codes",
        "--show-column-numbers",
    ]
    if strict:
        args.append("--strict")
    if json_output:
        args.append("--output=json")
    args.extend(str(f) for f in files)

    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)

    if json_output:
        try:
            return json.loads(result.stdout) if result.stdout.strip() else {"files": [], "errors": []}
        except json.JSONDecodeError:
            return {"files": [], "errors": [], "_raw": result.stdout}
    return {"_raw": result.stdout, "_stderr": result.stderr}


def parse_json_output(mypy_output: dict, all_files: list[Path]) -> TypeReviewResult:
    """Parse mypy JSON output into a TypeReviewResult."""
    result = TypeReviewResult()
    result.files_analyzed = len(all_files)

    error_map: dict[str, list[Diagnostic]] = defaultdict(list)
    seen_files = set()

    for entry in mypy_output.get("files", []):
        path = Path(entry["file"])
        rel = str(path.relative_to(ROOT))
        seen_files.add(rel)
        for err in entry.get("errors", []):
            diag = Diagnostic(
                file=rel,
                line=err.get("line", 0),
                severity=err.get("severity", "error"),
                code=err.get("code", ""),
                message=err.get("message", ""),
                full_message=f"{rel}:{err.get('line', 0)}: {err.get('severity', 'error')}: {err.get('message', '')}"
            )
            result.diagnostics.append(diag)
            if diag.severity == "error":
                result.errors += 1
            elif diag.severity == "warning":
                result.warnings += 1
            else:
                result.notes += 1
            error_map[rel].append(diag)

    result.files_with_errors = len(error_map)
    result.clean_files = [str(f.relative_to(ROOT)) for f in all_files
                          if str(f.relative_to(ROOT)) not in seen_files]
    return result


def format_review_output(result: TypeReviewResult) -> str:
    """Format the review result as human-readable text."""
    lines = []
    lines.append("=" * 60)
    lines.append("TYPE CHECK REVIEW REPORT")
    lines.append("=" * 60)

    if result.is_clean():
        lines.append("✅ CLEAN — no type errors found")
        if result.clean_files:
            lines.append(f"\nFiles analyzed ({result.files_analyzed}):")
            for f in result.clean_files:
                lines.append(f"  ✓ {f}")
        return "\n".join(lines)

    # Group by severity
    errors = [d for d in result.diagnostics if d.severity == "error"]
    warnings = [d for d in result.diagnostics if d.severity == "warning"]

    lines.append(f"\n❌ {result.errors} error(s), ⚠️ {result.warnings} warning(s)")
    lines.append(f"   {result.files_with_errors} file(s) with issues\n")

    if errors:
        lines.append("## ERRORS (must fix before merge)")
        for diag in sorted(errors, key=lambda d: (d.file, d.line)):
            lines.append(f"  {diag.file}:{diag.line}  [{diag.code}]")
            lines.append(f"    {diag.message}")

    if warnings:
        lines.append("\n## WARNINGS (consider fixing)")
        for diag in sorted(warnings, key=lambda d: (d.file, d.line)):
            lines.append(f"  {diag.file}:{diag.line}  [{diag.code}]")
            lines.append(f"    {diag.message}")

    lines.append(f"\n## CLEAN FILES ({len(result.clean_files)})")
    for f in result.clean_files:
        lines.append(f"  ✓ {f}")

    return "\n".join(lines)


def format_github_annotations(result: TypeReviewResult) -> str:
    """Output in GitHub Actions annotations format (for CI)."""
    lines = []
    for diag in result.diagnostics:
        sev = "error" if diag.severity == "error" else "warning"
        lines.append(
            f"::{sev} file={diag.file},line={diag.line},title={diag.code}::{diag.message}"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Type-check review on changed files")
    parser.add_argument("--base", default="main",
                        help="Base branch to diff against (default: main)")
    parser.add_argument("--files", nargs="+", type=Path, metavar="F",
                        help="Specific files to check (overrides --base diff)")
    parser.add_argument("--strict", action="store_true",
                        help="Run mypy --strict")
    parser.add_argument("--review-format", action="store_true",
                        help="Human review-friendly output")
    parser.add_argument("--annotations", action="store_true",
                        help="GitHub Actions annotations format")
    parser.add_argument("--json-output", action="store_true",
                        help="Machine-readable JSON output")
    args = parser.parse_args()

    if args.files:
        files = [f if f.is_absolute() else ROOT / f for f in args.files]
    else:
        files = get_changed_files(args.base)

    if not files:
        print("No changed Python files found.")
        return 0 if not args.files else 1

    print(f"Checking {len(files)} file(s)...", file=sys.stderr)
    mypy_out = run_mypy_on_files(files, strict=args.strict)
    result = parse_json_output(mypy_out, files)

    if args.annotations:
        print(format_github_annotations(result))
    elif args.review_format:
        print(format_review_output(result))
    elif args.json_output:
        print(json.dumps({
            "errors": result.errors,
            "warnings": result.warnings,
            "notes": result.notes,
            "files_analyzed": result.files_analyzed,
            "files_with_errors": result.files_with_errors,
            "clean_files": result.clean_files,
            "diagnostics": [
                {"file": d.file, "line": d.line, "severity": d.severity,
                 "code": d.code, "message": d.message}
                for d in result.diagnostics
            ]
        }, indent=2))
    else:
        # Default: concise summary
        if result.is_clean():
            print(f"✅ Clean — {result.files_analyzed} file(s), no type errors")
        else:
            print(f"❌ {result.errors} error(s), {result.warnings} warning(s), "
                  f"{result.files_with_errors} file(s) affected")
            if args.strict:
                print("(rerun without --strict to see details)")

    return 0 if result.is_clean() else 1


if __name__ == "__main__":
    sys.exit(main())
