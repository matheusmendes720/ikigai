"""What a search carries — and what it does not (ADR-046).

The search used to hand back the whole prose of every hit. On the corpus the
box runs, twenty hits were **384 999 bytes**, of which **365 744** were
bodies: the transport paid for the owner's whole vault on every call, and the
product's own latency criterion (ADR-037 §8 — a structured search under 100 ms
at p95) failed by 78 ms because of it. The store itself was 10,6 ms; the
payload was the rest.

These are the guards that keep it fixed. Each one names what breaks it, so
none of them can be satisfied by a payload that merely happens to be small:

* the **summary has no body field** — a body field put back is a body returned;
* the **search's SELECT does not name the column** — a body selected and
  dropped afterwards still crossed the wire, still cost the transfer;
* the **prose is still reachable** through `get_artifact` — the guard against
  amputating the prose instead of moving it;
* the **payload does not grow with the prose** — the behavioural proof, and the
  one a payload of the wrong shape cannot pass.

They need no database: the SQL is captured from the repository itself, and the
payload is built from the rows it returns.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.contracts.dom import Artifact, ArtifactKind, ArtifactSummary, SearchQuery, SearchResult
from src.data.repository import ArtifactRepository

NOW = datetime.now(UTC)
UID = "kpi:taxa-conclusao:a1b2c3d4:0123456789abcdef"


class RecordingClient:
    """Captures the SQL, and answers with the rows it was given.

    `rows` answers the searches (`execute`); `one` answers the single-row read
    (`fetch_one`). They are separate because a statement that returns
    artifacts and a statement that returns edges are different statements, and
    a double that answers both with the same rows is a double that lies.
    """

    def __init__(
        self,
        rows: list[dict[str, Any]] | None = None,
        one: dict[str, Any] | None = None,
    ) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.rows = rows or []
        self.one = one

    async def execute(self, sql: str, params: tuple[object, ...] = ()) -> list[dict[str, Any]]:
        self.calls.append((sql, tuple(params)))
        return list(self.rows)

    async def fetch_one(self, sql: str, params: tuple[object, ...] = ()) -> dict[str, Any] | None:
        self.calls.append((sql, tuple(params)))
        return self.one


def _repo(
    rows: list[dict[str, Any]] | None = None,
    one: dict[str, Any] | None = None,
) -> tuple[ArtifactRepository, RecordingClient]:
    client = RecordingClient(rows, one)
    return ArtifactRepository(client), client  # type: ignore[arg-type]


def _row(body: str = "", **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "uid": UID,
        "kind": ArtifactKind.KPI.value,
        "title": "Taxa de conclusão",
        "body": body,
        "body_hash": "0" * 64,
        "parent_uid": None,
        "quarter": "Q4-2026",
        "status": "ativo",
        "vault_path": "04-relatorios/kpi.md",
        "revision": 1,
        "created_at": NOW,
        "updated_at": NOW,
        "deleted_at": None,
    }
    row.update(overrides)
    return row


def _selected_columns(sql: str) -> set[str]:
    """The columns the statement actually SELECTs.

    Read as names, not as text: the summary carries `body_hash`, and a search
    for the string "body" would find it in a statement that does NOT select
    the prose. The guard has to be about the column, or it is about nothing.
    """
    select = sql.split(" from ", 1)[0]
    assert select.startswith("select "), f"the statement does not start with a SELECT: {sql}"
    return {part.strip() for part in select[len("select ") :].split(",")}


def test_the_summary_carries_no_prose() -> None:
    """The summary has no `body` field.

    Falsification: add `body` to `ArtifactSummary` — the search starts
    returning the prose again, and this fails.
    """
    assert "body" not in ArtifactSummary.model_fields


def test_the_artifact_is_the_summary_plus_the_prose() -> None:
    """The two stay in step: the artifact is the summary and the body.

    Falsification: add a field to the summary and not to the artifact — the
    store fills it in one and the other never learns of it.
    """
    assert set(Artifact.model_fields) == set(ArtifactSummary.model_fields) | {"body"}


def test_the_search_result_holds_summaries() -> None:
    """`SearchResult.artifacts` is typed with the summary, not the artifact.

    Falsification: type it with `Artifact` again — the schema the harness
    reads starts promising a body the search does not send.
    """
    annotation = SearchResult.model_fields["artifacts"].annotation
    assert getattr(annotation, "__origin__", None) is tuple
    assert annotation.__args__[0] is ArtifactSummary


async def test_the_search_sql_does_not_select_the_prose() -> None:
    """The column is ABSENT from the search's SELECT.

    Falsification: put `body` back into the search's column list — the body
    crosses the wire again, is built in the server's memory again, and this
    fails.
    """
    repo, client = _repo()
    await repo.search(SearchQuery(text="projeto"))
    assert client.calls, "the search sent no SQL"
    sql, _ = client.calls[0]
    assert "body" not in _selected_columns(sql)


async def test_the_prose_is_still_reachable_through_get_artifact() -> None:
    """Moving the prose is not removing it.

    The counter-guard: a search that carries no body is only a good design if
    the body is still ONE call away. `get_artifact` at depth 0 is that call.

    Falsification: strip the body from the read path — the prose becomes
    unreachable, and this fails.
    """
    repo, _ = _repo(one=_row(body="# A prosa do dono\n"))
    bundle = await repo.get_with_relations(UID, depth=0)
    assert bundle.artifact.body == "# A prosa do dono\n"


async def test_the_payload_does_not_grow_with_the_prose() -> None:
    """The behavioural proof: the payload is the same size whatever the prose.

    Two searches, twenty hits each, one with a half-megabyte body per hit and
    one with a single character. If the prose were in the payload, the second
    would be ten megabytes lighter.

    Falsification: put the body back into the summary — the two payloads
    differ by ten megabytes, and this fails.
    """
    prose = "X" * 500_000

    repo, _ = _repo([_row(body=prose) for _ in range(20)])
    heavy = await repo.search(SearchQuery(text="projeto", limit=20))
    heavy_payload = heavy.model_dump_json()

    repo, _ = _repo([_row(body="x") for _ in range(20)])
    light = await repo.search(SearchQuery(text="projeto", limit=20))
    light_payload = light.model_dump_json()

    assert len(heavy_payload) == len(light_payload), (
        f"the payload grew with the prose: {len(light_payload)} bytes without it, "
        f"{len(heavy_payload)} bytes with it"
    )
    assert "X" * 100 not in heavy_payload, "the prose is in the search payload"
    assert len(heavy_payload) < 50_000, (
        f"twenty summaries weigh {len(heavy_payload)} bytes; the guard's own bound "
        "is what says a summary page is small"
    )


async def test_the_search_still_answers_the_same_artifacts() -> None:
    """The summary is the artifact: the same identity, the same metadata.

    A guard that only said "the body is gone" would pass for a search that
    answers the wrong thing. This one says the answer did not change.

    Falsification: drop a field the summary is supposed to carry — the search
    stops describing what it found, and this fails.
    """
    repo, _ = _repo([_row(body="# A prosa\n")])
    result = await repo.search(SearchQuery(text="projeto", limit=20))
    assert result.artifacts, "the search found nothing"
    found = result.artifacts[0]
    assert found.uid == UID
    assert found.kind is ArtifactKind.KPI
    assert found.title == "Taxa de conclusão"
    assert found.quarter == "Q4-2026"
    assert found.status == "ativo"
    assert found.vault_path == "04-relatorios/kpi.md"
    assert found.revision == 1
    assert found.body_hash == "0" * 64
