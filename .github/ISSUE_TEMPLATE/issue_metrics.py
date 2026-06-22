#!/usr/bin/env python3
"""
Issue Metrics Tracker

Parses all issues and generates a sprint health report:
open count, avg age, blocked items, distribution by label/priority.

Usage:
    python -m github.scripts.issue_metrics --open
    python -m github.scripts.issue_metrics --sprint-health
    python -m github.scripts.issue_metrics --backlog-age

Requires: PyGithub
    pip install PyGithub

Environment:
    GITHUB_TOKEN   — classic token with repo permissions
    REPO_OWNER     — e.g. "matheusmendes"
    REPO_NAME      — e.g. "life"
"""

from __future__ import annotations

import os
import sys
import argparse
from datetime import datetime, timezone
from collections import defaultdict

try:
    from github import Github
except ImportError:
    sys.stderr.write("PyGithub not installed. Run: pip install PyGithub\n")
    sys.exit(1)


def get_client():
    token = os.environ.get("GITHUB_TOKEN")
    owner = os.environ.get("REPO_OWNER")
    name = os.environ.get("REPO_NAME")
    if not all([token, owner, name]):
        sys.stderr.write("GITHUB_TOKEN, REPO_OWNER, REPO_NAME must be set.\n")
        sys.exit(1)
    return Github(token).get_repo(f"{owner}/{name}")


def report_open():
    repo = get_client()
    issues = list(repo.get_issues(state="open"))
    by_label = defaultdict(list)
    by_priority = defaultdict(list)
    ages: list[tuple[str, int]] = []  # (title, days_open)

    now = datetime.now(timezone.utc)
    total = 0

    for issue in issues:
        if issue.pull_request:
            continue
        total += 1
        days = (now - issue.created_at.replace(tzinfo=timezone.utc)).days
        ages.append((issue.title, days))
        for label in issue.labels:
            by_label[label.name].append(issue.number)
            if label.name.startswith("priority/"):
                by_priority[label.name] = issue.number

    ages.sort(key=lambda x: x[1], reverse=True)
    oldest = ages[:5]

    print(f"# Open Issues: {total}\n")
    print("## Oldest Open Issues")
    for title, days in oldest:
        print(f"  [{days}d] {title}")

    print("\n## By Subsystem")
    for label, numbers in sorted(by_label.items()):
        if label.startswith("subsystem/"):
            print(f"  {label}: {len(numbers)}")

    print("\n## By Priority")
    for p in ["priority/critical", "priority/high", "priority/medium", "priority/low"]:
        print(f"  {p}: {len(by_priority.get(p, []))}")

    # Blocked
    blocked = [i for i in issues if "status/blocked" in [l.name for l in i.labels]]
    if blocked:
        print(f"\n## Blocked ({len(blocked)})")
        for issue in blocked:
            print(f"  #{issue.number} {issue.title}")

    return 0


def report_sprint_health():
    repo = get_client()
    issues = list(repo.get_issues(state="open"))
    sprint_issues = [
        i for i in issues
        if "process/sprint" in [l.name for l in i.labels] and not i.pull_request
    ]
    blocked = [
        i for i in sprint_issues
        if "status/blocked" in [l.name for l in i.labels]
    ]

    print(f"# Sprint Health\n")
    print(f"  Total sprint issues: {len(sprint_issues)}")
    print(f"  Blocked: {len(blocked)}")
    print(f"  Active: {len(sprint_issues) - len(blocked)}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub Issue Metrics")
    parser.add_argument("--open", action="store_true", help="Full open issues report")
    parser.add_argument("--sprint-health", action="store_true", help="Sprint health summary")
    args = parser.parse_args()

    if args.open:
        sys.exit(report_open())
    elif args.sprint_health:
        sys.exit(report_sprint_health())
    else:
        parser.print_help()
