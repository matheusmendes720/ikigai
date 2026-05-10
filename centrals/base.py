"""Base central: common contract for all centrals."""

from __future__ import annotations

import subprocess
import sys
from abc import ABC
from pathlib import Path
from typing import Any, Optional

from life.cli.config import LifeConfig, load_config


class BaseCentral(ABC):
    """A central aggregates one pillar (task/finance/knowledge/research) and dispatches to submodules or scripts."""

    name: str = "base"
    config: LifeConfig

    def __init__(self, config: Optional[LifeConfig] = None):
        self.config = config or load_config()

    def run_cli(
        self,
        cwd: Path,
        module: str,
        args: list[str],
        json_out: bool = True,
        timeout: int = 60,
    ) -> dict[str, Any]:
        """Run a Python module as CLI; return {ok, stdout, stderr, data}."""
        cmd = [sys.executable, "-m", module] + args + (["--json"] if json_out else [])
        try:
            r = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            data = None
            if json_out and r.stdout.strip():
                try:
                    import json

                    data = json.loads(r.stdout)
                except Exception:
                    pass
            return {
                "ok": r.returncode == 0,
                "stdout": r.stdout,
                "stderr": r.stderr,
                "data": data,
            }
        except Exception as e:
            return {"ok": False, "stdout": "", "stderr": "", "error": str(e)}
