"""Test runner: discover and run tests across submodules. Pytest or unittest."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, List, Optional

from life.config import load_config
from life.log import get_logger

logger = get_logger("life.test_runner")


def find_test_dirs(config: Optional[Any] = None) -> List[Path]:
    """Return list of submodule paths that have tests (tests/ or test_*.py)."""
    cfg = config or load_config()
    dirs = []
    for name, path in cfg.submodules.items():
        p = Path(path)
        if not p.exists():
            continue
        if (p / "tests").exists() or (p / "tests.py").exists():
            dirs.append(p)
        for f in p.glob("test_*.py"):
            dirs.append(p)
            break
    return list(dict.fromkeys(dirs))  # dedupe


def run_pytest(
    paths: Optional[List[Path]] = None,
    verbose: int = 0,
    timeout: int = 300,
) -> dict[str, Any]:
    """Run pytest in each submodule path. Return aggregate result."""
    cfg = load_config()
    paths = paths or find_test_dirs(cfg)
    if not paths:
        return {"ok": True, "ran": 0, "results": [], "message": "No test dirs found"}
    results = []
    all_ok = True
    for p in paths:
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pytest", str(p), "-v"] + (["-" + "v" * verbose] if verbose else []),
                cwd=cfg.root,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            ok = r.returncode == 0
            if not ok:
                all_ok = False
            results.append({"path": str(p), "ok": ok, "stdout": r.stdout, "stderr": r.stderr})
        except subprocess.TimeoutExpired:
            all_ok = False
            results.append({"path": str(p), "ok": False, "error": "timeout"})
        except Exception as e:
            all_ok = False
            results.append({"path": str(p), "ok": False, "error": str(e)})
    return {"ok": all_ok, "ran": len(results), "results": results}


def run_unittest(paths: Optional[List[Path]] = None) -> dict[str, Any]:
    """Run python -m unittest discover in each path."""
    cfg = load_config()
    paths = paths or find_test_dirs(cfg)
    if not paths:
        return {"ok": True, "ran": 0, "results": [], "message": "No test dirs found"}
    results = []
    all_ok = True
    for p in paths:
        try:
            r = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", str(p), "-v"],
                cwd=cfg.root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            ok = r.returncode == 0
            if not ok:
                all_ok = False
            results.append({"path": str(p), "ok": ok, "stdout": r.stdout, "stderr": r.stderr})
        except Exception as e:
            all_ok = False
            results.append({"path": str(p), "ok": False, "error": str(e)})
    return {"ok": all_ok, "ran": len(results), "results": results}
