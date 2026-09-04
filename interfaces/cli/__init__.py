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

from __future__ import annotations

# Path fixup MUST happen before the sibling-module imports below — pytest
# loads this `__init__.py` while resolving the test module's package chain,
# which happens BEFORE conftest.py executes, so conftest's sys.path fixups
# are too late for `from src.contracts...` inside `read_tasks.py`.
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]  # interfaces/cli/__init__.py → life/
_SRC = _REPO_ROOT / "src"
for _p in (_SRC, _REPO_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from .read_tasks import app  # noqa: E402
from .server import server_app  # noqa: E402
from .v2 import v2_app  # noqa: E402

app.add_typer(server_app, name="server")
app.add_typer(v2_app, name="v2")

__all__ = ["app"]
