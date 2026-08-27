"""Final verification script for T4 — period-sync CLI commands.

Run from repo root: python .omo/period-4-verify.py
"""
from __future__ import annotations

import json
import os
import sys

from typer.testing import CliRunner

from operational.cli.app import app

runner = CliRunner()

print("=" * 50)
print("PERIOD-REPORTS-SYNC T4 — CLI Commands Verification")
print("=" * 50)
print()

# 1) sync sub-typer is registered
print("[1] sync sub-typer registration:")
result = runner.invoke(app, ["sync", "--help"])
assert result.exit_code == 0, result.output
assert "vault" in result.output and "list" in result.output and "hierarchy" in result.output
print("    PASS - vault, list, hierarchy commands visible")
print()

# 2) state migrate is registered
print("[2] state migrate registration:")
result = runner.invoke(app, ["state", "migrate", "--help"])
assert result.exit_code == 0, result.output
assert "--db" in result.output and "--json" in result.output
print("    PASS - --db and --json options visible")
print()

# 3) sync vault full pipeline
print("[3] sync vault pipeline:")
if os.path.exists("test_final.db"):
    os.remove("test_final.db")
result = runner.invoke(
    app,
    [
        "sync",
        "vault",
        "--vault",
        "test_period_vault",
        "--db",
        "test_final.db",
        "--json",
    ],
)
assert result.exit_code == 0, result.output
data = json.loads(result.stdout)
assert data["ingested"] == 1
assert data["errors"] == 0
print(f"    PASS - ingested={data['ingested']} errors={data['errors']}")
print()

# 4) sync list
print("[4] sync list:")
result = runner.invoke(app, ["sync", "list", "--db", "test_final.db", "--json"])
assert result.exit_code == 0, result.output
data = json.loads(result.stdout)
assert len(data) == 1 and data[0]["id"] == "test-sonho"
print(f"    PASS - count={len(data)} first_id={data[0]['id']}")
print()

# 5) sync hierarchy
print("[5] sync hierarchy:")
result = runner.invoke(
    app,
    [
        "sync",
        "hierarchy",
        "--vault",
        "test_period_vault",
        "--db",
        "test_final.db",
        "--sonho",
        "test-sonho",
        "--json",
    ],
)
assert result.exit_code == 0, result.output
data = json.loads(result.stdout)
assert data["sonho_id"] == "test-sonho"
assert data["count"] == 1
print(f"    PASS - sonho_id={data['sonho_id']} count={data['count']}")
print()

# 6) state migrate cold
print("[6] state migrate (cold):")
if os.path.exists("test_final_state.db"):
    os.remove("test_final_state.db")
result = runner.invoke(app, ["state", "migrate", "--db", "test_final_state.db", "--json"])
assert result.exit_code == 0, result.output
data = json.loads(result.stdout)
assert data["count"] == 1 and data["applied"][0] == "001_initial"
print(f"    PASS - applied={data['applied']}")
print()

# 7) state migrate idempotency
print("[7] state migrate idempotency:")
result = runner.invoke(app, ["state", "migrate", "--db", "test_final_state.db", "--json"])
assert result.exit_code == 0, result.output
data = json.loads(result.stdout)
assert data["count"] == 0
print(f"    PASS - second run applied={data['applied']}")
print()

# 8) sync vault idempotency
print("[8] sync vault idempotency:")
result = runner.invoke(
    app,
    [
        "sync",
        "vault",
        "--vault",
        "test_period_vault",
        "--db",
        "test_final.db",
        "--json",
    ],
)
assert result.exit_code == 0, result.output
data = json.loads(result.stdout)
assert data["skipped"] == 1 and data["ingested"] == 0
print(f"    PASS - second run skipped={data['skipped']} ingested={data['ingested']}")
print()

# 9) --period filter on list
print("[9] sync list --period filter:")
result = runner.invoke(
    app,
    [
        "sync",
        "list",
        "--db",
        "test_final.db",
        "--period",
        "sonho",
        "--json",
    ],
)
assert result.exit_code == 0, result.output
data = json.loads(result.stdout)
assert len(data) == 1
print(f"    PASS - filtered count={len(data)}")
print()

# 10) non-JSON output works
print("[10] non-JSON output:")
result = runner.invoke(app, ["sync", "list", "--db", "test_final.db"])
assert result.exit_code == 0, result.output
assert "test-sonho" in result.stdout
print("    PASS - text output contains id")
print()

print("=" * 50)
print("ALL 10 SCENARIOS PASS")
print("=" * 50)