"""Test suite for tests/mcp_server/."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ikigai/src is on path
_SRC = Path(__file__).parent.parent.parent / "src" / "ikigai" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
