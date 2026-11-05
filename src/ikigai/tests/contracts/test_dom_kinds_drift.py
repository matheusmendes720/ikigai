"""The DOM drift test (SPEC-01 T1.5) — the load-bearing invariant of the contract.

A new kind must arrive complete: a namespace, a typed model, and an entry in
the store's table map. Adding one without the others is the failure this test
exists to catch, and it is a failure of the contract, not of the code.

The spec also asks this test to check the kind table in the prose spec. That is
deliberately not done: a unit test that parses a markdown document breaks when
the document is edited, and the document is not the contract. The registries
below are the contract, and they are checked against each other.
"""

from __future__ import annotations

from typing import Any, get_args

import src.contracts.dom_kinds as dom_kinds
from src.contracts.dom import KIND_NAMESPACE, Artifact, ArtifactKind
from src.contracts.store import KIND_TABLES


def _derived_models() -> dict[ArtifactKind, type[Artifact]]:
    """The per-kind models, discovered by introspection rather than a hardcoded list."""
    found: dict[ArtifactKind, type[Artifact]] = {}
    for name in dir(dom_kinds):
        candidate: Any = getattr(dom_kinds, name)
        if not isinstance(candidate, type):
            continue
        if not issubclass(candidate, Artifact) or candidate is Artifact:
            continue
        if "kind" not in candidate.model_fields:
            continue
        args = get_args(candidate.model_fields["kind"].annotation)
        if len(args) == 1 and isinstance(args[0], ArtifactKind):
            found[args[0]] = candidate
    return found


def test_every_kind_has_a_derived_type() -> None:
    derived = _derived_models()
    missing = {kind for kind in ArtifactKind if kind not in derived}
    names = sorted(kind.value for kind in missing)
    assert not missing, f"kinds without a derived type in dom_kinds: {names}"


def test_every_kind_has_a_namespace() -> None:
    missing = {kind for kind in ArtifactKind if kind not in KIND_NAMESPACE}
    assert not missing, f"kinds without a namespace: {sorted(m.value for m in missing)}"


def test_every_kind_has_a_table_entry() -> None:
    missing = {kind for kind in ArtifactKind if kind not in KIND_TABLES}
    assert not missing, f"kinds without a table entry: {sorted(m.value for m in missing)}"


def test_derived_types_declare_a_literal_discriminator() -> None:
    derived = _derived_models()
    for kind, model in derived.items():
        annotation = model.model_fields["kind"].annotation
        args = get_args(annotation)
        assert args == (kind,), f"{model.__name__} does not pin kind={kind}"


def test_derived_types_keep_the_strict_model_config() -> None:
    for model in _derived_models().values():
        assert model.model_config.get("frozen") is True
        assert model.model_config.get("extra") == "forbid"


def test_kinds_with_own_fields_have_a_table() -> None:
    derived = _derived_models()
    spine_fields = set(Artifact.model_fields)
    for kind, model in derived.items():
        own = set(model.model_fields) - spine_fields
        table = KIND_TABLES[kind]
        if own:
            assert table is not None, f"{kind} has fields of its own but no extension table"
        else:
            assert table is None, f"{kind} has no fields of its own but declares table {table}"


def test_a_typed_artifact_survives_the_write_envelope() -> None:
    """The envelope must not flatten the typed model back to the spine.

    `WriteRequest.artifact` is typed as the spine, and the spine forbids extra
    fields. If the envelope rebuilt the artifact as an `Artifact`, a KPI's
    `metric` and `target` would be gone before the repository ever saw them —
    and the repository writes the extension tables by `isinstance`, so the
    loss would be silent.
    """
    from src.contracts.dom import ArtifactKind, WriteRequest, make_uid
    from src.contracts.dom_kinds import KPIArtifact

    kpi = KPIArtifact(
        uid=make_uid(ArtifactKind.KPI, "sono", "aaaaaaaa", "0123456789abcdef"),
        title="Sono",
        metric="horas de sono",
        period="2026-11",
        created_at="2026-11-04T00:00:00+00:00",
        updated_at="2026-11-04T00:00:00+00:00",
    )
    req = WriteRequest(artifact=kpi, idempotency_key="k", client_id="owner")

    assert isinstance(req.artifact, KPIArtifact), (
        f"the envelope turned the typed artifact into {type(req.artifact).__name__}"
    )
    assert req.artifact.metric == "horas de sono"
