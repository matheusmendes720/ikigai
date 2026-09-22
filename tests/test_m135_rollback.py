"""M135 tests — vault_rollback.py.

Verifies reading the audit log, listing events with filters, and rolling
back toggle/reopen events (with both dry-run and apply modes). Uses real
tmp files + mocked append_event to keep the test log isolated.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.vault import rollback as rb  # noqa: E402
from tools.backtest import vault_propagation as vp  # noqa: E402


@pytest.fixture
def audit_log(tmp_path: Path) -> Path:
    """Create a small audit log with 4 events at different timestamps."""
    log = tmp_path / ".vault_events.jsonl"
    base = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
    events = [
        {"ts": (base + timedelta(hours=1)).isoformat(),
         "event": "vault.toggle_applied", "rel_path": "plan.md", "target_line": 1,
         "expected_text": "task one", "actor": "user", "ok": True},
        {"ts": (base + timedelta(hours=2)).isoformat(),
         "event": "vault.reopen_applied", "rel_path": "plan.md", "target_line": 2,
         "expected_text": "task two", "actor": "user", "ok": True},
        {"ts": (base + timedelta(hours=3)).isoformat(),
         "event": "vault.toggle_refused", "rel_path": "plan.md", "target_line": 3,
         "expected_text": "task three", "actor": "user", "preview_error": "mismatch"},
        {"ts": (base + timedelta(hours=4)).isoformat(),
         "event": "vault.toggle_applied", "rel_path": "plan.md", "target_line": 4,
         "expected_text": "task four", "actor": "agent", "ok": True},
    ]
    log.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    return log


# === _read_events ===

def test_read_events_basic(audit_log: Path) -> None:
    """Reads all events, oldest first."""
    events = rb._read_events(audit_log)
    assert len(events) == 4
    assert events[0]["event"] == "vault.toggle_applied"
    assert events[1]["event"] == "vault.reopen_applied"


def test_read_events_missing_file(tmp_path: Path) -> None:
    """Missing log → empty list."""
    assert rb._read_events(tmp_path / "missing.jsonl") == []


def test_read_events_skips_malformed(tmp_path: Path) -> None:
    """Malformed JSON lines are skipped."""
    log = tmp_path / ".vault_events.jsonl"
    log.write_text(
        '{"event": "good"}\n'
        'NOT JSON\n'
        '{"event": "also good"}\n',
        encoding="utf-8",
    )
    events = rb._read_events(log)
    assert len(events) == 2


# === _parse_ts ===

def test_parse_ts_with_z() -> None:
    """Trailing 'Z' is normalized to '+00:00'."""
    dt = rb._parse_ts("2026-09-22T12:00:00Z")
    assert dt is not None
    assert dt.tzinfo is not None


def test_parse_ts_with_offset() -> None:
    """Standard ISO with offset parses."""
    dt = rb._parse_ts("2026-09-22T12:00:00+00:00")
    assert dt is not None


def test_parse_ts_invalid() -> None:
    """Invalid string → None."""
    assert rb._parse_ts("not a date") is None
    assert rb._parse_ts("") is None


# === list_events ===

def test_list_events_newest_first(audit_log: Path) -> None:
    """list_events returns newest first."""
    events = rb.list_events(audit_log)
    assert len(events) == 4
    assert events[0]["expected_text"] == "task four"  # newest (h+4)
    assert events[3]["expected_text"] == "task one"   # oldest (h+1)


def test_list_events_limit(audit_log: Path) -> None:
    """limit caps the number of events."""
    events = rb.list_events(audit_log, limit=2)
    assert len(events) == 2
    assert events[0]["expected_text"] == "task four"


def test_list_events_actor_filter(audit_log: Path) -> None:
    """--actor filter narrows to that actor only."""
    events = rb.list_events(audit_log, actor="agent")
    assert len(events) == 1
    assert events[0]["actor"] == "agent"


def test_list_events_event_type_filter(audit_log: Path) -> None:
    """--event filter narrows to that event type only."""
    events = rb.list_events(audit_log, event_type="vault.reopen_applied")
    assert len(events) == 1


def test_list_events_since_hours(audit_log: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--since-hours excludes old events."""
    # base=12:00, events at +1=13:00, +2=14:00, +3=15:00, +4=16:00.
    # Pretend it's 14:30 UTC now; since_hours=1 → cutoff=13:30.
    # Events >= 13:30 are: +2, +3, +4 (3 events); +1 (13:00) excluded.
    fake_now = datetime(2026, 9, 22, 14, 30, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(rb, "_now_utc", lambda: fake_now)
    events = rb.list_events(audit_log, since_hours=1)
    assert len(events) == 3
    assert all(e["expected_text"] != "task one" for e in events)
    # Newest first.
    assert events[0]["expected_text"] == "task four"


def test_list_events_since_hours_includes_all_when_zero(
    audit_log: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """since_hours=0 (or very large) includes all events."""
    events = rb.list_events(audit_log, since_hours=1000)
    assert len(events) == 4


def test_list_events_combined_filters(audit_log: Path) -> None:
    """Combine actor + event_type + limit."""
    events = rb.list_events(
        audit_log, actor="user", event_type="vault.toggle_applied", limit=1,
    )
    # Newest toggle from user is task one (h+1). task_four is from agent.
    assert len(events) == 1
    assert events[0]["expected_text"] == "task one"


def test_list_events_empty_log(tmp_path: Path) -> None:
    """Empty / missing log → empty list."""
    assert rb.list_events(tmp_path / "missing.jsonl") == []
    log = tmp_path / ".vault_events.jsonl"
    log.write_text("", encoding="utf-8")
    assert rb.list_events(log) == []


# === _rollback_one ===

def test_rollback_toggle_applied_dry_run(
    audit_log: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """dry_run=True reports what would happen without mutating."""
    event = {"event": "vault.toggle_applied", "rel_path": "plan.md",
             "target_line": 1, "expected_text": "task one", "ok": True}
    # _resolve_plan_path is imported into apply_toggle_cli from rollback.
    # Patch it directly there.
    from tools.vault import apply_toggle_cli as atc
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] task one\n", encoding="utf-8")
    monkeypatch.setattr(atc, "_resolve_plan_path", lambda rp: plan)

    result = rb._rollback_one(event, actor="rb-test", reason="undo",
                              dry_run=True)
    assert result["ok"] is True
    assert result["action"] == "reopen"
    assert result["dry_run"] is True
    # File NOT mutated.
    assert plan.read_text(encoding="utf-8") == "- [x] task one\n"


def test_rollback_reopen_applied(
    audit_log: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """reopen_applied → toggle (close the reopened checkbox)."""
    event = {"event": "vault.reopen_applied", "rel_path": "plan.md",
             "target_line": 2, "expected_text": "task two", "ok": True}
    from tools.vault import apply_toggle_cli as atc
    plan = tmp_path / "plan.md"
    # After a reopen, the checkbox is [ ]. To roll back, we toggle to [x].
    # Line 2 is "task two" (the target), line 1 is filler.
    plan.write_text("- [ ] task one\n- [ ] task two\n", encoding="utf-8")
    monkeypatch.setattr(atc, "_resolve_plan_path", lambda rp: plan)
    appended: list[dict] = []
    monkeypatch.setattr(vp, "append_event", lambda e: appended.append(e))

    result = rb._rollback_one(event, actor="rb-test", reason="undo", dry_run=False)
    assert result["ok"] is True, result
    assert result["action"] == "toggle"
    # File mutated: line 2 was [ ], now [x].
    lines = plan.read_text(encoding="utf-8").splitlines()
    assert lines[1] == "- [x] task two"
    # Audit event recorded (rollback entry appended; original toggle also
    # calls append_event, so we expect at least 2).
    rollback_events = [e for e in appended if e.get("event") == "vault.rollback_applied"]
    assert len(rollback_events) == 1
    assert rollback_events[0]["original_event"] == "vault.reopen_applied"
    assert rollback_events[0]["reverse_action"] == "toggle"


def test_rollback_refused_event_noop(
    audit_log: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """toggle_refused → no-op (nothing to undo)."""
    event = {"event": "vault.toggle_refused", "rel_path": "plan.md",
             "target_line": 3, "expected_text": "task three", "ok": False,
             "preview_error": "mismatch"}
    result = rb._rollback_one(event, actor="rb-test", reason="undo", dry_run=False)
    assert result["ok"] is True
    assert "no-op" in result["action"]


def test_rollback_no_handler(
    audit_log: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unknown event type → error."""
    event = {"event": "vault.refactor", "rel_path": "plan.md",
             "target_line": 1, "expected_text": "x", "ok": True}
    result = rb._rollback_one(event, actor="rb-test", reason="undo", dry_run=False)
    assert result["ok"] is False
    assert "no rollback handler" in result["error"]


def test_rollback_rollback_event_rejected(
    audit_log: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cannot rollback a rollback (infinite undo chain prevention)."""
    event = {"event": "vault.rollback_applied", "rel_path": "plan.md",
             "target_line": 1, "expected_text": "x", "ok": True}
    result = rb._rollback_one(event, actor="rb-test", reason="undo", dry_run=False)
    assert result["ok"] is False
    assert "infinite undo" in result["error"]


def test_rollback_missing_path(
    audit_log: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Event with no rel_path → error."""
    event = {"event": "vault.toggle_applied", "rel_path": "",
             "target_line": 1, "expected_text": "x", "ok": True}
    result = rb._rollback_one(event, actor="rb-test", reason="undo", dry_run=False)
    assert result["ok"] is False
    assert "missing" in result["error"]


def test_rollback_file_no_longer_exists(
    audit_log: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plan file deleted between toggle and rollback → error."""
    from tools.vault import apply_toggle_cli as atc
    plan = tmp_path / "plan.md"  # Never created.
    monkeypatch.setattr(atc, "_resolve_plan_path", lambda rp: plan)
    event = {"event": "vault.toggle_applied", "rel_path": "plan.md",
             "target_line": 1, "expected_text": "x", "ok": True}
    result = rb._rollback_one(event, actor="rb-test", reason="undo", dry_run=False)
    assert result["ok"] is False
    assert "no longer exists" in result["error"]


def test_rollback_preview_fails_state_changed(
    audit_log: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If file state has changed (preview fails) → rollback refuses."""
    from tools.vault import apply_toggle_cli as atc
    plan = tmp_path / "plan.md"
    plan.write_text("- [ ] different text\n", encoding="utf-8")  # State changed!
    monkeypatch.setattr(atc, "_resolve_plan_path", lambda rp: plan)
    event = {"event": "vault.toggle_applied", "rel_path": "plan.md",
             "target_line": 1, "expected_text": "task one", "ok": True}
    result = rb._rollback_one(event, actor="rb-test", reason="undo", dry_run=False)
    assert result["ok"] is False
    assert "preview failed" in result["error"]


# === main CLI: list ===

def test_main_list_human(audit_log: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = rb.main(["list", "--log-path", str(audit_log), "--limit", "3"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "vault.toggle_applied" in out
    assert "vault.reopen_applied" in out


def test_main_list_json(audit_log: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = rb.main(["list", "--log-path", str(audit_log), "--limit", "3", "--json"])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert len(parsed) == 3


def test_main_list_actor_filter(
    audit_log: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = rb.main(["list", "--log-path", str(audit_log), "--actor", "agent"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "agent" in out
    assert "task four" in out


# === main CLI: undo ===

def test_main_undo_dry_run(
    audit_log: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """undo --dry-run → reports actions without mutating files."""
    # Patch _resolve_plan_path so preview_reopen can find the plan.
    from tools.vault import apply_toggle_cli as atc
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] task one\n", encoding="utf-8")
    monkeypatch.setattr(atc, "_resolve_plan_path", lambda rp: plan)

    # Filter to first event (task_one toggle).
    rc = rb.main([
        "undo", "--log-path", str(audit_log),
        "--event", "vault.toggle_applied",
        "--actor", "user",
        "--limit", "1",
        "--dry-run",
    ])
    assert rc == 0
    # File NOT mutated.
    assert plan.read_text(encoding="utf-8") == "- [x] task one\n"


def test_main_undo_no_matching(
    audit_log: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No matching events → exit 1."""
    rc = rb.main([
        "undo", "--log-path", str(audit_log),
        "--actor", "nobody",
    ])
    assert rc == 1
    assert "No matching events" in capsys.readouterr().err


def test_main_undo_real_rollback(
    audit_log: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """undo → file mutated + audit event written."""
    from tools.vault import apply_toggle_cli as atc
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] task one\n", encoding="utf-8")
    monkeypatch.setattr(atc, "_resolve_plan_path", lambda rp: plan)
    appended: list[dict] = []
    monkeypatch.setattr(vp, "append_event", lambda e: appended.append(e))

    rc = rb.main([
        "undo", "--log-path", str(audit_log),
        "--event", "vault.toggle_applied",
        "--actor", "user",
        "--limit", "1",
    ])
    assert rc == 0
    assert "- [ ] task one" in plan.read_text(encoding="utf-8")
    assert any(e["event"] == "vault.rollback_applied" for e in appended)


def test_main_undo_json_output(
    audit_log: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """undo --json emits structured results."""
    from tools.vault import apply_toggle_cli as atc
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] task one\n", encoding="utf-8")
    monkeypatch.setattr(atc, "_resolve_plan_path", lambda rp: plan)
    monkeypatch.setattr(vp, "append_event", lambda e: None)

    rc = rb.main([
        "undo", "--log-path", str(audit_log),
        "--event", "vault.toggle_applied",
        "--actor", "user", "--limit", "1",
        "--json",
    ])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert parsed[0]["rollback"]["ok"] is True


def test_main_invalid_cmd(audit_log: Path) -> None:
    with pytest.raises(SystemExit):
        rb.main(["bogus", "--log-path", str(audit_log)])


# === Typer registration ===

def test_vault_rollback_registered() -> None:
    """The vault-rollback command is registered."""
    import typer
    from interfaces.cli.v2 import register_vault_toggle
    app = typer.Typer()
    register_vault_toggle(app)
    cmd_names = [cmd.name for cmd in app.registered_commands]
    assert "vault-rollback" in cmd_names
