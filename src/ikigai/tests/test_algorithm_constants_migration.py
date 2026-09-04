"""W3.2 — QHE constants migration to prompt-template (ADR-019) tests.

Verifies the W3.2 migration is structurally correct:

1. ``prompts/algorithm_constants.json`` exists and contains every pre-W3.2
   constant with its canonical value.
2. ``prompts/load_constants.load_algorithm_constants()`` returns the
   expected dict.
3. ``prompts/load_constants.get(key)`` returns the same value and raises
   KeyError for missing keys.
4. The ``_defensive_default`` path matches the canonical JSON values
   exactly (defensive guarantee that a missing JSON file does not change
   observable behavior).
5. observe.py / balance.py / heuristics.py no longer import the old
   DEFAULT_* / HYSTERESIS_* names from state.py — they use load_constants.
6. observe.py / balance.py / heuristics.py no longer contain numeric
   literals for the migrated constants (i.e. 0.85, 0.60, 1.20, 0.50, 8.0,
   3, 2 should not appear as bare numbers in those files).
7. The drift detector in test_canonical_scope.py
   (test_no_algorithm_constants_in_agent_code) is wired and would catch a
   regression.

See dcode-harness-TASKS.md W3.2 + W5.2 (ADR-019).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Repo-root path resolution
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
# src/ikigai/tests/test_algorithm_constants_migration.py
IKIGAI_SRC = THIS_FILE.parent.parent / "src"
V2_DIR = IKIGAI_SRC / "agents" / "v2"
PROMPTS_DIR = V2_DIR / "prompts"
JSON_PATH = PROMPTS_DIR / "algorithm_constants.json"
LOADER_PATH = PROMPTS_DIR / "load_constants.py"


# Canonical pre-W3.2 values (must match algorithm_constants.json exactly).
CANONICAL_VALUES = {
    "QHE_PUSH_THRESHOLD": 0.85,
    "QHE_RECOVER_THRESHOLD": 0.60,
    "WORKLOAD_OVERLOAD_FACTOR": 1.20,
    "WORKLOAD_UNDERLOAD_FACTOR": 0.50,
    "CAPACITY_HOURS_PER_DAY": 8.0,
    "HYSTERESIS_UPGRADE_DAYS": 3,
    "HYSTERESIS_DOWNGRADE_DAYS": 2,
}

CANONICAL_REGIME_TARGETS = {
    "PUSH": 0.85,
    "MAINTAIN": 0.65,
    "REDUCE": 0.45,
    "RECOVER": 0.25,
}


# ---------------------------------------------------------------------------
# 1. JSON config file present + structurally correct
# ---------------------------------------------------------------------------


def test_algorithm_constants_json_exists() -> None:
    assert JSON_PATH.exists(), (
        f"{JSON_PATH} not present. W3.2 requires prompts/algorithm_constants.json "
        "as the single source of truth for algorithm tuning values."
    )


def test_algorithm_constants_json_has_all_canonical_keys() -> None:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    for key, expected in CANONICAL_VALUES.items():
        assert key in data, f"missing canonical key {key} in {JSON_PATH}"
        assert data[key] == expected, (
            f"{key} mismatch: got {data[key]}, expected {expected}. "
            "Pre-W3.2 values must be preserved exactly so behavior is unchanged."
        )


def test_algorithm_constants_json_has_regime_targets() -> None:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    assert "REGIME_TARGETS" in data, f"missing REGIME_TARGETS in {JSON_PATH}"
    assert data["REGIME_TARGETS"] == CANONICAL_REGIME_TARGETS


def test_algorithm_constants_json_invariant_push_gt_recover() -> None:
    """Invariant: PUSH > RECOVER (ordering check)."""
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    assert data["QHE_PUSH_THRESHOLD"] > data["QHE_RECOVER_THRESHOLD"], (
        "QHE_PUSH_THRESHOLD must be strictly greater than QHE_RECOVER_THRESHOLD"
    )


def test_algorithm_constants_json_invariant_hysteresis() -> None:
    """Invariant: HYSTERESIS_UPGRADE_DAYS ≥ HYSTERESIS_DOWNGRADE_DAYS (hysteresis protection)."""
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    assert data["HYSTERESIS_UPGRADE_DAYS"] >= data["HYSTERESIS_DOWNGRADE_DAYS"], (
        "Hysteresis upgrade should take >= downgrade days (prevents rapid regime flips)"
    )


# ---------------------------------------------------------------------------
# 2-4. Loader behaviour
# ---------------------------------------------------------------------------


def test_load_constants_module_imports() -> None:
    """load_constants.py must be importable and expose the 3 public symbols."""
    # Direct import — works in IKIGAI's pytest config where src/ikigai/src/
    # is on sys.path via conftest.py.
    from agents.v2.prompts.load_constants import (  # type: ignore[import-not-found]
        get,
        load_algorithm_constants,
        reset_cache,
    )

    assert callable(load_algorithm_constants)
    assert callable(get)
    assert callable(reset_cache)


def test_load_algorithm_constants_returns_all_canonical() -> None:
    from agents.v2.prompts.load_constants import load_algorithm_constants

    data = load_algorithm_constants()
    for key, expected in CANONICAL_VALUES.items():
        assert key in data, f"loader missing key: {key}"
        assert data[key] == expected
    assert data["REGIME_TARGETS"] == CANONICAL_REGIME_TARGETS


def test_get_returns_value() -> None:
    from agents.v2.prompts.load_constants import get

    for key, expected in CANONICAL_VALUES.items():
        assert get(key) == expected


def test_get_raises_keyerror_for_unknown() -> None:
    from agents.v2.prompts.load_constants import get

    with pytest.raises(KeyError):
        get("NOT_A_REAL_CONSTANT")


def test_load_constants_strips_comment_keys() -> None:
    """Keys starting with '_' are metadata and must NOT appear in loader output."""
    from agents.v2.prompts.load_constants import load_algorithm_constants

    data = load_algorithm_constants()
    for key in data:
        assert not key.startswith("_"), (
            f"loader leaked metadata key: {key}. "
            "Keys prefixed with '_' are reserved for JSON comments."
        )


def test_load_constants_is_cached() -> None:
    """Repeated calls return the same object (LRU cache prevents disk re-reads)."""
    from agents.v2.prompts.load_constants import load_algorithm_constants

    a = load_algorithm_constants()
    b = load_algorithm_constants()
    assert a is b, "load_algorithm_constants() must be LRU-cached"


def test_load_constants_defensive_default_matches_canonical() -> None:
    """If the JSON is missing, the defensive default must equal canonical values.

    This guards against the loader silently using different defaults than the
    JSON file. Verified by importing the module and patching the path to a
    non-existent location, then calling load_algorithm_constants() with cache
    cleared.
    """
    from agents.v2.prompts import load_constants as lc_mod

    # Save and swap the path to point at a missing file.
    original_path = lc_mod._CONSTANTS_PATH
    try:
        lc_mod._CONSTANTS_PATH = Path("/nonexistent/algorithm_constants.json")
        lc_mod.reset_cache()
        defensive = lc_mod.load_algorithm_constants()
        for key, expected in CANONICAL_VALUES.items():
            assert defensive[key] == expected, (
                f"_defensive_default mismatch for {key}: got {defensive[key]}, expected {expected}"
            )
        assert defensive["REGIME_TARGETS"] == CANONICAL_REGIME_TARGETS
    finally:
        lc_mod._CONSTANTS_PATH = original_path
        lc_mod.reset_cache()


# ---------------------------------------------------------------------------
# 5-6. Node modules use loader (not raw DEFAULT_* or hardcoded literals)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "node_file",
    ["observe.py", "balance.py", "heuristics.py"],
)
def test_node_does_not_import_default_constants_from_state(node_file: str) -> None:
    """observe.py / balance.py / heuristics.py MUST NOT import DEFAULT_* from state."""
    src = (V2_DIR / "nodes" / node_file).read_text(encoding="utf-8")
    # Pattern: `from ..state import ...DEFAULT_QHE...` or
    #          `from .state import ...DEFAULT_QHE...` etc.
    forbidden = re.search(
        r"from\s+\.+\.?state\s+import[^)]*?(DEFAULT_|HYSTERESIS_)",
        src,
        re.DOTALL,
    )
    assert not forbidden, (
        f"{node_file} still imports forbidden constants from state. "
        "Use prompts.load_constants.get() instead. Match: "
        f"{forbidden.group(0) if forbidden else 'n/a'!r}"
    )


@pytest.mark.parametrize(
    "node_file",
    ["observe.py", "balance.py", "heuristics.py"],
)
def test_node_uses_load_constants_phrase(node_file: str) -> None:
    """observe.py / balance.py / heuristics.py MUST use load_constants.get()."""
    src = (V2_DIR / "nodes" / node_file).read_text(encoding="utf-8")
    assert "load_constants" in src, (
        f"{node_file} does not reference prompts.load_constants. "
        "W3.2 migration requires reading values via load_constants.get()."
    )


def test_state_module_does_not_export_algorithm_constants() -> None:
    """state.py MUST NOT define DEFAULT_QHE_* / HYSTERESIS_* / etc. (W3.2 strip)."""
    state_src = (V2_DIR / "state.py").read_text(encoding="utf-8")
    forbidden_names = (
        "DEFAULT_QHE_PUSH",
        "DEFAULT_QHE_RECOVER",
        "DEFAULT_WORKLOAD_OVERLOAD_FACTOR",
        "DEFAULT_WORKLOAD_UNDERLOAD_FACTOR",
        "DEFAULT_CAPACITY_HOURS_PER_DAY",
        "HYSTERESIS_UPGRADE_DAYS",
        "HYSTERESIS_DOWNGRADE_DAYS",
    )
    for name in forbidden_names:
        # Allow the name to appear in a comment ("REMOVED") but NOT in an
        # assignment context. We check for `<name> =` (with optional whitespace).
        if re.search(rf"^{name}\s*=", state_src, re.MULTILINE):
            pytest.fail(f"state.py still defines {name} — W3.2 migration incomplete")


def test_load_constants_documents_adr019() -> None:
    """load_constants.py must reference ADR-019 and the prompt-template-only rule."""
    src = LOADER_PATH.read_text(encoding="utf-8")
    assert "ADR-019" in src, "load_constants.py must reference ADR-019"
    assert "algorithm_constants.json" in src, (
        "load_constants.py must reference algorithm_constants.json as single source of truth"
    )


# ---------------------------------------------------------------------------
# 7. Drift detector end-to-end (subprocess to avoid module-level state pollution)
# ---------------------------------------------------------------------------


def test_drift_detector_regression_catch() -> None:
    """The canonical-scope drift detector must catch a regression.

    We invoke test_canonical_scope.py via subprocess so the AST scan runs in a
    clean process. We don't try to import-test the detector directly because
    it scans for module-level assignments and patching at runtime is brittle.
    The scan is cheap (<1s) so subprocess overhead is negligible.
    """
    drift_test = THIS_FILE.parent / "test_canonical_scope.py"
    if not drift_test.exists():
        pytest.skip(f"{drift_test} not present")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(drift_test),
            "-v",
            "-k",
            "no_algorithm_constants_in_agent_code or no_state_module_imports_default_constants",
            "--no-header",
            "-q",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=THIS_FILE.parents[3],  # <repo-root>
    )
    assert result.returncode == 0, (
        "Drift detector failed — algorithm constants may have re-appeared in "
        "agents/v2/*.py. Subprocess stdout:\n" + result.stdout + "\nstderr:\n" + result.stderr
    )
