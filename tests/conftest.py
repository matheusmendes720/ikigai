"""Test suite root for tests/ — sets up sys.path for src/ imports."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project-root src/ is on path for solverforge_calendar, contracts, etc.
# Path(__file__) is tests/conftest.py → parent is tests/ → parent.parent is repo root
_SRC = Path(__file__).parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
