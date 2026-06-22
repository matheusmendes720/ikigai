#!/usr/bin/env python3
"""
GitHub Project Board Manager

Usage:
    python -m github.scripts.project_board --assign-issue 42 --to-column "In Progress"
    python -m github.scripts.project_board --sync-labels          # sync labels.yml to repo

Requires: PyGithub
    pip install PyGithub

Environment:
    GITHUB_TOKEN   — classic token with repo:+project permissions
    REPO_OWNER     — e.g. "matheusmendes"
    REPO_NAME      — e.g. "life"
    PROJECT_NUMBER — the GitHub Project number (find in project URL)
"""

import os
import sys
import argparse
from pathlib import Path

try:
    from github import Github
except ImportError:
    sys.stderr.write("PyGithub not installed. Run: pip install PyGithub\n")
    sys.exit(1)


def get_client():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.stderr.write("GITHUB_TOKEN environment variable not set.\n")
        sys.exit(1)
    return Github(token)


def assign_issue_to_column(issue_number: int, column_name: str):
    """Move an issue to a specific project column."""
    # This requires GitHub Projects v2 GraphQL API.
    # For Projects v1 (classic), use the REST API instead.
    sys.stderr.write(
        f"Would move issue #{issue_number} to column '{column_name}'.\n"
        "GitHub Projects v2 requires GraphQL. "
        "See: https://docs.github.com/en/issues/sharing-your-project-about-automation\n"
    )


def sync_labels():
    """Sync labels from .github/labels.yml to the repository."""
    gh = get_client()
    owner = os.environ.get("REPO_OWNER")
    repo_name = os.environ.get("REPO_NAME")

    if not owner or not repo_name:
        sys.stderr.write("REPO_OWNER and REPO_NAME must be set.\n")
        sys.exit(1)

    repo = gh.get_repo(f"{owner}/{repo_name}")
    labels_file = Path(__file__).parent.parent / "labels.yml"

    import yaml
    with open(labels_file) as f:
        labels_def = yaml.safe_load(f)

    existing = {l.name for l in repo.get_labels()}
    for label in labels_def:
        name = label["name"]
        if name in existing:
            print(f"  [exists] {name}")
        else:
            repo.create_label(
                name=name,
                color=label["color"].lstrip("#"),
                description=label["description"]
            )
            print(f"  [created] {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub Project Board Manager")
    parser.add_argument("--assign-issue", type=int, metavar="N",
                        help="Issue number to assign")
    parser.add_argument("--to-column", metavar="COL",
                        help="Column name to move issue to")
    parser.add_argument("--sync-labels", action="store_true",
                        help="Sync labels from labels.yml to repo")
    args = parser.parse_args()

    if args.sync_labels:
        sync_labels()
    elif args.assign_issue and args.to_column:
        assign_issue_to_column(args.assign_issue, args.to_column)
    else:
        parser.print_help()
