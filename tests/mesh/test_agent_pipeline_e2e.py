"""End-to-end test: TaskChange → review_queue_cli inspect → worker drain → CLI re-inspect.

Validates that the full agent propagation pipeline works correctly through
the public CLI surface — not just by reading the queue internals. Uses
`_FakeAdapter` to stand in for the real ForkAdapter implementations
(Taskdog / Cli / SolverforgeCalendar) so we exercise the worker's
adapter dispatch without touching real SQLite / JSONL state.

Coverage:
  * Happy path: enqueue → CLI shows pending → run_once → CLI shows propagated
  * Multi-event drain
  * Partial propagation (one adapter fails) → CLI shows partial_propagation
  * Rejection (vague title) → CLI shows rejected
  * CLARIFY path (vague title) → CLI shows clarified
  * Idempotency: run_once twice, no double-processing
  * CLI observation is consistent at every stage
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from src.contracts.common import UEID
from src.contracts.task_change import (
    PropagationEvent,
    TaskAction,
    TaskChange,
)
from src.mesh import queue as queue_mod
from src.mesh.review_queue_cli import main as cli_main
from src.mesh.review_queue_worker import run_once


# ─────────────────── Fake adapter ───────────────────


@dataclass
class _FakeAdapter:
    """Minimal ForkAdapter implementation for E2E tests.

    Records every PropagationEvent it receives. Can be configured to raise
    on apply_change() to simulate per-adapter failures (partial propagation).
    """

    name: str
    received: list[PropagationEvent] = field(default_factory=list)
    raises: Exception | None = None

    def read(self, ueid: UEID) -> dict[str, Any] | None:
        for event in self.received:
            if event.ueid == ueid:
                return {"ueid": str(event.ueid), "title": event.fields.get("title")}
        return None

    def apply_change(self, event: PropagationEvent) -> None:
        if self.raises is not None:
            raise self.raises
        self.received.append(event)

    def supports_field(self, field_name: str) -> bool:
        return field_name in {"ueid", "title", "status"}


def _sample_event(
    event_id: str,
    *,
    title: str = "Concrete actionable task",
    ueid: str = "tsk:test:00000000-0000-0000-0000-000000000000:0000000000000001",
    due: str | None = None,
    status: str = "pending",
) -> TaskChange:
    fields: dict[str, Any] = {"title": title}
    if due is not None:
        fields["due"] = due
    return TaskChange(
        event_id=event_id,
        ueid=ueid,
        action=TaskAction.CREATE,
        fields=fields,
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
        status=status,  # type: ignore[arg-type]
    )


def _future_iso() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()


# ─────────────────── Fixtures ───────────────────


@pytest.fixture
def queue_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    qdir = tmp_path / "review_queue"
    qdir.mkdir()
    monkeypatch.setattr(queue_mod, "QUEUE_DIR", qdir)
    return qdir


@pytest.fixture
def two_adapters() -> list[_FakeAdapter]:
    return [_FakeAdapter(name="fake-cli"), _FakeAdapter(name="fake-taskdog")]


# ─────────────────── Helper ───────────────────


def _cli_status(queue_dir: Path) -> dict[str, int]:
    """Parse `review_queue_cli status` output into {status: count}.

    Filters to only the 6 known TaskStatus values (skips `total:` and `queue_dir:` lines).
    Zero-valued statuses ARE included in the dict — matches the CLI's actual output.
    """
    import io
    from contextlib import redirect_stdout

    from src.mesh.review_queue_cli import VALID_STATUSES

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli_main(["status", "--queue-dir", str(queue_dir)])
    assert rc == 0
    out = buf.getvalue()
    counts: dict[str, int] = {}
    valid = set(VALID_STATUSES)
    for line in out.splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        if key in valid:
            counts[key] = int(val.strip())
    return counts


def _expected_counts(**kwargs: int) -> dict[str, int]:
    """Build a full status dict with explicit zeros for unset keys."""
    from src.mesh.review_queue_cli import VALID_STATUSES

    counts = {s: 0 for s in VALID_STATUSES}
    counts.update(kwargs)
    return counts


def _cli_list_ids(queue_dir: Path) -> list[str]:
    """Parse `review_queue_cli list` output into [event_id]."""
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli_main(["list", "--queue-dir", str(queue_dir)])
    assert rc == 0
    return [json.loads(ln)["event_id"] for ln in buf.getvalue().splitlines() if ln.strip()]


# ─────────────────── Tests ───────────────────


def test_happy_path_enqueue_then_propagate(
    queue_dir: Path, two_adapters: list[_FakeAdapter]
) -> None:
    """Enqueue → CLI shows pending → run_once → CLI shows propagated."""
    event = _sample_event("evt_happy", due=_future_iso())
    queue_mod.enqueue(event)

    # CLI observation BEFORE drain
    assert _cli_status(queue_dir) == _expected_counts(pending=1)
    assert _cli_list_ids(queue_dir) == ["evt_happy"]

    # Run the worker drain
    result = run_once(two_adapters)
    assert result.consumed == 1
    assert result.approved == 1
    assert result.rejected == 0

    # CLI observation AFTER drain
    assert _cli_status(queue_dir) == _expected_counts(propagated=1)

    # `list` shows all events by default; filter by --status propagated to verify
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        cli_main(["list", "--queue-dir", str(queue_dir), "--status", "propagated"])
    assert json.loads(buf.getvalue().splitlines()[0])["event_id"] == "evt_happy"

    # Both adapters received the propagation
    assert len(two_adapters[0].received) == 1
    assert len(two_adapters[1].received) == 1
    assert two_adapters[0].received[0].event_id == "evt_happy"


def test_multi_event_drain(
    queue_dir: Path, two_adapters: list[_FakeAdapter]
) -> None:
    """3 events → single run_once drains all → status reflects 3 propagated."""
    events = [
        _sample_event(
            f"evt_{i}",
            ueid=f"tsk:test:00000000-0000-0000-0000-000000000000:{i:016x}",
            due=_future_iso(),
        )
        for i in range(3)
    ]
    for event in events:
        queue_mod.enqueue(event)

    assert _cli_status(queue_dir) == _expected_counts(pending=3)

    result = run_once(two_adapters)
    assert result.consumed == 3
    assert result.approved == 3

    assert _cli_status(queue_dir) == _expected_counts(propagated=3)


def test_partial_propagation_status_reflected(
    queue_dir: Path, two_adapters: list[_FakeAdapter]
) -> None:
    """One adapter raises → status shows partial_propagation (not propagated)."""
    # First adapter succeeds, second raises
    two_adapters[1].raises = RuntimeError("simulated downstream failure")

    queue_mod.enqueue(_sample_event("evt_partial", due=_future_iso()))

    result = run_once(two_adapters)
    assert result.consumed == 1
    assert result.approved == 1
    assert result.partial == 1

    # CLI shows partial_propagation, NOT propagated
    assert _cli_status(queue_dir) == _expected_counts(partial_propagation=1)

    # First adapter still received it; second did not
    assert len(two_adapters[0].received) == 1
    assert len(two_adapters[1].received) == 0


def test_rejection_path_via_past_due_date(
    queue_dir: Path, two_adapters: list[_FakeAdapter]
) -> None:
    """Event with due date in the past → REJECT → CLI shows rejected."""
    past_iso = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
    queue_mod.enqueue(_sample_event("evt_past_due", due=past_iso))

    result = run_once(two_adapters)
    assert result.consumed == 1
    assert result.rejected == 1
    assert result.approved == 0

    counts = _cli_status(queue_dir)
    assert counts["rejected"] == 1
    assert counts["propagated"] == 0

    # Adapters did NOT receive the event
    for adapter in two_adapters:
        assert adapter.received == []


def test_clarify_path_via_vague_title(
    queue_dir: Path, two_adapters: list[_FakeAdapter]
) -> None:
    """Title 'todo' triggers CLARIFY → CLI shows clarified."""
    queue_mod.enqueue(_sample_event("evt_vague", title="todo"))

    result = run_once(two_adapters)
    assert result.consumed == 1
    assert result.clarified == 1
    assert result.approved == 0

    assert _cli_status(queue_dir) == _expected_counts(clarified=1)


def test_run_once_is_idempotent(
    queue_dir: Path, two_adapters: list[_FakeAdapter]
) -> None:
    """After first drain, second drain processes nothing (already propagated)."""
    queue_mod.enqueue(_sample_event("evt_idem", due=_future_iso()))

    first = run_once(two_adapters)
    assert first.consumed == 1

    second = run_once(two_adapters)
    assert second.consumed == 0
    assert second.approved == 0

    # Adapters received exactly ONE propagation event (not two)
    for adapter in two_adapters:
        assert len(adapter.received) == 1


def test_cli_show_returns_propagated_event_details(
    queue_dir: Path, two_adapters: list[_FakeAdapter]
) -> None:
    """After propagation, `show <event_id>` returns the acked event JSON."""
    queue_mod.enqueue(_sample_event("evt_show", due=_future_iso()))
    run_once(two_adapters)

    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli_main(["show", "--queue-dir", str(queue_dir), "evt_show"])
    assert rc == 0
    parsed = json.loads(buf.getvalue())
    assert parsed["event_id"] == "evt_show"
    assert parsed["status"] == "propagated"
    assert parsed["action"] == "create"
    assert parsed["fields"]["title"] == "Concrete actionable task"


def test_cli_list_with_status_filter_after_drain(
    queue_dir: Path, two_adapters: list[_FakeAdapter]
) -> None:
    """After drain, --status pending returns empty; --status propagated returns the events."""
    queue_mod.enqueue(_sample_event("evt_a", due=_future_iso()))
    queue_mod.enqueue(_sample_event("evt_b", due=_future_iso()))

    # Before drain: pending:2
    assert _cli_status(queue_dir) == _expected_counts(pending=2)

    run_once(two_adapters)

    # After drain: propagated:2; --status pending yields nothing
    assert _cli_status(queue_dir) == _expected_counts(propagated=2)

    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        cli_main(["list", "--queue-dir", str(queue_dir), "--status", "pending"])
    assert buf.getvalue().strip() == ""

    buf = io.StringIO()
    with redirect_stdout(buf):
        cli_main(["list", "--queue-dir", str(queue_dir), "--status", "propagated"])
    ids = sorted(json.loads(ln)["event_id"] for ln in buf.getvalue().splitlines() if ln.strip())
    assert ids == ["evt_a", "evt_b"]


def test_pipeline_with_empty_queue_is_noop(
    queue_dir: Path, two_adapters: list[_FakeAdapter]
) -> None:
    """Drain an empty queue must not crash; counts all zero."""
    assert _cli_status(queue_dir) == _expected_counts()

    result = run_once(two_adapters)
    assert result.consumed == 0
    assert result.approved == 0
    assert result.rejected == 0
    assert result.clarified == 0

    for adapter in two_adapters:
        assert adapter.received == []