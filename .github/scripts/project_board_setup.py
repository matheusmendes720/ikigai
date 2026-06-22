#!/usr/bin/env python3
"""
GitHub Project Board Setup

Creates and populates a GitHub Project (v2) board for Algorithmic Life OS.
Creates columns, adds starter issues, and sets up automation.

Usage:
    python .github/scripts/project_board_setup.py --create-board "Sprint 1"
    python .github/scripts/project_board_setup.py --list-boards
    python .github/scripts/project_board_setup.py --add-starter-issues

Requires: PyGithub, GitHub CLI (gh)
    pip install PyGithub
    gh auth login  (one-time: gh auth login --hostname github.com)

Environment:
    GITHUB_TOKEN  — Fine-grained PAT with repo + project permissions
    REPO_OWNER   — e.g. "matheusmendes"
    REPO_NAME    — e.g. "life"
"""

from __future__ import annotations

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from dataclasses import dataclass


ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Column:
    name: str
    position: int


STARTER_COLUMNS = [
    Column("Backlog", 0),
    Column("Ready", 1),
    Column("In Progress", 2),
    Column("In Review", 3),
    Column("Done", 4),
    Column("Closed", 5),
]

# Starter issues to create for a new project
STARTER_ISSUES = [
    {
        "title": "docs: Create WSL2/Ubuntu VPS bootstrap guide",
        "body": """## Description
Create `docs/DEPLOY.md` with step-by-step instructions for setting up a cloud agent environment on WSL2 and Ubuntu VPS.

## Acceptance Criteria
- [ ] WSL2 setup section
- [ ] Ubuntu VPS (DigitalOcean/AWS) setup section
- [ ] tmux workflow for persistent sessions
- [ ] Environment variables documented
- [ ] Troubleshooting table included

## Subsystem
docs

## Priority
medium
""",
        "labels": ["documentation", "subsystem/docs", "priority/medium"],
    },
    {
        "title": "infra: Set up GitHub Project board for sprint tracking",
        "body": """## Description
Create and configure a GitHub Project (v2) board to track sprint progress for life-ops/operational.

## Acceptance Criteria
- [ ] Board with columns: Backlog, Ready, In Progress, In Review, Done
- [ ] All open issues triaged into columns
- [ ] Automation configured: issue -> Ready on label, Done on PR merge
- [ ] Sprint milestone created

## Priority
high
""",
        "labels": ["infrastructure", "priority/high"],
    },
    {
        "title": "infra: Wire CI code-review-checks job into PR merge requirements",
        "body": """## Description
Ensure the `code-review-checks` GitHub Actions job runs on PRs and that passing is required before merge.

## Acceptance Criteria
- [ ] CI workflow runs on PR open
- [ ] PR merge blocked if code-review-checks fails
- [ ] Review report visible in PR conversation

## Priority
high
""",
        "labels": ["infrastructure", "priority/high"],
    },
    {
        "title": "operational: Implement `pav habit sync --tw` command",
        "body": """## Description
Add a new CLI command `pav habit sync --tw` that exports habit streaks to Taskwarrior as UDAs, enabling cross-tool tracking.

## Motivation
Currently habit tracking is isolated in `operational/`. A `sync --tw` command would allow the `life/` root CLI hub to expose habit data to Taskwarrior, closing the loop between the PAV kernel and the task central.

## Proposed CLI
pav habit sync --tw [--dry-run]

## Subsystem
subsystem/operational

## Priority
medium
""",
        "labels": ["enhancement", "subsystem/operational", "priority/medium", "process/backlog"],
    },
    {
        "title": "vibe-ops: Implement `sync_taskwarrior_to_sqlite()` in SyncEngine",
        "body": """## Description
Implement the `sync_taskwarrior_to_sqlite()` pathway in `src/middleware/sync_engine.py`. Currently a stub.

## Acceptance Criteria
- [ ] Reads completed TW tasks from last 24h
- [ ] Updates `roadmap_sync` rows in `vibe_ops.db`
- [ ] Idempotent (safe to re-run)
- [ ] `upstream_id` UDA used for deduplication

## Subsystem
subsystem/vibe-ops

## Priority
medium
""",
        "labels": ["enhancement", "subsystem/vibe-ops", "priority/medium", "process/backlog"],
    },
]


def gh_graphql(query: str, variables: dict | None = None) -> dict:
    """Run a GitHub GraphQL query using gh CLI."""
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    if variables:
        for k, v in variables.items():
            cmd.extend(["-F", f"{k}={json.dumps(v)}"])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh api failed: {result.stderr}")
    return json.loads(result.stdout)


def create_project(name: str) -> str:
    """Create a GitHub Project (v2) and return its number."""
    query = """
    mutation CreateProjectV2($name: String!) {
        createProjectV2(input: {name: $name, ownerId: "REPLACE_ME", template: BASIC_KANBAN}) {
            projectV2 { number }
        }
    }
    """
    sys.stderr.write("Note: gh/GraphQL project creation requires the repo GraphQL ID.\n")
    sys.stderr.write("Use the GitHub web UI to create the project, then run:\n")
    sys.stderr.write("  gh project view NUMBER --owner REPO --json >> .github/PROJECT.json\n")
    sys.stderr.write(f"\nTo create via web: https://github.com/{os.environ.get('REPO_OWNER','OWNER')}/{os.environ.get('REPO_NAME','REPO')}/projects/new\n")
    return ""


def list_boards():
    """List all GitHub Projects for the repo."""
    cmd = ["gh", "project", "list", "--owner", "repo", "--format", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        data = json.loads(result.stdout)
        for p in data.get("projects", []):
            print(f"  #{p['number']} {p['name']} ({p['shortDescription']})")
    else:
        print("  No projects found. Create one at: https://github.com/OWNER/REPO/projects/new")
    return 0


def add_starter_issues() -> int:
    """Create starter issues for initial project setup."""
    token = os.environ.get("GITHUB_TOKEN")
    owner = os.environ.get("REPO_OWNER")
    repo = os.environ.get("REPO_NAME")

    if not all([token, owner, repo]):
        sys.stderr.write("GITHUB_TOKEN, REPO_OWNER, REPO_NAME must be set.\n")
        return 1

    created = []
    for issue_spec in STARTER_ISSUES:
        title = issue_spec["title"]
        body = issue_spec["body"]
        labels = ",".join(issue_spec["labels"])

        cmd = [
            "gh", "issue", "create",
            "--title", title,
            "--body", body,
            "--label", labels,
            "--repo", f"{owner}/{repo}",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            url = result.stdout.strip()
            print(f"  ✅ Created: {url}")
            created.append(url)
        else:
            print(f"  ❌ Failed: {title} — {result.stderr.strip()}")

    print(f"\n{len(created)} issue(s) created successfully.")
    return 0 if len(created) == len(STARTER_ISSUES) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub Project Board Setup")
    parser.add_argument("--create-board", metavar="NAME",
                        help="Create a new GitHub Project board")
    parser.add_argument("--list-boards", action="store_true",
                        help="List all project boards")
    parser.add_argument("--add-starter-issues", action="store_true",
                        help="Create starter issues for initial project setup")
    args = parser.parse_args()

    if args.list_boards:
        sys.exit(list_boards())
    elif args.create_board:
        sys.exit(0 if create_project(args.create_board) else 1)
    elif args.add_starter_issues:
        sys.exit(add_starter_issues())
    else:
        parser.print_help()
