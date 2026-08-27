#!/usr/bin/env python3
"""
Vault ↔ Taskdog synchronization tool.

Compares entities in the IKIGAi vault with tasks in taskdog
and optionally syncs them bidirectionally.

Usage:
    python vault_taskdog_sync.py --status          # Show diff
    python vault_taskdog_sync.py --sync             # Sync vault → taskdog
    python vault_taskdog_sync.py --dry-run          # Show what would be synced
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

# ─── Paths ────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent.resolve()
VAULT_ROOT = REPO_ROOT / "data" / "matheus"
# Windows path mapping - taskdog is on Windows filesystem
TASKDOG_ROOT = Path("/mnt/c/Users/mathe/code_space/apps/dev-tools/taskdog")

# ─── Frontmatter parsing ─────────────────────────────────────────────────────


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse markdown frontmatter into (metadata, body)."""
    if not content.startswith("---\n"):
        return {}, content
    
    lines = content.split("\n")
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    
    if end_idx is None:
        return {}, content
    
    yaml_content = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1:]).strip()
    
    try:
        data = yaml.safe_load(yaml_content) or {}
    except yaml.YAMLError:
        data = {}
    
    return data, body


# ─── Taskdog helpers ──────────────────────────────────────────────────────────


def run_taskdog(args: list[str], timeout: float = 10.0) -> subprocess.CompletedProcess:
    """Run a taskdog CLI command."""
    import os
    env = os.environ.copy()
    env["COLUMNS"] = "200"
    env["LINES"] = "50"
    return subprocess.run(
        ["uv", "run", "taskdog"] + args,
        cwd=str(TASKDOG_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def get_taskdog_tasks() -> list[dict[str, Any]]:
    """Get all tasks from taskdog - parses the box-drawing table format."""
    result = run_taskdog(["list", "--fields", "id,name,status,priority,tags,deadline,estimated_duration,note"])
    if result.returncode != 0:
        print(f"⚠️  taskdog error: {result.stderr.strip() or result.stdout.strip()}")
        return []
    
    lines = result.stdout.strip().split("\n")
    tasks = []
    current_task = None
    current_line_idx = 0
    
    # Skip header lines (typically 4 lines: title, top border, column headers, separator)
    for line in lines[4:]:
        current_line_idx += 4
        # Skip border and separator lines
        if not line.strip() or line.startswith("┏") or line.startswith("┡") or line.startswith("╞") or line.startswith("└"):
            continue
        
        # Split by │ (box drawing character) and filter empty parts
        raw_parts = line.split("│")
        # Remove leading/trailing empty parts due to leading/trailing borders
        parts = [p.strip() for p in raw_parts[1:-1]]  # Skip first and last which are empty from border chars
        
        if len(parts) < 4:
            # Continuation line - append to current task name
            if current_task and len(parts) >= 2:
                current_task["name"] += " " + parts[1].strip()
            continue
        
        try:
            # First part is ID
            task_id = int(parts[0].strip())
            # Second part is name (may contain the full name or partial)
            name = parts[1].strip()
            # Third part is status
            status = parts[2].strip()
            # Fourth part is priority
            priority = int(parts[3].strip()) if parts[3].strip() else 0
            # Fifth part is tags
            tags_str = parts[4].strip() if len(parts) > 4 else ""
            
            task = {
                "id": task_id,
                "name": name,
                "status": status,
                "priority": priority,
                "tags": [t.strip().lower() for t in tags_str.split(",") if t.strip()],
            }
            tasks.append(task)
            current_task = task
        except (ValueError, IndexError) as e:
            # Continuation line or parse error
            if current_task and len(parts) >= 2:
                current_task["name"] += " " + parts[1].strip()
            continue
    
    return tasks


def create_taskdog_task(name: str, priority: int = 5, tags: list[str] | None = None, 
                       deadline: str | None = None, estimated_duration: float | None = None,
                       note: str | None = None) -> dict[str, Any] | None:
    """Create a task in taskdog."""
    args = ["add", name, "-p", str(priority)]
    if tags:
        for tag in tags:
            args.extend(["-t", tag])
    if deadline:
        args.extend(["-d", deadline])
    if estimated_duration:
        args.extend(["-e", str(estimated_duration)])
    if note:
        args.extend(["-n", note])
    
    result = run_taskdog(args)
    if result.returncode != 0:
        print(f"⚠️  Failed to create task '{name}': {result.stderr.strip()}")
        return None
    
    return {"name": name, "priority": priority, "tags": tags or [], "status": "PENDING"}


def delete_taskdog_task(task_id: int) -> bool:
    """Delete a task from taskdog."""
    result = run_taskdog(["rm", str(task_id)])
    return result.returncode == 0


def complete_taskdog_task(task_id: int) -> bool:
    """Mark a task as completed in taskdog."""
    result = run_taskdog(["done", str(task_id)])
    return result.returncode == 0


# ─── Vault helpers ────────────────────────────────────────────────────────────


def read_vault_entity(path: Path) -> dict[str, Any] | None:
    """Read a vault markdown file and return its frontmatter."""
    try:
        content = path.read_text(encoding="utf-8")
        data, _ = parse_frontmatter(content)
        return data
    except Exception as e:
        print(f"⚠️  Error reading {path}: {e}")
        return None


def get_vault_entities(entity_type: str) -> list[dict[str, Any]]:
    """Get all entities of a given type from the vault."""
    entities = []
    entity_dir = VAULT_ROOT / entity_type
    
    if not entity_dir.exists():
        return []
    
    for md_file in entity_dir.rglob("*.md"):
        data = read_vault_entity(md_file)
        if data:
            data["_file"] = str(md_file.relative_to(VAULT_ROOT))
            entities.append(data)
    
    return entities


# ─── Analysis ─────────────────────────────────────────────────────────────────


def analyze_vault_taskdog_gaps() -> dict[str, Any]:
    """Analyze gaps between vault and taskdog."""
    objectives = get_vault_entities("objectives")
    projects = get_vault_entities("projects")
    deliverables = get_vault_entities("deliverables")
    tasks = get_taskdog_tasks()
    
    # Find actionable vault items (IN_PROGRESS or TODO status)
    actionable_deliverables = [d for d in deliverables 
                               if d.get("status") in ("IN_PROGRESS", "TODO")]
    active_projects = [p for p in projects if p.get("status") == "ACTIVE"]
    
    # Taskdog ikigai-tagged tasks
    ikigai_tasks = [t for t in tasks if "ikigai" in [tag.lower() for tag in t.get("tags", [])]]
    
    # Find orphan test tasks - any task with "test" in name is suspect
    orphan_tasks = []
    for task in ikigai_tasks:
        task_name_lower = task["name"].lower()
        is_test = "test" in task_name_lower
        # Check if corresponds to any vault entity
        is_orphan = True
        for d in deliverables + projects:
            title = d.get("title", "").lower()
            slug = d.get("slug", "").lower()
            if title and (title in task_name_lower or slug in task_name_lower):
                is_orphan = False
                break
        if is_test and is_orphan:
            orphan_tasks.append(task)
    
    # Identify missing tasks based on vault state
    
    # 1. Process tracker deliverable (IN_PROGRESS)
    missing_tasks = []
    process_tracker = next((d for d in deliverables if "process-tracker" in d.get("slug", "")), None)
    if process_tracker and process_tracker.get("status") == "IN_PROGRESS":
        has_tracker_task = any("tracker" in t["name"].lower() for t in ikigai_tasks)
        if not has_tracker_task:
            missing_tasks.append({
                "type": "deliverable",
                "slug": process_tracker.get("slug"),
                "title": process_tracker.get("title", "D4 - Process tracker rollout"),
                "ueid": process_tracker.get("ueid"),
                "priority": 7,
                "tags": ["ikigai", "deliverable", "tracker", "q3-kr1"],
                "note": f"ueid: {process_tracker.get('ueid')}",
            })
    
    # 2. B1 Blocker task
    blocker_files = list((VAULT_ROOT / "ikigai_state").glob("b1-blocker-resolution.md"))
    if blocker_files:
        blocker_data = read_vault_entity(blocker_files[0])
        if blocker_data:
            has_b1_task = any(
                (("b1" in t["name"].lower() or "blocker" in t["name"].lower() or "h3" in t["name"].lower())
                 or "blocker" in [tag.lower() for tag in t.get("tags", [])])
                and "critical" in [tag.lower() for tag in t.get("tags", [])]
                for t in ikigai_tasks
            )
            if not has_b1_task:
                missing_tasks.append({
                    "type": "blocker",
                    "title": blocker_data.get("title", "B1 Blocker Resolution"),
                    "ueid": blocker_data.get("ueid"),
                    "priority": 10,
                    "tags": ["ikigai", "blocker", "critical", "q3-kr1"],
                    "note": f"ueid: {blocker_data.get('ueid')}",
                })
    
    # 3. Check KR2 - Demo task (from objective key_results)
    objective = next((o for o in objectives if "q3-2026" in o.get("slug", "")), None)
    if objective:
        key_results = objective.get("key_results", [])
        has_demo_task = any("demo" in t["name"].lower() and "portfolio" in t["name"].lower() 
                           for t in ikigai_tasks)
        if not has_demo_task:
            missing_tasks.append({
                "type": "kr",
                "title": "[KR2] Gravar demo de 12min para portfolio",
                "priority": 8,
                "tags": ["ikigai", "kr2", "portfolio", "demo"],
                "note": "KR2 from Q3-2026 objective",
            })
    
    return {
        "vault": {
            "objectives": objectives,
            "projects": projects,
            "deliverables": deliverables,
            "actionable_deliverables": actionable_deliverables,
            "active_projects": active_projects,
        },
        "taskdog": {
            "all_tasks": tasks,
            "ikigai_tasks": ikigai_tasks,
            "orphan_tasks": orphan_tasks,
        },
        "missing_tasks": missing_tasks,
    }


# ─── Sync ────────────────────────────────────────────────────────────────────


def sync_vault_to_taskdog(dry_run: bool = False) -> dict[str, Any]:
    """Sync vault entities to taskdog."""
    analysis = analyze_vault_taskdog_gaps()
    
    results = {
        "created": [],
        "deleted": [],
        "completed": [],
        "errors": [],
    }
    
    # Delete orphan test tasks
    for orphan in analysis["taskdog"]["orphan_tasks"]:
        if dry_run:
            print(f"🔴 [DRY-RUN] Would delete orphan task #{orphan['id']}: {orphan['name']}")
        else:
            if delete_taskdog_task(orphan["id"]):
                results["deleted"].append(orphan)
                print(f"✅ Deleted orphan task #{orphan['id']}: {orphan['name']}")
            else:
                results["errors"].append(f"Failed to delete task #{orphan['id']}")
    
    # Create missing tasks
    for missing in analysis["missing_tasks"]:
        if dry_run:
            print(f"🟢 [DRY-RUN] Would create: {missing['title']} (p={missing['priority']}, tags={missing.get('tags', [])})")
        else:
            task = create_taskdog_task(
                name=missing["title"],
                priority=missing["priority"],
                tags=missing.get("tags", []),
                note=missing.get("note", ""),
            )
            if task:
                results["created"].append(task)
                print(f"✅ Created task: {missing['title']}")
            else:
                results["errors"].append(f"Failed to create: {missing['title']}")
    
    return results


# ─── Main ────────────────────────────────────────────────────────────────────


def print_status():
    """Print vault ↔ taskdog status."""
    analysis = analyze_vault_taskdog_gaps()
    
    print("""
======================================================================
🔍 VAULT ↔ TASKDOG STATUS
======================================================================
""")
    
    print("📦 VAULT ENTITIES:")
    print(f"   Objectives: {len(analysis['vault']['objectives'])}")
    for obj in analysis["vault"]["objectives"]:
        status = obj.get("status", "?")
        title = obj.get("title", obj.get("slug", "?"))
        print(f"      [{status}] {title}")
    
    print(f"\n   Projects: {len(analysis['vault']['projects'])}")
    for proj in analysis["vault"]["projects"]:
        status = proj.get("status", "?")
        title = proj.get("title", proj.get("slug", "?"))
        print(f"      [{status}] {title}")
    
    print(f"\n   Deliverables: {len(analysis['vault']['deliverables'])}")
    actionable = [d for d in analysis["vault"]["deliverables"] if d.get("status") == "IN_PROGRESS"]
    print(f"      (Actionable (IN_PROGRESS): {len(actionable)})")
    for d in actionable:
        title = d.get("title", d.get("slug", "?"))
        print(f"         • {title}")
    
    print(f"""
🐕 TASKDOG TASKS: {len(analysis['taskdog']['all_tasks'])}
      (ikigai-tagged: {len(analysis['taskdog']['ikigai_tasks'])})
""")
    for task in analysis["taskdog"]["ikigai_tasks"]:
        priority = task.get("priority", "?")
        name = task.get("name", "?")
        status = task.get("status", "?")
        print(f"      [{priority}] {status}: {name}")
    
    if analysis["missing_tasks"]:
        print(f"""
⚠️  MISSING TASKS ({len(analysis['missing_tasks'])}):
""")
        for missing in analysis["missing_tasks"]:
            print(f"      + {missing['title']} (priority={missing['priority']}, tags={missing.get('tags', [])})")
    
    if analysis["taskdog"]["orphan_tasks"]:
        print(f"""
🗑️  ORPHAN TASKS ({len(analysis['taskdog']['orphan_tasks'])}):
""")
        for orphan in analysis["taskdog"]["orphan_tasks"]:
            print(f"      - #{orphan['id']} {orphan['name']}")
    
    print("\n" + "=" * 66)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Vault ↔ Taskdog sync tool")
    parser.add_argument("--status", action="store_true", help="Show vault ↔ taskdog status")
    parser.add_argument("--sync", action="store_true", help="Sync vault to taskdog")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be synced without making changes")
    
    args = parser.parse_args()
    
    if args.status:
        print_status()
    elif args.sync or args.dry_run:
        print(f"{'[DRY-RUN] ' if args.dry_run else ''}Syncing vault → taskdog...")
        results = sync_vault_to_taskdog(dry_run=args.dry_run)
        print(f"\nSync complete:")
        print(f"  Created: {len(results['created'])}")
        print(f"  Deleted: {len(results['deleted'])}")
        print(f"  Completed: {len(results['completed'])}")
        if results['errors']:
            print(f"  Errors: {len(results['errors'])}")
            for err in results['errors']:
                print(f"    - {err}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
