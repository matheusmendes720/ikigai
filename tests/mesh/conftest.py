"""Test suite root for tests/mesh/ — sets up sys.path for mesh/contracts imports.

mesh + contracts live at the project-root `src/` (NOT `src/ikigai/src/`).
This conftest ensures that path is on sys.path so `from src.mesh.X` and
`from src.contracts.X` resolve correctly.

Also auto-isolates src.mesh.queue.QUEUE_DIR to a per-test tmp dir so tests
that touch the review queue never write to the real `data/review_queue/`.
Tests that want a specific queue path can still override via their own
fixture (autouse runs first, then explicit fixtures override).

Mirrors the pattern in tests/ikigai/conftest.py and src/ikigai/tests/conftest.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Project-root src/ — has contracts/ and mesh/ packages
_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


@pytest.fixture(autouse=True)
def _isolate_review_queue(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auto-isolate src.mesh.queue.QUEUE_DIR to a per-test tmp dir.

    Tests that explicitly request a `queue_dir` / `tmp_queue` fixture still
    win because explicit fixtures run after this autouse one (pytest
    dependency order). Tests that forget to override get safe isolation
    and never pollute `data/review_queue/` on the developer's machine.
    """
    # Lazy import: src.mesh.queue pulls in contracts/task_change; importing
    # here keeps the conftest import cheap when sys.path is already set up.
    from src.mesh import queue as queue_mod

    qdir = tmp_path_factory.mktemp("review_queue")
    monkeypatch.setattr(queue_mod, "QUEUE_DIR", qdir)