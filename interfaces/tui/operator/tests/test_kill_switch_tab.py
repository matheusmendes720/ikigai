"""Tests for the W5.3 operator TUI kill-switch tab + banner.

Uses Textual's `app.run_test()` async helper (NOT a real TTY). The
OperatorApp is the 4-tab dashboard (Tasks / Adapters / Backend / Queue);
W5.3 adds the 5th tab (`KillSwitch`) and a persistent banner shown on
every tab when the kill switch is active.

Path strategy:
  Monkey-patch the module-level constants `REPO_ROOT`, `VAULT_ROOT`,
  `DATA_ROOT`, `REVIEW_QUEUE_DIR` in `interfaces.tui.operator._kill_switch_tab`
  so the real `check_kill_switch` reads from `tmp_path`. The real
  `check_kill_switch` is pure and takes paths explicitly — no need to
  mock at the sys_ikigai layer.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure `life/` is on sys.path for `from sys_ikigai.X` and `from interfaces.X`.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_SRC_ROOT = _REPO_ROOT / "src"
for p in (_REPO_ROOT, _SRC_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from interfaces.tui.operator.app import OperatorApp  # noqa: E402
import interfaces.tui.operator._kill_switch_tab as _ks_tab  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tui_paths(monkeypatch, tmp_path):
    """Redirect the kill-switch TUI's REPO_ROOT / VAULT_ROOT / DATA_ROOT to tmp_path.

    Also creates `vault/`, `data/`, and `data/review_queue/` so the real
    `check_kill_switch` and `snapshot()` can read from those paths.
    """
    vault = tmp_path / "vault"
    data = tmp_path / "data"
    review_queue = data / "review_queue"
    vault.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    review_queue.mkdir(parents=True, exist_ok=True)

    # Module-level constants in _kill_switch_tab.py
    monkeypatch.setattr(_ks_tab, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(_ks_tab, "VAULT_ROOT", vault)
    monkeypatch.setattr(_ks_tab, "DATA_ROOT", data)
    monkeypatch.setattr(_ks_tab, "REVIEW_QUEUE_DIR", review_queue)

    return {
        "tmp_path": tmp_path,
        "vault": vault,
        "data": data,
        "review_queue": review_queue,
    }


# ---------------------------------------------------------------------------
# Tab registration — OperatorApp.BINDINGS must include "5" → show_kill_switch
# ---------------------------------------------------------------------------


def test_5th_tab_registered() -> None:
    """OperatorApp.BINDINGS includes binding for `5` → show_kill_switch."""
    binding_keys = []
    binding_actions = []
    for b in OperatorApp.BINDINGS:
        binding_keys.append(b.key)
        binding_actions.append(b.action)

    assert "5" in binding_keys, f"binding for '5' missing; got {binding_keys}"
    assert "show_kill_switch" in binding_actions, (
        f"show_kill_switch action missing; got {binding_actions}"
    )


# ---------------------------------------------------------------------------
# Banner — shown only when data/.kill_switch exists
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_banner_absent_when_inactive(tui_paths) -> None:
    """banner_widget() returns None when data/.kill_switch does NOT exist.

    No .kill_switch file created → no banner → banner_widget() returns None.
    """
    # Make sure no kill-switch file exists
    assert not (tui_paths["data"] / ".kill_switch").exists()

    banner = _ks_tab.banner_widget()
    assert banner is None, (
        f"banner_widget() should return None when no .kill_switch exists; "
        f"got {banner!r}"
    )


@pytest.mark.asyncio
async def test_banner_present_when_active(tui_paths) -> None:
    """banner_widget() returns a Static widget when data/.kill_switch exists.

    Creates `tmp_path/data/.kill_switch` with content 'active\n', then
    verifies banner_widget() returns a non-None Static.
    """
    kill_file = tui_paths["data"] / ".kill_switch"
    kill_file.write_text("active\n", encoding="utf-8")
    assert kill_file.exists()

    banner = _ks_tab.banner_widget()
    assert banner is not None, (
        "banner_widget() should return Static when data/.kill_switch exists; got None"
    )
    # The widget should carry the killswitch-banner id (set by banner_widget)
    assert banner.id == "killswitch-banner"
    # And its render() output should mention KILL SWITCH ACTIVE
    rendered_content = banner.render()
    if hasattr(rendered_content, "plain"):
        rendered_text = rendered_content.plain
    else:
        # Some renderables are plain strings
        rendered_text = str(rendered_content)
    assert "KILL SWITCH ACTIVE" in rendered_text, (
        f"banner render missing 'KILL SWITCH ACTIVE'; got:\n{rendered_text}"
    )


# ---------------------------------------------------------------------------
# Snapshot — is_active reflects the file state
# ---------------------------------------------------------------------------


def test_snapshot_is_active_when_file_present(tui_paths) -> None:
    """snapshot()['is_active'] is True when data/.kill_switch exists."""
    (tui_paths["data"] / ".kill_switch").write_text("active\n", encoding="utf-8")

    snap = _ks_tab.snapshot()
    assert snap["is_active"] is True
    assert snap["active_reason"] == "data_file"
    assert snap["mechanisms"]["data_file_active"] is True


def test_snapshot_inactive_when_no_files(tui_paths) -> None:
    """snapshot()['is_active'] is False when no kill-switch file exists."""
    assert not (tui_paths["data"] / ".kill_switch").exists()

    snap = _ks_tab.snapshot()
    assert snap["is_active"] is False
    assert snap["active_reason"] == "none"
    assert snap["mechanisms"]["data_file_active"] is False
    assert snap["mechanisms"]["env_var_active"] is False
    assert snap["mechanisms"]["vault_file_active"] is False
