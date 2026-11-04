"""Test suite root — the canonical (ADR-037) suite.

2026-11-02: this file was rewritten as part of the ADR-037 cut. It used to
carry three things that are now gone from the published tree:

1. a **dual-module-identity aliasing** block that imported ``sys_ikigai.*``
   at conftest-import time and registered ``ikigai.*`` aliases in
   ``sys.modules``. It existed to defend against the dual-module-identity bug
   class (memory: ``test-review-queue-worker-dual-module-fix-2026-09-05``).
   With the pre-ADR-037 runtime unpublished, there is no second identity left
   to defend against — the aliasing block was importing the very tree the cut
   removes, and would have broken the whole suite at collection time;
2. a ``src.mesh`` isolation fixture, for the fork mesh that is retired;
3. a taskdog HTTP-bridge fixture, for an adapter that no longer ships.

What survives is load-bearing and stays: the ``sys.path`` setup and the
Windows ``tempfile.tempdir`` redirect (memory: ``windows-stdio-binary-mode-fix``
/ ``pytest-tmp`` — a stale ``AppData\\Local\\Temp`` lock raises
``PermissionError [WinError 5]``).

The legacy test modules are **not deleted** — they stay on the owner's disk
and in the git history. They are excluded from collection here, and
unpublished from the branch, because they test code that is no longer
published. If a canonical test ever needs one of them back, the module
returns with its subject.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — must happen BEFORE any test module or pytest plugin imports
# src.* (some plugins walk sys.path or import src.* during their own
# collection/setup).
# ---------------------------------------------------------------------------
# The canonical import style is the dotted prefix: `from src.contracts.X
# import Y` resolves against <repo-root>/, and `from strategics.X import Y`
# against <repo-root>/src/ikigai/src/ (the published `strategics` package).
# The package's own pytest config (`pythonpath = ["src", "../.."]`) declares
# both; the entries below make the same guarantee for a bare `pytest` run
# from the repository root.
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parent.parent.parent.parent  # <repo-root>
_SRC_ROOT = _THIS.parent.parent.parent  # <repo-root>/src/  (contracts/, services/)
_IKIGAI_SRC = _THIS.parent.parent / "src"  # <repo-root>/src/ikigai/src/  (strategics/)
for _p in (_REPO_ROOT, _SRC_ROOT, _IKIGAI_SRC):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# ---------------------------------------------------------------------------
# The retired pre-ADR-037 suite — excluded from collection, not deleted.
#
# These modules test the runtime that ADR-037 unpublished: `sys_ikigai/`
# (entities, state machines, gateway, vault write, propagation, drift
# detector), `src/mesh/` (the fork mesh), and the vault markdown pipeline.
# They remain on the owner's disk and in the git history.
# ---------------------------------------------------------------------------
LEGACY_TEST_MODULES: tuple[str, ...] = (
    "test_cli.py",
    "test_constants.py",
    "test_correction_signal.py",
    "test_dict_to_frontmatter.py",
    "test_drift_detector.py",
    "test_drift_state.py",
    "test_enums.py",
    "test_event_log.py",
    "test_event_log_cli.py",
    "test_exceptions.py",
    "test_fractal_regime.py",
    "test_frontmatter_to_dict.py",
    "test_gantt_optimizer.py",
    "test_gateway.py",
    "test_gateway_client_cli.py",
    "test_ikigai_cli.py",
    "test_ikigai_record.py",
    "test_integration_data_model.py",
    "test_kill_switch.py",
    "test_override.py",
    "test_phase_snapshot.py",
    "test_proposal_contracts.py",
    "test_propagation_sqlite_adapter.py",
    "test_recursive_reflection.py",
    "test_reverse_sync.py",
    "test_reverse_sync_state.py",
    "test_score_value.py",
    "test_sqlite_append_only.py",
    "test_sqlite_bridge.py",
    "test_state_machines.py",
    "test_state_reducer.py",
    "test_taskdog_adapter_list_all.py",
    "test_td_advanced.py",
    "test_td_tag.py",
    "test_types.py",
    "test_ueid_dual_format.py",
    "test_ueid_validator.py",
    "test_vault_lock.py",
    "test_vault_read.py",
    "test_vault_sync.py",
    "test_vault_sync_cli.py",
    "test_vault_sync_e2e.py",
    "test_vault_write.py",
    "test_vault_write_audit_log.py",
    "test_vault_write_invariant.py",
)

collect_ignore = [str(_THIS.parent / name) for name in LEGACY_TEST_MODULES]

# ---------------------------------------------------------------------------
# Redirect tempfile.tempdir to a project-local directory. On Windows,
# pytest-asyncio's autouse fixture walks the user-level temp dir
# (`C:\Users\<user>\AppData\Local\Temp\pytest-of-<user>\`) and raises
# `PermissionError [WinError 5]` when a prior run left a stale/locked
# directory. Pointing `tempfile.tempdir` (and the standard TMP env vars)
# at a project-local path sidesteps the shared-temp-lock bug entirely.
# We use `data/pytest-tmp/` (gitignored) instead of `AppData\Local\Temp\`.
# ---------------------------------------------------------------------------
_TMP_BASE = _REPO_ROOT / "data" / "pytest-tmp"
_TMP_BASE.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(_TMP_BASE)
os.environ["TMPDIR"] = str(_TMP_BASE)
os.environ["TEMP"] = str(_TMP_BASE)
os.environ["TMP"] = str(_TMP_BASE)

import pytest  # noqa: E402 — must come AFTER sys.path and env setup above


def pytest_configure(config):
    """Run the async tests, whatever the rootdir is.

    Most of this suite is `async def`: the write contract, the transport's
    error translation and the vault sync are all asynchronous. pytest-asyncio
    defaults to "strict", which SKIPS an unmarked async test rather than
    failing it — so a suite with no asyncio_mode runs a fraction of itself
    and still reports green. The two pytest configs say `asyncio_mode = auto`
    as well; this makes it hold from any rootdir, not only from those two.
    """
    config.option.asyncio_mode = "auto"
