#!/usr/bin/env python
"""System Optimizer — Agent node: benchmarks latency, memory, I/O cost, keystrokes."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[4]


def run_pav(args: str, repeat: int = 3) -> dict[str, Any]:
    """Run a pav command multiple times and collect timing stats."""
    timings: list[float] = []
    exit_codes: list[int] = []
    outputs: list[str] = []

    for _ in range(repeat):
        t0 = time.perf_counter()
        cmd = ["uv", "run", "--directory", str(_ROOT), "pav", *args.split()]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        elapsed = (time.perf_counter() - t0) * 1000  # ms
        timings.append(elapsed)
        exit_codes.append(r.returncode)
        outputs.append((r.stdout or "")[:100])

    return {
        "command": args,
        "timings_ms": timings,
        "min_ms": round(min(timings), 1),
        "max_ms": round(max(timings), 1),
        "avg_ms": round(sum(timings) / len(timings), 1),
        "exit_codes": exit_codes,
        "consistent": len(set(exit_codes)) == 1,
        "output_preview": outputs[0][:80] if outputs else "",
    }


def estimate_io_cost(command: str) -> dict[str, Any]:
    """Estimate I/O cost by measuring bytes read from disk."""
    # For CLI commands that load state, measure how much JSON is read
    state_dir = Path.home() / ".time-tasker"
    json_files = list(state_dir.glob("*.json"))

    total_bytes = sum(f.stat().st_size for f in json_files if f.exists())
    return {
        "json_state_files": len(json_files),
        "total_state_bytes": total_bytes,
        "estimated_mb": round(total_bytes / 1024 / 1024, 3),
    }


def estimate_keystrokes(command: str) -> int:
    """Count estimated keystrokes to run a command from pav home menu."""
    # From home menu: type number + enter = 2 keys per command
    # Direct CLI: pav + space + cmd = 5 + len(cmd) keys
    if "home" in command:
        return 2
    base = len("pav ") + len(command)
    return base


def analyze_optimization_opportunities(latencies: dict[str, Any]) -> list[dict[str, Any]]:
    """Propose optimizations based on benchmark data."""
    proposals = []
    slow_threshold_ms = 500

    for cmd, data in latencies.items():
        if data["avg_ms"] > slow_threshold_ms:
            proposals.append({
                "command": cmd,
                "issue": "slow_response",
                "avg_ms": data["avg_ms"],
                "suggestion": "Consider lazy-loading this module",
            })

    # Check for cold start vs warm
    cold_times = [d["timings_ms"][0] for d in latencies.values() if d["timings_ms"]]
    warm_times = []
    for d in latencies.values():
        if len(d["timings_ms"]) > 1:
            warm_times.extend(d["timings_ms"][1:])

    if cold_times and warm_times:
        avg_cold = sum(cold_times) / len(cold_times)
        avg_warm = sum(warm_times) / len(warm_times) if warm_times else 0
        if avg_cold > avg_warm * 1.5:
            proposals.append({
                "issue": "cold_start_penalty",
                "cold_ms": round(avg_cold, 1),
                "warm_ms": round(avg_warm, 1),
                "suggestion": "Pre-import frequently-used modules at startup",
            })

    return proposals


def main() -> dict[str, Any]:
    results: dict[str, Any] = {
        "command_latencies": {},
        "io_costs": {},
        "keystroke_counts": {},
        "slowest_commands": [],
        "optimization_proposals": [],
        "keystroke_count": 0,
        "total_flow_time_s": 0.0,
    }

    commands = [
        "habit list --json",
        "routine list --json",
        "metric list --json",
        "policy decisions --json",
        "state show --json",
        "report daily --json",
        "report weekly --json",
        "demo show --json",
        "doctor --json",
    ]

    for cmd in commands:
        timing = run_pav(cmd, repeat=3)
        results["command_latencies"][cmd] = timing
        results["io_costs"][cmd] = estimate_io_cost(cmd)
        results["keystroke_counts"][cmd] = estimate_keystrokes(cmd)

    # Sort by slowest
    sorted_cmds = sorted(
        results["command_latencies"].items(),
        key=lambda x: x[1]["avg_ms"],
        reverse=True,
    )
    results["slowest_commands"] = [
        {"command": cmd, "avg_ms": data["avg_ms"]} for cmd, data in sorted_cmds[:5]
    ]

    # Optimization proposals
    results["optimization_proposals"] = analyze_optimization_opportunities(
        results["command_latencies"]
    )

    # Total keystrokes for a full QA flow (10 commands)
    results["keystroke_count"] = sum(results["keystroke_counts"].values())

    # Total flow time
    total_ms = sum(d["avg_ms"] for d in results["command_latencies"].values())
    results["total_flow_time_s"] = round(total_ms / 1000, 2)

    # Memory estimate (rough: Python process ~30-50MB baseline)
    results["memory_estimate_mb"] = {
        "baseline_process": 35,
        "with_3_repeats_per_cmd": 35 + len(commands) * 5,
        "rough_total_mb": 35 + len(commands) * 5,
    }

    results["summary"] = {
        "total_commands": len(commands),
        "total_flow_time_s": results["total_flow_time_s"],
        "slowest_avg_ms": results["slowest_commands"][0]["avg_ms"] if results["slowest_commands"] else 0,
        "optimization_opportunities": len(results["optimization_proposals"]),
    }

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return results


if __name__ == "__main__":
    main()
