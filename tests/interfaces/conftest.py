"""Conftest for tests/interfaces/ — adds repo root to sys.path.

The interfaces/ package sits at repo root, so it needs the repo root on
sys.path. The root conftest at tests/conftest.py adds src/, but not the
repo root itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
