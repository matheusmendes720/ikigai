"""Integration test conftest — minimal stub.

PAV CLI/TUI is a future feature (see memory: pav-cli-tui-future-feature-2026-08-27).
This stub keeps integration tests for the core PAV engine runnable without
importing operational.cli/tui/ui.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure src is on the path
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
