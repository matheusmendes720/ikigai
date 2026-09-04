"""Test suite root for tests/ — sets up sys.path for src/ imports."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on path for `from src.contracts.sonho` style imports.
# Path(__file__) is tests/conftest.py → parent is tests/ → parent.parent is repo root
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Ensure project-root src/ is on path for `from contracts.task_change` style imports.
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Also add src/ikigai/src/ so `from ikigai.gateway.stdio_server_base import ...` works
# in unit tests. The E2E tests in tests/gateway/clients/ inject this into the
# subprocess env via conftest, but unit tests in tests/gateway/ run in the parent.
_IKIGAI_SRC = Path(__file__).parent.parent / "src" / "ikigai" / "src"
if str(_IKIGAI_SRC) not in sys.path:
    sys.path.insert(0, str(_IKIGAI_SRC))
