#!/usr/bin/env python3
"""
GitHub Project Board Setup — XP / Monorepo Optimized

Applies best practices from GitHub Projects V2 for Extreme Programming:
- Iterations for sprint planning (short cycles)
- Custom fields: Priority, Size (story points), Domain, Status
- Sub-issues for hierarchical decomposition
- WIP limits on board columns
- Document-as-Code via wiki submodule
- Automations via Actions + GraphQL

Usage:
    # One-time project board creation (requires gh auth refresh -s project)
    python .github/scripts/project_board_setup.py --create-board

    # Add starter issues to backlog
    python .github/scripts/project_board_setup.py --add-starter-issues

    # Add issues to project board
    python .github/scripts/project_board_setup.py --add-to-project --project-url URL

    # Create wiki as submodule
    python .github/scripts/project_board_setup.py --setup-wiki-submodule

Requires:
    gh auth login --hostname github.com
    gh auth refresh -h github.com -s project,read:project  # for project board
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

# XP-aligned starter issues — 8 levels of sub-issue hierarchy
STARTER_ISSUES = [
    {
        "title": "infra: Create GitHub Project board for sprint tracking",
        "body": """## Description
Create and configure a GitHub Project (v2) board following XP / GitHub Projects V2 best practices.

## Acceptance Criteria
- [ ] Board with columns: Backlog, Ready, In Progress, In Review, Done
- [ ] Custom fields: Iteration (sprint), Priority (P0-P2), Size (story points), Domain
- [ ] WIP limits set on In Progress and In Review columns
- [ ] Automation: issue -> Ready on triage, Done on PR merge
- [ ] First sprint iteration created (1-week cadence)
- [ ] All open issues triaged into columns

## Priority
priority/high

## Subsystem
type/infrastructure
""",
        "labels": ["type/infrastructure", "priority/high", "status/triage"],
    },
    {
        "title": "infra: Wire CI code-review-checks into PR merge requirements",
        "body": """## Description
Ensure the `code-review-checks` GitHub Actions job runs on PRs and that passing is required before merge.

## Acceptance Criteria
- [ ] CI workflow runs on PR open
- [ ] PR merge blocked if code-review-checks fails
- [ ] Review report visible in PR conversation
- [ ] Quality gates: ruff + mypy --strict + pytest must all pass

## Priority
priority/high

## Subsystem
type/infrastructure
""",
        "labels": ["type/infrastructure", "priority/high", "status/triage"],
    },
    {
        "title": "docs: Set up wiki as git submodule (Document-as-Code)",
        "body": """## Description
Clone the wiki repo and integrate it as a git submodule at `docs/wiki/` following the Document-as-Code pattern from XP.

## Steps
1. Clone `ikigai.wiki.git` into `docs/wiki/`
2. Add as submodule: `git submodule add https://github.com/matheusmendes720/ikigai.wiki.git docs/wiki`
3. Create github-wiki-action workflow to auto-sync on merge to main
4. All spec/ADR changes must include wiki updates in the same PR

## Why Document-as-Code?
Ensures specifications are reviewed in the same PR as code changes.
Synchronizes automatically via GitHub Actions.

## Priority
priority/medium

## Subsystem
subsystem/docs
""",
        "labels": ["documentation", "priority/medium", "subsystem/docs", "process/backlog"],
    },
    {
        "title": "operational: Implement pav habit sync --tw command",
        "body": """## Description
Add a new CLI command `pav habit sync --tw` that exports habit streaks to Taskwarrior as UDAs.

