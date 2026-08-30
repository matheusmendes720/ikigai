"""Test suite root for tests/mesh/ — sets up sys.path for mesh/contracts imports.

mesh + contracts live at the project-root `src/` (NOT `src/ikigai/src/`).
This conftest ensures that path is on sys.path so `from src.mesh.X` and
`from src.contracts.X` resolve correctly.

Mirrors the pattern in tests/ikigai/conftest.py and src/ikigai/tests/conftest.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Project-root src/ — has contracts/ and mesh/ packages
_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))