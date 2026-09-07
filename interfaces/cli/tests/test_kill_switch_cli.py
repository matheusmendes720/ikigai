"""Tests for the W5.3 kill-switch consumer CLI (interfaces/cli/kill_switch.py).

Uses `typer.testing.CliRunner` (in-process, fast — NOT subprocess).

Path redirection: `status` does an inline `Path(__file__).resolve().parents[2]`
to compute the repo root. We monkey-patch `__file__` on each of the three
kill_switch modules so `parents[2]` lands in a per-test tmp dir. Real
`check_kill_switch` / `recover_kill_switch` are pure functions that take
paths explicitly, so no sys_ikigai-layer patching is needed.

Exit codes (design §3.5): 0=ok, 1=active/refused, 2=resume w/o --confirm,
3=empty --reason.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

# Ensure `life/` is on sys.path for `from sys_ikigai.X` and `from interfaces.cli.X`.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_ROOT = _REPO_ROOT / "src"
for p in (_REPO_ROOT, _SRC_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


# ---------------------------------------------------------------------------
# Import the kill_switch app directly (bypasses interfaces.cli.__init__ —
# which requires full PYTHONPATH setup for src.contracts + src.mesh).
# ---------------------------------------------------------------------------
from interfaces.cli.kill_switch import app as kill_switch_app  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cli_paths(monkeypatch, tmp_path):
    """Redirect kill_switch path computations to a fresh tmp dir.

    Patches `__file__` on the 2 modules that compute `repo_root` via
    `Path(__file__).resolve().parents[2]` so `parents[2]` lands at
    `tmp_path`. Creates `vault/`, `data/`, `data/review_queue/` for
    real `check_kill_switch` / `read_kill_switch_history` reads.

    V5-F (2026-09-07): the third module (`_kill_switch_actions`) was
    inlined back into `kill_switch.py` and deleted; only `kill_switch`
    + `_kill_switch_helpers` remain as separate patch targets.
    """
    fake_root = tmp_path
    vault = fake_root / "vault"
    data = fake_root / "data"
    review_queue = data / "review_queue"
    for d in (vault, data, review_queue):
        d.mkdir(parents=True, exist_ok=True)

    # Path("tmp/a/b/kill_switch.py").resolve().parents[2] = tmp
    fake_dir = fake_root / "interfaces" / "cli"
    fake_dir.mkdir(parents=True, exist_ok=True)

    import interfaces.cli.kill_switch as _ks
    import interfaces.cli._kill_switch_helpers as _helpers

    monkeypatch.setattr(_ks, "__file__", str(fake_dir / "kill_switch.py"))
    monkeypatch.setattr(_helpers, "__file__", str(fake_dir / "_kill_switch_helpers.py"))

    def run_cli(args: list[str]):
        return CliRunner().invoke(kill_switch_app, args)

    return {
        "tmp_path": fake_root,
        "vault": vault,
        "data": data,
        "review_queue": review_queue,
        "run_cli": run_cli,
    }


# ---------------------------------------------------------------------------
# status verb
# ---------------------------------------------------------------------------


def test_status_inactive(cli_paths) -> None:
    """No files active → exit 0, JSON is_active: false."""
    result = cli_paths["run_cli"](["status", "--json"])

    assert result.exit_code == 0, f"status exited {result.exit_code}: {result.output}"
    payload = json.loads(result.output)
    assert payload["is_active"] is False
    assert payload["active_reason"] == "none"
    assert payload["mechanisms"]["env_var_active"] is False
    assert payload["mechanisms"]["vault_file_active"] is False
    assert payload["mechanisms"]["data_file_active"] is False


def test_status_active_data_file(cli_paths) -> None:
    """Touch data/.kill_switch in tmpdir → exit 1, JSON is_active: true."""
    kill_file = cli_paths["data"] / ".kill_switch"
    kill_file.write_text("active\n", encoding="utf-8")

    result = cli_paths["run_cli"](["status", "--json"])

    assert result.exit_code == 1, f"status exited {result.exit_code}: {result.output}"
    payload = json.loads(result.output)
    assert payload["is_active"] is True
    assert payload["active_reason"] == "data_file"
    assert payload["mechanisms"]["data_file_active"] is True


# ---------------------------------------------------------------------------
# history verb — filters to kill_switch_* events only
# ---------------------------------------------------------------------------


def test_history_filters_kill_switch(cli_paths) -> None:
    """history returns only entries with action.startswith('kill_switch_')."""
    qdir = cli_paths["review_queue"]
    # TaskChange entry (should be FILTERED OUT)
    (qdir / "evt-not-ks.json").write_text(
        json.dumps(
            {
                "event_id": "evt-not-ks",
                "ueid": "cli:other:11111111:22222222",
                "action": "create",  # NOT kill_switch_*
                "fields": {"title": "regular task"},
                "source_fork": "cli",
                "timestamp": 1.0,
                "status": "pending",
            }
        ),
        encoding="utf-8",
    )
    # kill_switch_pause + kill_switch_resume entries (should be INCLUDED)
    for i, action in enumerate(["kill_switch_pause", "kill_switch_resume"]):
        (qdir / f"evt-ks-{i}.json").write_text(
            json.dumps(
                {
                    "event_id": f"evt-ks-{i}",
                    "ueid": f"kill:audit:{i:08d}:{i:08d}",
                    "action": action,
                    "fields": {
                        "reason": f"reason-{i}",
                        "active_reason_at_action": "none",
                    },
                    "source_fork": "interfaces/cli",
                    "timestamp": float(i + 2),
                    "status": "pending",
                }
            ),
            encoding="utf-8",
        )

    result = cli_paths["run_cli"](["history", "--json"])

    assert result.exit_code == 0, f"history exited {result.exit_code}: {result.output}"
    payload = json.loads(result.output)
    assert "events" in payload
    actions = sorted(e["action"] for e in payload["events"])
    assert actions == ["kill_switch_pause", "kill_switch_resume"]
    for evt in payload["events"]:
        assert evt["action"] != "create"


# ---------------------------------------------------------------------------
# pause verb — refuses empty reason
# ---------------------------------------------------------------------------


def test_pause_refuses_empty_reason(cli_paths) -> None:
    """`pause --reason ""` exits 3 (reason required)."""
    result = cli_paths["run_cli"](["pause", "--reason", ""])

    assert result.exit_code == 3, f"pause exited {result.exit_code}: {result.output}"
    assert not (cli_paths["data"] / ".kill_switch").exists()


# ---------------------------------------------------------------------------
# resume verb — refuses without --confirm + empty reason
# ---------------------------------------------------------------------------


def test_resume_refuses_without_confirm(cli_paths) -> None:
    """`resume --reason "x"` (no --confirm) exits 2."""
    result = cli_paths["run_cli"](["resume", "--reason", "manual override"])

    assert result.exit_code == 2, f"resume exited {result.exit_code}: {result.output}"
    assert (
        "Kill switch recovery will" in result.output
        or "confirm" in result.output.lower()
    )


def test_resume_refuses_empty_reason(cli_paths) -> None:
    """`resume --reason ""` exits 3 (empty reason checked BEFORE confirm)."""
    result = cli_paths["run_cli"](["resume", "--reason", ""])

    assert result.exit_code == 3, f"resume exited {result.exit_code}: {result.output}"


# ---------------------------------------------------------------------------
# pause verb — audit entry written
# ---------------------------------------------------------------------------


def test_audit_entry_written(cli_paths) -> None:
    """After `pause --reason "x"`, JSON appears in data/review_queue/."""
    result = cli_paths["run_cli"](["pause", "--reason", "test audit write"])

    assert result.exit_code == 0, f"pause exited {result.exit_code}: {result.output}"

    kill_file = cli_paths["data"] / ".kill_switch"
    assert kill_file.exists()
    assert kill_file.read_text(encoding="utf-8").strip() == "active"

    qdir = cli_paths["review_queue"]
    audit_files = list(qdir.glob("*.json"))
    assert len(audit_files) >= 1, (
        f"expected ≥1 audit entry in {qdir}, found {len(audit_files)}"
    )

    found_pause = False
    for f in audit_files:
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if payload.get("action") == "kill_switch_pause":
            assert payload["fields"]["reason"] == "test audit write"
            assert payload["source_fork"] == "interfaces/cli"
            found_pause = True
            break
    assert found_pause, f"no kill_switch_pause entry found in {qdir}"


# ---------------------------------------------------------------------------
# recover alias — also refuses without --confirm
# ---------------------------------------------------------------------------


def test_recover_refuses_without_confirm(cli_paths) -> None:
    """`recover --reason "x"` (no --confirm) exits 2 (alias for resume)."""
    result = cli_paths["run_cli"](["recover", "--reason", "test recovery"])

    assert result.exit_code == 2, f"recover exited {result.exit_code}: {result.output}"
