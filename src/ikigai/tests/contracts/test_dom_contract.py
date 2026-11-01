"""Contract tests for the unified DOM (SPEC-01 T1.4).

These assert the shape of the contract, not the behaviour of the store.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.contracts.common import UEID
from src.contracts.dom import (
    KIND_NAMESPACE,
    Artifact,
    ArtifactKind,
    SearchQuery,
    WriteRequest,
    make_uid,
)
from src.contracts.dom_kinds import KPIArtifact


def _artifact(**overrides: object) -> Artifact:
    now = datetime.now(UTC)
    data: dict[str, object] = {
        "uid": "kpi:taxa-conclusao:a1b2c3d4:0123456789abcdef",
        "kind": ArtifactKind.KPI,
        "title": "Taxa de conclusão",
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return Artifact(**data)


def test_every_kind_has_a_namespace() -> None:
    for kind in ArtifactKind:
        assert kind in KIND_NAMESPACE, f"{kind} has no namespace"
        namespace = KIND_NAMESPACE[kind]
        assert namespace.islower()
        assert 2 <= len(namespace) <= 5
        assert namespace.isalpha()


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        _artifact(unexpected="nope")


def test_frozen() -> None:
    artifact = _artifact()
    with pytest.raises(ValidationError):
        artifact.title = "changed"  # type: ignore[misc]


def test_uid_is_the_contract_class() -> None:
    assert Artifact.model_fields["uid"].annotation is UEID
    assert issubclass(UEID, str)


def test_make_uid_roundtrip() -> None:
    uid = make_uid(ArtifactKind.KPI, "taxa-conclusao", "a1b2c3d4", "0123456789abcdef")
    assert uid == "kpi:taxa-conclusao:a1b2c3d4:0123456789abcdef"
    assert UEID(str(uid)) == uid


def test_make_uid_rejects_malformed_parts() -> None:
    with pytest.raises(ValueError):
        make_uid(ArtifactKind.KPI, "Taxa-Conclusao", "a1b2c3d4", "0123456789abcdef")
    with pytest.raises(ValueError):
        make_uid(ArtifactKind.KPI, "taxa", "zz", "0123456789abcdef")


def test_search_query_limit_bounds() -> None:
    with pytest.raises(ValidationError):
        SearchQuery(limit=0)
    with pytest.raises(ValidationError):
        SearchQuery(limit=201)
    assert SearchQuery(limit=200).limit == 200


def test_write_request_requires_the_write_envelope() -> None:
    with pytest.raises(ValidationError):
        WriteRequest(artifact=_artifact(), idempotency_key="k")  # type: ignore[call-arg]
    request = WriteRequest(artifact=_artifact(), idempotency_key="k", client_id="laptop")
    assert request.expected_revision is None


def test_kpi_uses_decimal_not_float() -> None:
    artifact = KPIArtifact(
        uid="kpi:taxa-conclusao:a1b2c3d4:0123456789abcdef",
        title="Taxa",
        metric="taxa de conclusão",
        period="2026-Q4",
        target="12.5",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    assert str(artifact.target) == "12.5"
    with pytest.raises(ValidationError):
        KPIArtifact(
            uid="kpi:taxa-conclusao:a1b2c3d4:0123456789abcdef",
            title="Taxa",
            metric="taxa",
            period="2026-Q4",
            target="abc",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
