"""Test suite root for tests/solverforge_calendar/ — sets up sys.path for solverforge_calendar imports."""

from __future__ import annotations

import sys
from pathlib import Path

# Project-root src/ — has solverforge_calendar package
_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
