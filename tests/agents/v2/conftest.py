"""Test suite for tests/agents/v2/ — temp directory fix for Windows pytest-asyncio."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Redirect tempfile.tempdir to a project-local directory to avoid
# Windows permission errors with pytest-asyncio's temp directory.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_TMP_BASE = _REPO_ROOT / "data" / "pytest-tmp"
_TMP_BASE.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(_TMP_BASE)
os.environ["TMPDIR"] = str(_TMP_BASE)
os.environ["TEMP"] = str(_TMP_BASE)
os.environ["TMP"] = str(_TMP_BASE)