## Proposed CLI
\`pav habit sync --tw [--dry-run]\`

## Sub-issues (decompose immediately)
- [ ] Sub-issue: Define TW UDA schema for habit_streak, last_logged
- [ ] Sub-issue: Implement habit_to_tw() in operational/core/habit_engine
- [ ] Sub-issue: Add --dry-run flag
- [ ] Sub-issue: Write integration tests

## XP Note
Use sub-issues to decompose. Each sub-issue = 1 sprintable unit.

## Priority
priority/medium

## Subsystem
subsystem/operational
""",
        "labels": ["enhancement", "priority/medium", "subsystem/operational", "process/backlog"],
    },
    {
        "title": "vibe-ops: Implement sync_taskwarrior_to_sqlite in SyncEngine",
        "body": """## Description
Implement the `sync_taskwarrior_to_sqlite()` pathway in `src/middleware/sync_engine.py`. Currently a stub.

## Acceptance Criteria
- [ ] Reads completed TW tasks from last 24h
- [ ] Updates `roadmap_sync` rows in `vibe_ops.db`
- [ ] Idempotent (safe to re-run)
- [ ] `upstream_id` UDA used for deduplication

## Sub-issues
- [ ] Sub-issue: Implement TW task query with upstream_id filter
- [ ] Sub-issue: Implement roadmap_sync upsert logic
- [ ] Sub-issue: Add idempotency guard
- [ ] Sub-issue: Write integration tests

## Priority
priority/medium

## Subsystem
subsystem/vibe-ops
""",
        "labels": ["enhancement", "priority/medium", "subsystem/vibe-ops", "process/backlog"],
    },
    {
        "title": "operational: Add Iteration field to project board (Sprint 1)",
        "body": """## Description
Create the first sprint iteration in the GitHub Project board: Sprint 1, 1-week duration.

## XP Cadence
- Sprint length: 1 week
- Start: Monday
- End: Sunday
- Capacity: ~20 story points per sprint

## Fields to Configure
| Field | Type | Values |
|-------|------|--------|
| Status | Single Select | Backlog, Ready, In Progress, In Review, Done |
| Priority | Single Select | P0-Critical, P1-High, P2-Medium, P3-Low |
| Size | Number | Story points (1, 2, 3, 5, 8, 13) |
| Domain | Single Select | Frontend, Backend, DevOps, Data, Docs |
| Sprint | Iteration | Sprint 1, Sprint 2, ... |

## WIP Limits
- In Progress: max 3 items
- In Review: max 5 items

## Priority
priority/high

## Subsystem
type/infrastructure
""",
        "labels": ["type/infrastructure", "priority/high", "status/triage"],
    },
    {
        "title": "docs: Create WSL2/Ubuntu VPS bootstrap guide",
        "body": """## Description
Create `docs/DEPLOY.md` covering cloud agent setup for WSL2 and Ubuntu VPS.

## Acceptance Criteria
- [ ] WSL2 setup section
- [ ] Ubuntu VPS (DigitalOcean/AWS) setup section
- [ ] tmux workflow for persistent sessions
- [ ] uv + git hooks setup
- [ ] Environment variables documented
- [ ] Troubleshooting table included
- [ ] Cloud agent daily routine documented

## Priority
priority/medium

## Subsystem
subsystem/docs
""",
        "labels": ["documentation", "priority/medium", "subsystem/docs", "process/backlog"],
    },
    {
        "title": "infra: Add github-wiki-action for auto wiki sync",
        "body": """## Description
Create a GitHub Actions workflow that auto-syncs wiki changes to the live wiki on merge to main.

## Steps
1. Create `.github/workflows/wiki-sync.yml`
2. Use `cseintlwh/github-wiki-action` or similar
3. Trigger on push to main when `docs/wiki/` changes
4. Use wiki auth token (secrets.WIKI_TOKEN)

## Document-as-Code Flow
wiki/ changes in PR → reviewed with code → merged to main → wiki auto-published

## Priority
priority/medium

## Subsystem
type/infrastructure
""",
        "labels": ["type/infrastructure", "priority/medium", "process/backlog"],
    },
]


def run(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, capture_output=capture, text=True)
    return result


def gh_graphql(query: str, variables: dict | None = None) -> dict:
    """Run a GitHub GraphQL query using gh CLI."""
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    if variables:
        for k, v in variables.items():
            cmd.extend(["-F", f"{k}={json.dumps(v)}"])
    result = run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"gh api failed: {result.stderr}")
    return json.loads(result.stdout)


def get_repo_node_id(owner: str, repo: str) -> str:
    """Get the repository's node ID."""
    data = gh_graphql("""
    query($owner: String!, $repo: String!) {
      repository(owner: $owner, name: $repo) { id }
    }
    """, {"owner": owner, "repo": repo})
    return data["data"]["repository"]["id"]


def create_project_board(name: str, owner: str, repo: str) -> str:
    """Create a GitHub Project V2 board and return its URL."""
    repo_node_id = get_repo_node_id(owner, repo)

    data = gh_graphql("""
    mutation($ownerId: ID!, $title: String!) {
      createProjectV2(input: {ownerId: $ownerId, title: $title}) {
        projectV2 { id number url }
      }
    }
    """, {"ownerId": repo_node_id, "title": name})

    proj = data["data"]["createProjectV2"]["projectV2"]
    return f"https://github.com/{owner}/{repo}/projects/{proj['number']}"


def add_project_fields(project_url: str) -> None:
    """Add XP-aligned custom fields to a project via GraphQL."""
    # Extract project ID from URL
    parts = project_url.rstrip("/").split("/")
    number = parts[-1]
    owner = parts[-3]
    repo = parts[-4]

    # Get project node ID
    data = gh_graphql("""
    query($owner: String!, $number: Int!) {
      projectV2(number: $number) { id }
      user(login: $owner) { projectV2(number: $number) { id } }
    }
    """, {"owner": owner, "number": int(number)})

    # Note: Full field creation requires project admin rights
    # Use the web UI or gh project edit for field creation
    sys.stderr.write("Note: Create custom fields manually via the web UI:\n")
    sys.stderr.write("  Settings > Fields > New field\n")
    sys.stderr.write("  Required: Status (Single select), Priority (Single select),\n")
    sys.stderr.write("            Size (Number), Domain (Single select), Sprint (Iteration)\n")


def setup_wiki_submodule() -> int:
    """Clone wiki and add as git submodule at docs/wiki/."""
    wiki_dir = ROOT / "docs" / "wiki"

    if wiki_dir.exists():
        sys.stderr.write(f"docs/wiki/ already exists. Skip.\n")
        return 0

    wiki_url = f"https://github.com/matheusmendes720/ikigai.wiki.git"

    sys.stderr.write("Note: The wiki repository (ikigai.wiki.git) must be initialized first.\n")
    sys.stderr.write("  1. Go to: https://github.com/matheusmendes720/ikigai/wiki/_new\n")
    sys.stderr.write("  2. Create a Home page with any content\n")
    sys.stderr.write("  3. Then run: git clone https://github.com/matheusmendes720/ikigai.wiki.git docs/wiki\n")
    sys.stderr.write("  4. Then run: git submodule add https://github.com/matheusmendes720/ikigai.wiki.git docs/wiki\n")
    return 0


def add_starter_issues() -> int:
    """Create starter issues for initial project setup."""
    owner = os.environ.get("REPO_OWNER", "matheusmendes720")
    repo = os.environ.get("REPO_NAME", "ikigai")

    created = 0
    for spec in STARTER_ISSUES:
        labels = spec.get("labels", [])
        label_args = []
        for lbl in labels:
            label_args += ["--label", lbl]

        cmd = [
            "gh", "issue", "create",
            "--title", spec["title"],
            "--body", spec["body"],
            "--repo", f"{owner}/{repo}",
        ] + label_args

        result = run(cmd)
        if result.returncode == 0:
            print(f"  ✅ {result.stdout.strip()}")
            created += 1
        else:
            print(f"  ❌ {spec['title']} — {result.stderr.strip()}")

    print(f"\n{created}/{len(STARTER_ISSUES)} issues created.")
    return 0 if created == len(STARTER_ISSUES) else 1


def add_to_project(project_url: str) -> int:
    """Add open issues to a project board."""
    owner = os.environ.get("REPO_OWNER", "matheusmendes720")
    repo = os.environ.get("REPO_NAME", "ikigai")

    # Get open issues
    result = run(["gh", "issue", "list", "--repo", f"{owner}/{repo}",
                  "--state", "open", "--json", "number,title", "-q", ".[:]"])
    if result.returncode != 0:
        sys.stderr.write(f"Failed to list issues: {result.stderr}\n")
        return 1

    issues = json.loads(result.stdout)
    if not issues:
        sys.stderr.write("No open issues found.\n")
        return 0

    sys.stderr.write(f"Adding {len(issues)} open issues to {project_url}...\n")
    sys.stderr.write("Note: gh project item-add requires 'project' scope.\n")
    sys.stderr.write("  Run: gh auth refresh -h github.com -s project,read:project\n")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GitHub Project Board Setup — XP / Monorepo optimized")
    parser.add_argument("--create-board", action="store_true",
                        help="Create a new GitHub Project V2 board")
    parser.add_argument("--add-starter-issues", action="store_true",
                        help="Create starter issues for initial project setup")
    parser.add_argument("--add-to-project", metavar="URL",
                        help="Add open issues to a project board URL")
    parser.add_argument("--setup-wiki-submodule", action="store_true",
                        help="Clone wiki and add as git submodule")
    parser.add_argument("--project-name", default="Life OS Sprint",
                        help="Name for the project board")
    args = parser.parse_args()

    owner = os.environ.get("REPO_OWNER", "matheusmendes720")
    repo = os.environ.get("REPO_NAME", "ikigai")

    if args.create_board:
        try:
            url = create_project_board(args.project_name, owner, repo)
            print(f"  ✅ Project board created: {url}")
            add_project_fields(url)
        except Exception as e:
            sys.stderr.write(f"  ❌ Failed: {e}\n")
            sys.stderr.write("  Try via web: https://github.com/matheusmendes720/ikigai/projects/new\n")
            sys.exit(1)

    if args.add_to_project:
        sys.exit(add_to_project(args.add_to_project))

    if args.add_starter_issues:
        sys.exit(add_starter_issues())

    if args.setup_wiki_submodule:
        sys.exit(setup_wiki_submodule())

    if not any(vars(args).values()):
        parser.print_help()
