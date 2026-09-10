"""ikigai-taskdog CLI — direct SQLite, no upstream server required.

UX 2026-09-10: User removed all upstream `taskdog` aliases because the
upstream binary requires an HTTP server on :8000 to be running. This
module replaces the upstream client with a direct SQLite read/write
using our existing `TaskdogAdapter`.

Subcommands (matching upstream conventions where possible):
  list              list all non-archived tasks
  add <name>        create a new task
  show <ueid>       show task details
  --json            output as JSON (for scripting)

This is the ONLY taskdog CLI the project needs. Upstream `taskdog`
binary is no longer required for daily work.
"""

from __future__ import annotations

import argparse
import json as _json
import sys
from pathlib import Path

# Bootstrap sys.path so we can import src.mesh.adapters.taskdog
# regardless of cwd (entry point shells don't have worktree root on
# path by default).
_SCRIPT_DIR = Path(__file__).resolve()
_WORKTREE_SRC = _SCRIPT_DIR.parents[2]  # src/mesh → src → worktree
if str(_WORKTREE_SRC.parent) not in sys.path:
    sys.path.insert(0, str(_WORKTREE_SRC.parent))
if str(_WORKTREE_SRC) not in sys.path:
    sys.path.insert(0, str(_WORKTREE_SRC))


def cmd_list(args: argparse.Namespace) -> int:
    """List all non-archived tasks via TaskdogAdapter."""
    from src.mesh.adapters.taskdog import TaskdogAdapter, TASKDOG_DB

    if not TASKDOG_DB.exists():
        print(f"taskdog DB not found at {TASKDOG_DB}")
        return 1

    adapter = TaskdogAdapter()
    tasks = adapter.list_all()
    tasks = [t for t in tasks if t.get("status") != "archived"]

    if args.json:
        print(_json.dumps(tasks, indent=2, default=str))
        return 0

    if not tasks:
        print("No tasks.")
        return 0

    print(f"{len(tasks)} task(s):")
    for t in tasks:
        print(f"  [{t['ueid']}] {t['name']}  status={t['status']}  priority={t['priority']}  due={t['deadline']}")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    """Add a new task via TaskdogAdapter.apply_change."""
    import uuid
    from datetime import datetime, UTC
    from src.contracts.common import UEID
    from src.contracts.task_change import TaskAction, PropagationEvent, TaskChange
    from src.mesh.adapters.taskdog import TaskdogAdapter

    if not args.name:
        print("error: task name required", file=sys.stderr)
        return 1

    # Build UEID + PropagationEvent
    slug = args.name.lower().replace(" ", "-")[:50]
    short_id = uuid.uuid4().hex[:16]
    ueid_str = f"tsk:{slug}:{short_id[:8]}:{short_id[8:]}"

    try:
        parsed_ueid = UEID(ueid_str)
    except ValueError as e:
        print(f"error: invalid UEID {ueid_str}: {e}", file=sys.stderr)
        return 1

    event = TaskChange(
        event_id=f"cli-{short_id}",
        ueid=parsed_ueid,
        action=TaskAction.CREATE,
        fields={"title": args.name, "priority": args.priority, "due": args.due or ""},
        source_fork="ikigai-taskdog-cli",
        timestamp=datetime.now(UTC).replace(tzinfo=None),
    )

    adapter = TaskdogAdapter()
    try:
        adapter.apply_change(event)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(_json.dumps({"event_id": event.event_id, "ueid": str(parsed_ueid), "status": "planned"}))
    else:
        print(f"Created: [{parsed_ueid}] {args.name}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Show task details by UEID."""
    from src.contracts.common import UEID
    from src.mesh.adapters.taskdog import TaskdogAdapter

    if not args.ueid:
        print("error: ueid required", file=sys.stderr)
        return 1

    try:
        parsed = UEID(args.ueid)
    except ValueError as e:
        print(f"error: invalid UEID: {e}", file=sys.stderr)
        return 1

    adapter = TaskdogAdapter()
    task = adapter.read(parsed)
    if task is None:
        print(f"Task not found: {args.ueid}")
        return 1

    if args.json:
        print(_json.dumps(task, indent=2, default=str))
    else:
        for k, v in task.items():
            print(f"  {k}: {v}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ikigai-taskdog",
        description="IKIGAI taskdog CLI — direct SQLite, no upstream server required.",
    )
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # list
    p_list = subparsers.add_parser("list", help="List all non-archived tasks")
    p_list.add_argument("--json", action="store_true", help="Output as JSON")
    p_list.set_defaults(func=cmd_list)

    # add
    p_add = subparsers.add_parser("add", help="Create a new task")
    p_add.add_argument("name", help="Task name/title")
    p_add.add_argument("--priority", default="medium", choices=["high", "medium", "low"])
    p_add.add_argument("--due", default=None, help="Due date YYYY-MM-DD")
    p_add.add_argument("--json", action="store_true", help="Output as JSON")
    p_add.set_defaults(func=cmd_add)

    # show
    p_show = subparsers.add_parser("show", help="Show task details")
    p_show.add_argument("ueid", help="UEID of the task")
    p_show.add_argument("--json", action="store_true", help="Output as JSON")
    p_show.set_defaults(func=cmd_show)

    # tui — opens Textual TUI (no server)
    p_tui = subparsers.add_parser(
        "tui",
        help="Open Textual TUI for taskdog (direct SQLite, no server)",
    )
    p_tui.set_defaults(func=lambda _a: _import_cmd("cmd_tui", _a))

    args = parser.parse_args()
    return args.func(args)


def _import_cmd(name: str, args: argparse.Namespace) -> int:
    """Lazy-import a subcommand from __main__ikigai_taskdog_tui.

    Avoids importing Textual (slow) when user just runs list/add/show.
    """
    import importlib
    mod = importlib.import_module("src.mesh.__main__ikigai_taskdog_tui")
    return getattr(mod, name)(args)


if __name__ == "__main__":
    raise SystemExit(main())
