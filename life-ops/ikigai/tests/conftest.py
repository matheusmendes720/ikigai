"""Test suite root — mirrors life-ops/operational/ layout."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on path for all test modules
_SRC = Path(__file__).parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
