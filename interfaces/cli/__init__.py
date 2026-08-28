"""Interface CLI — consumer/producer for IKIGAI mesh v1.

Run via Typer: `python -m interfaces.cli <command>` (see __main__.py).

Commands (defined in interfaces.cli.read_tasks):
  list                Read tasks from data/tasks.jsonl
  done <task_id>      Mark a task done → appends data/feedback.jsonl
  stats               Aggregate counts by horizon / priority
  mesh-show <ueid>    Cross-fork view (CLI + taskdog + solverforge-calendar)
  task-add            Producer: writes CliAdapter slice + enqueues TaskChange

Invariants:
  - Read-only on vault/ (interfaces never write vault)
  - All writes go to data/ (mesh queue + jsonl append-only)
  - AI-native by design: zero LLM in the path
"""

from interfaces.cli.read_tasks import app

__all__ = ["app"]
