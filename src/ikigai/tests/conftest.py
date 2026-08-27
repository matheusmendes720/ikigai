"""Test suite root — mirrors src/operational/ layout."""

from __future__ import annotations

import sys
from pathlib import Path

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