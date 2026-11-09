"""The change feed resumes: a client that was away gets the gap.

The announcement alone (`pg_notify`, 0004) is a doorbell: it reaches whoever
is listening at that instant and nobody else. A client that was reconnecting
when the write happened never learns it happened, and the gap is silent and
permanent — the client knows what it WROTE (the drafts) and not what CHANGED.

0007 makes the same trigger write the event to a table, in the artifact's own
transaction, and announce the row it wrote. These tests hold the two halves
and the thing that ties them together:

1. **live** — the event carries the store's sequence;
2. **replay** — `since` returns what came after it, in the store's order;
3. **the tie** — the `hello` frame says where the log stands, so a client can
   tell "nothing happened" from "I missed something".
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.contracts.dom import SearchResult
from src.services.changes import ChangeEvent, ChangeFeed, Replay
from src.transport import mcp_server, ws_server

MIGRATIONS = Path(__file__).resolve().parents[3] / "contracts" / "migrations"


class FakeRepo:
    """A repository that answers the log the way the store does."""

    def __init__(self, rows: list[dict[str, Any]] | None = None, tip: int = 0) -> None:
        self.rows = rows or []
        self.tip = tip
        self.asked: list[tuple[int, int]] = []
        self.pruned: list[int] = []

    async def events_since(self, since: int, limit: int) -> list[dict[str, Any]]:
        self.asked.append((since, limit))
        return [row for row in self.rows if int(row["seq"]) > since][:limit]

    async def event_tip(self) -> int:
        return self.tip

    async def prune_events(self, keep: int) -> int:
        self.pruned.append(keep)
        return 0


def _rows(*seqs: int, op: str = "UPDATE") -> list[dict[str, Any]]:
    return [{"seq": seq, "uid": "kpi:x:aabbccdd:0123456789abcdef", "op": op} for seq in seqs]


# ---------------------------------------------------------------------------
# 1. the live half carries the sequence
# ---------------------------------------------------------------------------
def test_a_live_event_carries_the_store_sequence() -> None:
    """Without it the client cannot say what it already saw."""
    frame = ws_server.event_frame(
        ChangeEvent(uid="kpi:x:aabbccdd:0123456789abcdef", op="UPDATE", seq=42)
    )

    assert frame["data"]["seq"] == 42
    assert frame["data"]["uid"] == "kpi:x:aabbccdd:0123456789abcdef"
    assert frame["event"] == "artifact.update"


def test_an_event_without_a_sequence_still_travels() -> None:
    """An older trigger, or a payload built by hand, must not break the frame."""
    frame = ws_server.event_frame(ChangeEvent(uid="kpi:x:aabbccdd:0123456789abcdef", op="INSERT"))

    assert "seq" not in frame["data"]
    assert frame["data"]["op"] == "INSERT"


# ---------------------------------------------------------------------------
# 2. the replay half
# ---------------------------------------------------------------------------
async def test_the_replay_returns_what_came_after() -> None:
    repo = FakeRepo(rows=_rows(4, 5, 6), tip=6)
    replay = await ChangeFeed(repo).replay(since=3)  # type: ignore[arg-type]

    assert [event.seq for event in replay.events] == [4, 5, 6]
    assert replay.tip == 6
    assert replay.truncated is False
    assert replay.last_seq == 6


async def test_the_replay_asks_for_one_row_more_than_it_returns() -> None:
    """`truncated` has to be a fact, not a guess about how many there were."""
    repo = FakeRepo(rows=_rows(*range(1, 11)), tip=10)
    await ChangeFeed(repo).replay(since=0, limit=3)  # type: ignore[arg-type]

    assert repo.asked == [(0, 4)], "it must ask for limit+1 to know whether there is more"


async def test_a_gap_bigger_than_a_page_is_said_out_loud() -> None:
    """Silence would be worse than either answer."""
    repo = FakeRepo(rows=_rows(*range(1, 11)), tip=10)
    replay = await ChangeFeed(repo).replay(since=0, limit=3)  # type: ignore[arg-type]

    assert len(replay.events) == 3
    assert replay.truncated is True


async def test_an_empty_gap_is_empty_and_not_truncated() -> None:
    repo = FakeRepo(rows=[], tip=9)
    replay = await ChangeFeed(repo).replay(since=9)  # type: ignore[arg-type]

    assert replay.events == ()
    assert replay.truncated is False
    assert replay.last_seq is None
    assert replay.tip == 9


def test_the_order_is_the_stores_and_not_a_clock() -> None:
    """Two writes in the same microsecond are two events; a timestamp cannot order them."""
    sql = (MIGRATIONS / "0007_artifact_events_log.sql").read_text(encoding="utf-8")

    assert re.search(r"seq\s+bigserial primary key", sql), (
        "the cursor must be a sequence, not a timestamp"
    )


# ---------------------------------------------------------------------------
# 3. the tie: the hello says where the log stands
# ---------------------------------------------------------------------------
async def test_the_router_reports_the_tip() -> None:
    class Services:
        changes = ChangeFeed(FakeRepo(rows=[], tip=17))  # type: ignore[arg-type]

    assert await ws_server.Router(Services()).tip() == 17  # type: ignore[arg-type]


async def test_an_unreadable_tip_does_not_break_the_connection() -> None:
    """A degraded replay is better than no client at all."""

    class Broken:
        async def tip(self) -> int:
            raise RuntimeError("the log is gone")

    class Services:
        changes = Broken()

    assert await ws_server.Router(Services()).tip() == 0  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 4. the migration: persist AND announce, in one transaction
# ---------------------------------------------------------------------------
def _migration() -> str:
    return (MIGRATIONS / "0007_artifact_events_log.sql").read_text(encoding="utf-8")


def test_the_migration_exists_with_a_reverse() -> None:
    for name in ("0007_artifact_events_log.sql", "0007_artifact_events_log.down.sql"):
        path = MIGRATIONS / name
        assert path.exists(), f"{name} is missing"
        assert path.read_text(encoding="utf-8").strip(), f"{name} is empty"


def test_the_trigger_keeps_the_event_and_still_announces() -> None:
    sql = _migration()

    assert "insert into ikig.artifact_events" in sql, "the event is not kept"
    assert "pg_notify" in sql, "the live feed was lost"
    assert "returning seq into seq_value" in sql, "the announcement must carry the sequence"


def test_the_reverse_restores_the_announcement_without_the_log() -> None:
    """A rollback must leave a database that still announces its changes."""
    down = (MIGRATIONS / "0007_artifact_events_log.down.sql").read_text(encoding="utf-8")

    assert "create or replace function ikig.notify_artifact_event" in down
    assert "pg_notify" in down
    assert "insert into ikig.artifact_events" not in down
    assert "drop table if exists ikig.artifact_events" in down


def test_the_log_is_bounded() -> None:
    """A table that only grows is a table that eventually costs a backup."""
    sql = _migration()

    assert "prune_artifact_events" in sql
    assert "offset keep" in sql, "the prune must keep the newest, not the oldest"


# ---------------------------------------------------------------------------
# 5. the transport frame
# ---------------------------------------------------------------------------
class FakeSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send_json(self, data: dict[str, Any]) -> None:
        self.sent.append(data)


class FakeArtifacts:
    async def search(self, query: Any) -> Any:
        return SearchResult(artifacts=())


def _router(changes: Any) -> Any:
    services = mcp_server.Services(
        artifacts=FakeArtifacts(),  # type: ignore[arg-type]
        relations=object(),  # type: ignore[arg-type]
        embeddings=object(),  # type: ignore[arg-type]
        changes=changes,  # type: ignore[arg-type]
        drafts=object(),  # type: ignore[arg-type]
    )
    mcp_server.set_services(services)
    return ws_server.Router(services)


async def _resume(
    frame: dict[str, Any], rows: list[dict[str, Any]] | None = None, tip: int = 0
) -> dict[str, Any]:
    import json

    router = _router(ChangeFeed(FakeRepo(rows=rows, tip=tip)))  # type: ignore[arg-type]
    socket = FakeSocket()
    await router.handle(socket, json.dumps(frame))  # type: ignore[arg-type]
    assert socket.sent
    return socket.sent[0]


async def test_a_resume_frame_answers_with_the_gap() -> None:
    frame = await _resume({"type": "resume", "id": "r1", "since": 3}, rows=_rows(4, 5), tip=5)

    assert frame["type"] == "result"
    assert frame["ok"] is True
    assert [event["seq"] for event in frame["data"]["events"]] == [4, 5]
    assert frame["data"]["tip"] == 5
    assert frame["data"]["truncated"] is False


async def test_a_resume_without_a_since_is_refused() -> None:
    """There is no sane default: 0 would replay the whole log."""
    frame = await _resume({"type": "resume", "id": "r2"})

    assert frame["ok"] is False
    assert frame["error"]["code"] == "validation"


async def test_the_replay_is_not_a_tool() -> None:
    """The six tools are the six; a resume is a frame, not an operation on the DOM."""
    router = _router(ChangeFeed(FakeRepo()))  # type: ignore[arg-type]
    await router.load_tools()

    assert not any("resume" in name or "event" in name for name in router.tool_names)


def test_a_replay_is_a_plain_value() -> None:
    """The service returns data, not a live generator: it can be framed and sent."""
    replay = Replay(events=(ChangeEvent(uid="u", op="UPDATE", seq=1),), tip=1)

    assert isinstance(replay.events, tuple)
    assert replay.last_seq == 1
