"""reflect node — retrospective channel: aggregate completed work."""
from __future__ import annotations

import datetime as dt
from typing import Any

from ..state import IKIGAiStateDict


def reflect_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Retrospective channel: aggregate completed work since last cycle.

    Reads UPI history from solverforge-calendar-mcp to count completions.
    Populates `retrospective_log` with summary strings.
    """
    import subprocess
    import json

    log: list[str] = []

    try:
        result = subprocess.run(
            [
                "solverforge-calendar-mcp",
                "--json",
                "upi_list",
                "--limit",
                "100",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            items = data if isinstance(data, list) else []
            done = [i for i in items if i.get("status") == "Done"]
            blocked = [i for i in items if i.get("status") == "Blocked"]
            log.append(f"[RETRO] {len(done)} tasks completed since last cycle")
            log.append(f"[RETRO] {len(blocked)} tasks currently blocked")
            if done:
                recent = done[-3:]
                for item in recent:
                    title = item.get("title", "?")
                    log.append(f"  ✓ {title}")
    except Exception:
        log.append("[RETRO] Could not read UPI history — operating on stale state")

    # Hysteresis tracking
    days_in_regime = state.get("days_in_regime", 1) + 1

    return {
        "retrospective_log": log,
        "days_in_regime": days_in_regime,
        "last_step": "reflect",
    }
