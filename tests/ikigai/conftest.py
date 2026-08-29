"""Test suite root for tests/ikigai/ — sets up sys.path for graph imports."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ikigai/src is on path for ikigai_maintainer graph imports
_SRC = Path(__file__).parent.parent.parent / "src" / "ikigai" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
