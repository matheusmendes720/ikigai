"""decompose node — UEID hierarchy traversal (Dream→Task).

Traverses the IKIGAi UEID hierarchy: Dream → Goal → Objective → Project → Task → Deliverable.
Emits proposed decomposition for any active dream.
"""

from __future__ import annotations

from typing import Any

from ..state import IKIGAiStateDict


UEID_PREFIXES = {
    "dream": "dream",
    "goal": "goal",
    "objective": "obj",
    "project": "proj",
    "task": "task",
    "deliverable": "del",
}


def decompose_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Traverse UEID hierarchy for active dream and propose decomposition.

    Reads the markdown vault (via solverforge-calendar-mcp upi_search) for
    tagged items. Returns proposed decomposition into tasks.
    """
    import subprocess
    import json

    active_dream = state.get("active_dream_ueid")
    decomposition: list[str] = []

    if not active_dream:
        return {"decomposition": [], "last_step": "decompose"}

    # Extract dream ID from UEID
    dream_id = active_dream.split(":")[-1] if ":" in active_dream else active_dream

    # Search for child items of this dream
    try:
        result = subprocess.run(
            [
                "solverforge-calendar-mcp",
                "--json",
                "upi_search",
                "--query",
                f"dream:{dream_id}",
                "--limit",
                "50",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            items = json.loads(result.stdout) if result.stdout else []
            # Group by UEID tier
            by_tier: dict[str, list[dict]] = {}
            for item in items:
                ueid = item.get("ueid", "")
                tier = _tier_from_ueid(ueid)
                by_tier.setdefault(tier, []).append(item)

            # Generate decomposition recommendations
            for tier_name in ("goal", "objective", "project", "task"):
                tier_items = by_tier.get(tier_name, [])
                if not tier_items:
                    decomposition.append(f"[{tier_name.upper()}] No {tier_name} found — draft one")
                else:
                    decomposition.append(f"[{tier_name.upper()}] {len(tier_items)} existing")

    except Exception:
        decomposition.append("[DECOMPOSE] Could not read vault — using stale hierarchy")

    return {
        "decomposition": decomposition,
        "last_step": "decompose",
    }


def _tier_from_ueid(ueid: str) -> str:
    """Extract the tier name from a UEID string."""
    if not ueid:
        return "unknown"
    prefix = ueid.split(":")[1] if ":" in ueid else ueid
    return prefix.lower()
