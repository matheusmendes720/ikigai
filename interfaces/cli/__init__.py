"""Interface CLI — consumer/producer for IKIGAI mesh v1.

Run via Typer: `python -m interfaces.cli <command>` (see __main__.py).

Top-level commands (defined in interfaces.cli.read_tasks):
  list                Read tasks from data/tasks.jsonl
  done <task_id>      Mark a task done → appends data/feedback.jsonl
  stats               Aggregate counts by horizon / priority
  mesh-show <ueid>    Cross-fork view (CLI + taskdog + solverforge-calendar)
  task-add            Producer: writes CliAdapter slice + enqueues TaskChange

Sub-app `server` (defined in interfaces.cli.server):
  life server ls              List all fork adapters
  life server inspect <name>  Detailed view of one adapter
  life server status          Backend process status
  life server start/stop <name>  STUB — wires up in B4-B5

Invariants:
  - Read-only on vault/ (interfaces never write vault)
  - All writes go to data/ (mesh queue + jsonl append-only)
  - AI-native by design: zero LLM in the path
"""

from interfaces.cli.read_tasks import app
from interfaces.cli.server import server_app

app.add_typer(server_app, name="server")

__all__ = ["app"]