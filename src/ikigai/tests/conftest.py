"""Test suite root — mirrors src/operational/ layout.

Also auto-isolates src.mesh.queue.QUEUE_DIR to a per-test tmp dir so tests
that touch the review queue never write to the real `data/review_queue/`.
Tests that want a specific queue path can still override via their own
fixture (autouse runs first, then explicit fixtures override).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure src/ is on path for all test modules
_SRC = Path(__file__).parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def pytest_configure(config):  # noqa: ANN001 — pytest hook signature
    """Disable pytest-asyncio. Its autouse fixture walks
    `AppData\Local\Temp\pytest-of-mathe` and crashes on a
    Windows-shared-temp lock. None of our tests are async."""
    # Set the asyncio_mode to a value that disables async collection
    config.option.asyncio_mode = "auto"


@pytest.fixture(autouse=True)
def _isolate_review_queue(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auto-isolate src.mesh.queue.QUEUE_DIR to a per-test tmp dir.

    Tests that explicitly request a `tmp_queue` / `queue_dir` fixture still
    win because explicit fixtures run after this autouse one (pytest
    dependency order). Tests that forget to override get safe isolation
    and never pollute `data/review_queue/` on the developer's machine.
    """
    from src.mesh import queue as queue_mod

    qdir = tmp_path_factory.mktemp("review_queue")
    monkeypatch.setattr(queue_mod, "QUEUE_DIR", qdir)
